"""SDGNode 公共算子 handler（契约 = cards/skill/*.yaml；GeoSkill handler(params, context) -> dict）。

约定：
- params["outputs_dir"] 由执行器注入（runs/<run>/<step>/）；缺省写 runs/_adhoc。
- 离线演示数据经 env SDGNODE_DEMO_DIR + params["city"] 从 sdgnode_skills.synth 合成；
  生产环境该解析换成 CAFE 下推到数据主权节点（数据不动，计算下推）。
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import shape

from . import synth


# --------------------------------------------------------------------------- #
# 基础 IO
# --------------------------------------------------------------------------- #
def _out_dir(params: dict, name: str = "") -> Path:
    d = Path(params.get("outputs_dir") or os.environ.get("SDGNODE_ADHOC_OUT", "runs/_adhoc"))
    if name:
        d = d / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(path: str):
    ds = rasterio.open(path)
    return ds, ds.read(1)


def _demo_paths(params: dict) -> dict:
    city = str(params.get("city", "武汉"))
    base = Path(os.environ.get("SDGNODE_DEMO_DIR", "state/demo"))
    return synth.ensure(city, base)


# --------------------------------------------------------------------------- #
# s1 · 边界获取（数据卡 sdg.data.boundary.chn-cities 的可执行替身）
# --------------------------------------------------------------------------- #
def fetch_boundary(params: dict, context) -> dict:
    d = _demo_paths(params)
    city = str(params.get("city", "武汉"))
    out = _out_dir(params, "boundary")
    aoi = out / f"aoi_{city}.geojson"
    aoi.write_text(Path(d["aoi"]).read_text(encoding="utf-8"), encoding="utf-8")
    mask = out / f"mask_{city}.tif"
    mask.write_bytes(Path(d["mask"]).read_bytes())
    return {"aoi": str(aoi), "mask": str(mask)}


# --------------------------------------------------------------------------- #
# s2 · clip-stack：按掩膜裁剪 + 期相解析（离线=合成源，生产=CAFE 解引用）
# --------------------------------------------------------------------------- #
def clip_stack(params: dict, context) -> dict:
    d = _demo_paths(params)
    mask_path = params.get("mask") or d["mask"]
    out = _out_dir(params, "stack")
    with rasterio.open(mask_path) as m:
        mask_arr = m.read(1).astype(bool)
        tf, crs, shape_ = m.transform, m.crs, m.shape
    result = {"alignment_report": None}
    for key in ("built_up_t0", "built_up_t1", "pop_t0", "pop_t1"):
        src = d[key]
        with rasterio.open(src) as ds:
            arr = ds.read(1)
        arr = np.where(mask_arr, arr, 0)  # 掩膜外置 0（NODATA 语义演示简化）
        dst = out / f"{Path(src).stem}_clipped.tif"
        with rasterio.open(dst, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                           count=1, dtype=arr.dtype.name,
                           crs=crs, transform=tf) as w:
            w.write(arr, 1)
        result[key] = str(dst)
    result["alignment_report"] = str(out / "alignment.json")
    (out / "alignment.json").write_text(json.dumps(
        {"clip": mask_path, "crs": str(crs), "grid": list(shape_), "synthetic_demo_mode": True},
        ensure_ascii=False, indent=2), encoding="utf-8")
    result["stack"] = result["built_up_t1"]  # 演示：堆栈以目标期栅格为代理
    return result


# --------------------------------------------------------------------------- #
# s3 · LCRPGR（SDG 11.3.1，UN-Habitat 口径：年均复合增长率比值）
# --------------------------------------------------------------------------- #
def lcrpgr(params: dict, context) -> dict:
    inp = params.get("inputs", {})
    year = int(params.get("year", 2020))
    baseline = int(params.get("baseline", 2015))
    method = str(params.get("method", "UN-Habitat 2025"))
    dt = year - baseline
    if dt <= 0:
        raise ValueError(f"year({year}) 必须晚于 baseline({baseline})")

    def area(p):
        ds, a = _read(p)
        cell = abs(ds.transform.a * ds.transform.e) * 111_000 ** 2 * (ds.res[0] / ds.res[0])
        cell = abs(ds.transform.a) * 111_000 * (abs(ds.transform.e) * 111_000)
        return float((a > 0).sum() * cell)

    def pop_total(p):
        _, a = _read(p)
        return float(np.nansum(a))

    a0, a1 = area(inp["built_up_t0"]), area(inp["built_up_t1"])
    p0, p1 = pop_total(inp["population_t0"]), pop_total(inp["population_t1"])
    lcr = (a1 / a0) ** (1 / dt) - 1
    pgr = (p1 / p0) ** (1 / dt) - 1

    ds0, b0 = _read(inp["built_up_t0"])
    _, b1 = _read(inp["built_up_t1"])
    trans = np.zeros_like(b0)
    trans[(b0 > 0) & (b1 > 0)] = 1   # 存量建成
    trans[(b0 == 0) & (b1 > 0)] = 2  # 新增建成
    trans[(b0 > 0) & (b1 == 0)] = 3  # 建成退化
    out = _out_dir(params, "metrics")
    tm = out / "transition_map.tif"
    with rasterio.open(tm, "w", driver="GTiff", height=trans.shape[0], width=trans.shape[1],
                       count=1, dtype="uint8", crs=ds0.crs, transform=ds0.transform) as w:
        w.write(trans, 1)
    (out / "metrics.json").write_text(json.dumps(
        {"lcr": lcr, "pgr": pgr, "lcrpgr": (lcr / pgr if pgr else None),
         "baseline": baseline, "year": year, "method": method,
         "built_area_m2": {"t0": a0, "t1": a1}, "population": {"t0": p0, "t1": p1}},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return {"lcr": lcr, "pgr": pgr, "lcrpgr": lcr / pgr if pgr else float("nan"),
            "transition_map": str(tm)}


# --------------------------------------------------------------------------- #
# s4 · report.render（tpl.sdg-report）
# --------------------------------------------------------------------------- #
def report_render(params: dict, context) -> dict:
    inp = params.get("inputs", {})
    src = params.get("source", {})  # 来源四件套由执行器注入：run/recipe/params/data_snapshot
    out = _out_dir(params, "report")
    title = params.get("title", "SDG 指标评估报告")
    fmt = params.get("format", "html")
    if fmt != "html":
        raise ValueError(f"P1 演示模板仅支持 html（{fmt} 走 P3 Quarto/Pandoc 管线）")
    lcr = float(inp.get("lcr", float("nan")))
    pgr = float(inp.get("pgr", float("nan")))
    lp = inp.get("lcrpgr")
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>{title}</title></head><body>
<h1>{title}</h1>
<h2>方法</h2><p>口径：{src.get('params', {}).get('method', 'UN-Habitat 2025')}。
LCR/PGR = 建成区面积、人口的年均复合增长率之比（SDG 11.3.1）；基准年 {src.get('params', {}).get('baseline')}，目标年 {src.get('params', {}).get('year')}，城市 {src.get('params', {}).get('city')}。</p>
<h2>数据与参数</h2><ul>
<li>方案：<code>{src.get('recipe', '—')}</code></li>
<li>运行：<code>{src.get('source_run', '—')}</code></li>
<li>数据快照：<code>{json.dumps(src.get('data_snapshot', {}), ensure_ascii=False)}</code></li>
<li>数据：GHS-BUILT-S / GHS-POP（离线演示=合成源，标记 synthetic）</li></ul>
<h2>结果</h2><table border="1" cellpadding="6"><tr><th>量</th><th>值</th></tr>
<tr><td>土地消耗率 LCR</td><td>{lcr:.5f}/年</td></tr>
<tr><td>人口增长率 PGR</td><td>{pgr:.5f}/年</td></tr>
<tr><td><b>SDG 11.3.1（LCR/PGR）</b></td><td><b>{float(lp):.3f}</b></td></tr></table>
<p>比值&gt;1 表示城市扩张快于人口增长（土地消耗低效）。</p>
<h2>不确定性</h2><p>合成演示数据仅验证管线契约，不构成指标结论；真实评估须以 GHSL R2023A + 官方边界执行。</p>
<h2>来源</h2><p>run://<code>{src.get('source_run', '—')}</code> · recipe <code>{src.get('recipe', '—')}</code> · params <code>{json.dumps(src.get('params', {}), ensure_ascii=False)}</code></p>
</body></html>"""
    rp = out / "report.html"
    rp.write_text(html, encoding="utf-8")
    return {"report": str(rp)}


# --------------------------------------------------------------------------- #
# 其他公共算子（注册即可用）
# --------------------------------------------------------------------------- #
def zonal_statistics(params: dict, context) -> dict:
    raster, zones = params["raster"], params["zones"]
    stats = (params.get("stats") or "mean,sum,min,max").split(",")
    out = _out_dir(params, "zonal")
    feats = json.loads(Path(zones).read_text(encoding="utf-8"))["features"]
    with rasterio.open(raster) as ds:
        arr = ds.read(1)
        rows = []
        for i, f in enumerate(feats):
            gm = geometry_mask([f["geometry"]], out_shape=ds.shape, transform=ds.transform, invert=True)
            v = arr[gm & ~np.isnan(arr)] if np.issubdtype(arr.dtype, np.floating) else arr[gm]
            if v.size == 0:
                continue
            vals = {"zone": i, "name": f.get("properties", {}).get("name", str(i))}
            for s in stats:
                vals[s] = {"mean": float(v.mean()), "sum": float(v.sum()), "min": float(v.min()),
                           "max": float(v.max()), "count": int(v.size)}.get(s, "")
            rows.append(vals)
    tp = out / "stats_table.csv"
    with open(tp, "w", newline="", encoding="utf-8") as fh:
        if rows:
            wtr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wtr.writeheader()
            wtr.writerows(rows)
    return {"stats_table": str(tp), "stats_geojson": zones, "n_zones": len(rows)}


def ndvi(params: dict, context) -> dict:
    out = _out_dir(params, "ndvi")
    with rasterio.open(params["red"]) as rd, rasterio.open(params["nir"]) as nr:
        r, n = rd.read(1).astype("float64"), nr.read(1).astype("float64")
        den = n + r
        v = np.where(den > 0, (n - r) / np.where(den == 0, 1, den), np.nan)
        p = out / "ndvi.tif"
        with rasterio.open(p, "w", driver="GTiff", height=v.shape[0], width=v.shape[1],
                           count=1, dtype="float32", crs=rd.crs, transform=rd.transform, nodata=np.nan) as w:
            w.write(v.astype(np.float32), 1)
    return {"ndvi": str(p)}


def transition_matrix(params: dict, context) -> dict:
    out = _out_dir(params, "transition")
    with rasterio.open(params["t0"]) as d0, rasterio.open(params["t1"]) as d1:
        a, b = d0.read(1), d1.read(1)
        cls = sorted(set(np.unique(a)) | set(np.unique(b)))
        m = {str(int(i)): {str(int(j)): 0 for j in cls} for i in cls}
        for i in cls:
            for j in cls:
                m[str(int(i))][str(int(j))] = int(((a == i) & (b == j)).sum())
    p = out / "transition_matrix.json"
    p.write_text(json.dumps({"cell_count": m}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"matrix": str(p), "counts": m}


def water_extent(params: dict, context) -> dict:
    out = _out_dir(params, "water")
    with rasterio.open(params["raster"]) as ds:
        arr = ds.read(1)
        thr = float(params.get("threshold", 0.5))
        w = arr >= thr if np.issubdtype(arr.dtype, np.floating) else arr > 0
        km2 = float(w.sum()) * abs(ds.transform.a) * 111_000 * abs(ds.transform.e) * 111_000 / 1e6
    p = out / "water_extent.json"
    p.write_text(json.dumps({"extent_km2": km2, "cells": int(w.sum())}), encoding="utf-8")
    return {"extent_km2": km2, "report": str(p)}


HANDLERS = {
    "sdg.data.boundary.chn-cities": fetch_boundary,
    "sdg.skill.raster.clip-stack": clip_stack,
    "sdg.skill.urban.lcrpgr": lcrpgr,
    "sdg.skill.report.render": report_render,
    "sdg.skill.raster.zonal-statistics": zonal_statistics,
    "sdg.skill.index.ndvi": ndvi,
    "sdg.skill.land.transition-matrix": transition_matrix,
    "sdg.skill.water.water-extent": water_extent,
}

# 与 cards/skill/*.yaml 的对应（注册进 GeoNode 时把卡挂到 skill 上）
SKILL_CARDS = {
    "sdg.skill.raster.clip-stack": "cards/skill/raster.clip-stack.yaml",
    "sdg.skill.urban.lcrpgr": "cards/skill/urban.lcrpgr.yaml",
    "sdg.skill.report.render": "cards/skill/report.render.yaml",
    "sdg.skill.raster.zonal-statistics": "cards/skill/raster.zonal-statistics.yaml",
}


def register_all(node, root: Path | str, with_data_proxy: bool = True) -> int:
    """把算子注册进 GeoNode（skill 名=卡 id）。返回注册数。"""
    root = Path(root)
    n = 0
    for name, handler in HANDLERS.items():
        if name == "sdg.data.boundary.chn-cities" and not with_data_proxy:
            continue
        card = None
        cp = SKILL_CARDS.get(name)
        if cp and (root / cp).exists():
            from geonexus.geocard import load_geocard

            card = load_geocard(root / cp)
        node.register_skill(
            name=name,
            handler=handler,
            description=(card.description if card else f"SDGNode operator {name}")[:200],
            geocard=card,
        )
        n += 1
    return n
