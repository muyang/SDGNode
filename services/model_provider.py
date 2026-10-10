#!/usr/bin/env python3
"""P2 · SDGNode 模型服务（MODEL.md 线上约定的参考实现，端口默认 8801）。

诚实声明：本服务是**契约级参考实现**，不含真实权重——
  · /osdg*     OSDG v0 词法占位分类器（关键词命中计分，确定性，非 Transformer 权重）
  · /pm25*     PM2.5 v0 代理公式（AOD 栅格均值 → 线性代理，surrogate）
  · /prithvi/jobs*  批作业桩（submit→poll→collect 状态机，产物标记 synthetic）
价值在于：输入/输出契约、provider 选路、算力门禁 retarget 全部按 SDK 真代码走通。

InferenceProvider 约定：POST {endpoint} {"model","inputs","params","request_id"} → {"outputs":{...}}
BatchProvider  约定：POST {endpoint} → {"job_id","status":"queued"}；GET {endpoint}/{job_id} → 终态 {"outputs"}
"""
from __future__ import annotations

import threading
import uuid

from fastapi import FastAPI, Request

app = FastAPI(title="SDGNode model service (contract reference)")
_lock = threading.Lock()
_stats: dict[str, int] = {}
_jobs: dict[str, dict] = {}

_GOAL_TERMS = {
    1: ["贫困", "贫困率", "pov", "poverty", "收入", "income"],
    2: ["粮食", "农业", "crop", "food", "hunger", "农"],
    3: ["健康", "卫生", "disease", "health", "医疗", "污染致死"],
    4: ["教育", "学校", "education", "sc"],
    5: ["性别", "women", "gender", "妇女"],
    6: ["水", "water", "卫生设施", "sanitation", "水质"],
    7: ["能源", "electric", "energy", "电", "可再生"],
    8: ["就业", "就业", "gdp", "work", "劳动"],
    9: ["基础设施", "工业", "innovation", "industrial", "创新"],
    10: ["不平等", "inequal", "equality", "收入差", "移民"],
    11: ["城市", "城市", "urban", "housing", "住房", "贫民窟"],
    12: ["消费", "生产", "waste", "consumption", "回收"],
    13: ["气候", "climate", "排放", "emission", "ghg", "碳"],
    14: ["海洋", "海洋", "marine", "ocean", "fish", "渔业"],
    15: ["森林", "陆地", "forest", "land", "biodiversity", "荒漠化", "土地退化"],
    16: ["治理", "和平", "justice", "governance", "腐败", "制度"],
    17: ["合作", "数据", "伙伴", "partnership", "cooperation", "统计能力", "资金"],
}


def _bump(route: str) -> None:
    with _lock:
        _stats[route] = _stats.get(route, 0) + 1


def _osdg_classify(text: str) -> dict:
    t = (text or "").lower()
    scores: dict[int, float] = {}
    for goal, terms in _GOAL_TERMS.items():
        hit = sum(1 for w in terms if w.lower() in t)
        scores[goal] = min(1.0, hit * 0.34)
    return scores


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "sdgnode-model-v0", "note": "contract reference, no real weights"}


@app.get("/__stats")
def stats() -> dict:
    with _lock:
        return dict(_stats)


@app.post("/")
async def root_dispatch(req: Request) -> dict:
    """算力门禁 retarget 到 node_url（根地址）时按 body.model 分发。"""
    body = await req.json()
    model = str(body.get("model", "")).lower()
    if "osdg" in model:
        return await osdg(req)
    if "pm25" in model:
        return await pm25(req)
    return {"error": f"no route for model {model!r} at root"}


@app.post("/osdg")
@app.post("/osdg/invoke")
async def osdg(req: Request) -> dict:
    _bump("/osdg")
    body = await req.json()
    text = str(body.get("inputs", {}).get("text", ""))
    scores = _osdg_classify(text)
    matched = [g for g, s in scores.items() if s >= 0.15]
    return {
        "outputs": {
            "sdg_scores": {str(k): round(v, 3) for k, v in scores.items()},
            "matched_sdgs": matched,
        },
        "model": body.get("model"),
        "request_id": body.get("request_id"),
        "note": "v0-lexical placeholder",
    }


@app.post("/pm25")
@app.post("/pm25/invoke")
async def pm25(req: Request) -> dict:
    _bump("/pm25")
    import numpy as np
    import rasterio

    body = await req.json()
    aod_ref = str(body.get("inputs", {}).get("aod_grid", ""))
    mean_aod = 0.15
    try:
        with rasterio.open(aod_ref) as ds:
            arr = ds.read(1)
            mean_aod = float(np.nanmean(arr))
    except Exception:  # noqa: BLE001
        pass
    # v0 代理公式（surrogate）：pm25 = 18.5 * mean(AOD) + 3.5 —— 真实管线换 GBDT
    level = 18.5 * mean_aod + 3.5
    out_path = f"runs/pm25/pm25_{body.get('request_id', 'adhoc')[:16]}.tif"
    try:
        import os
        from pathlib import Path

        Path("runs/pm25").mkdir(parents=True, exist_ok=True)
        with rasterio.open(aod_ref) as ds:
            arr = ds.read(1).astype("float32")
            profile = ds.profile
        vals = np.clip(18.5 * arr + 3.5, 0, 300).astype("float32")
        profile.update(dtype="float32", count=1)
        with rasterio.open(out_path, "w", **profile) as w:
            w.write(vals, 1)
    except Exception:  # noqa: BLE001
        out_path = f"runs/pm25/pm25_value_{round(level, 3)}.json"
        import json
        from pathlib import Path

        Path("runs/pm25").mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps({"pm25_mean": level}), encoding="utf-8")
    return {
        "outputs": {
            "pm25_grid": out_path,
            "cv_metrics": {"r2": 0.0, "note": "surrogate v0，非验证指标", "mean_aod": mean_aod},
            "pm25_mean": level,
        },
        "model": body.get("model"),
        "request_id": body.get("request_id"),
    }


@app.post("/prithvi/jobs")
async def prithvi_submit(req: Request) -> dict:
    _bump("/prithvi/jobs")
    body = await req.json()
    job_id = f"job-{uuid.uuid4().hex[:10]}"
    _jobs[job_id] = {"polls": 0, "request": body}
    return {"job_id": job_id, "status": "queued"}


@app.get("/prithvi/jobs/{job_id}")
def prithvi_poll(job_id: str) -> dict:
    _bump("/prithvi/jobs/poll")
    job = _jobs.get(job_id)
    if job is None:
        return {"status": "failed", "error": f"unknown job {job_id}"}
    job["polls"] += 1
    if job["polls"] < 3:
        return {"status": "running", "progress": job["polls"] / 3}
    return {
        "status": "succeeded",
        "outputs": {
            "class_map": f"runs/batch/{job_id}_flood_synthetic.tif",
            "note": "synthetic batch product (contract stub, no weights)",
        },
    }
