#!/usr/bin/env python3
"""P2 验收 · 模型调用闭环（MODEL.md 四步主流程全走 SDK 真代码）。

T1 osdg 成功路径（CPU 匹配 → InferenceProvider → 输出契约）
T2 pm25 成功路径（AOD 栅格 → 代理公式 → 产物落盘）
T3 samgeo 拒绝路径（GPU 需求 vs 纯 CPU 池 → no_compatible_compute + 理由 + **零字节外发**）
T4 prithvi 批作业（protocol=batch → submit→poll→collect，验证门禁 retarget 真实改址）
T5 注册中心算力发现（registry_url → resolve_compute_capabilities → 门禁按目录里的 compute 卡判定）
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import httpx  # noqa: E402
import uvicorn  # noqa: E402


def _serve(app_obj, host: str, port: int) -> uvicorn.Server:
    cfg = uvicorn.Config(app_obj, host=host, port=port, log_level="error")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    return srv


def _wait(url: str, timeout: float = 15.0) -> bool:
    for _ in range(int(timeout * 5)):
        try:
            if httpx.get(url, timeout=1.5).status_code < 500:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    return False


def _card_with_endpoint(sdk, rel_path: str, endpoint: str):
    from geonexus.geocard import GeoCard, load_geocard

    d = load_geocard(ROOT / rel_path).to_dict()
    d.setdefault("access", {})["endpoint"] = endpoint
    return GeoCard.model_validate(d)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svc-port", type=int, default=8801)
    ap.add_argument("--reg-port", type=int, default=8802)
    ap.add_argument("--sdk-src", default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"))
    args = ap.parse_args()
    sys.path.insert(0, args.sdk_src)
    sys.path.insert(0, str(ROOT))

    from geonexus.model import BatchProvider, InferenceProvider, invoke_model
    from geonexus.recipe import load_recipe  # noqa: F401  (保证路径一致，备用)
    from geonexus.resource import ComputeCapability

    # ---- 服务：模型服务 + 临时（无持久化）注册中心 ----
    from services.model_provider import app as model_app

    svc = _serve(model_app, "127.0.0.1", args.svc_port)
    assert _wait(f"http://127.0.0.1:{args.svc_port}/health"), "model service not up"
    print(f"[p2] model service up : http://127.0.0.1:{args.svc_port}")

    results: list[tuple[str, bool, str]] = []

    def note(name: str, ok: bool, msg: str):
        results.append((name, ok, msg))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg[:220]}")

    base = f"http://127.0.0.1:{args.svc_port}"

    def stats() -> dict:
        try:
            return httpx.get(f"{base}/__stats", timeout=5).json()
        except Exception:  # noqa: BLE001
            return {}

    # ---- T1 OSDG 成功 ----
    osdg = _card_with_endpoint(None, "cards/model/osdg.classifier-v2.yaml", f"{base}/osdg/invoke")
    caps_cpu = [ComputeCapability(node_url=f"{base}/osdg/invoke", cpu=16, memory_gb=64, gpu=None)]
    out = invoke_model(
        osdg,
        inputs={"text": "城市空气质量监测显示空气污染致死率上升，公共健康与气候排放治理是重点，统计能力建设需要国际伙伴合作"},
        capabilities=caps_cpu,
    )
    ok = out.status == "succeeded" and "sdg_scores" in out.outputs
    note("T1 osdg invoke succeeded", ok, f"status={out.status} matched_sdgs={out.outputs.get('matched_sdgs')} err={out.error}")

    # ---- T2 PM2.5 成功（真读栅格）----
    demo = ROOT / "state" / "demo" / "武汉"
    if not (demo / "built_up_2020.tif").exists():
        sys.path.insert(0, str(ROOT))
        from sdgnode_skills import synth

        synth.ensure("武汉", ROOT / "state" / "demo")
    pm = _card_with_endpoint(None, "cards/model/pm25.gbdt-v1.yaml", f"{base}/pm25/invoke")
    caps_pm = [ComputeCapability(node_url=f"{base}/pm25/invoke", cpu=16, memory_gb=64, gpu=None)]
    out2 = invoke_model(
        pm,
        inputs={
            "aod_grid": str(demo / "built_up_2020.tif"),
            "meteorology": {"blh": "era5.blh.tif", "ws10": "era5.ws.tif"},
            "period": "2020",
            "bbox": [114.0, 30.2, 114.7, 30.9],
        },
        capabilities=caps_pm,
    )
    ok2 = out2.status == "succeeded" and "pm25_grid" in out2.outputs
    note("T2 pm25 invoke succeeded", ok2, f"status={out2.status} pm25_mean={out2.outputs.get('pm25_mean')} err={out2.error}")

    # ---- T3 samgeo 门禁拒绝 + 零字节外发 ----
    sam = _card_with_endpoint(None, "cards/model/sam.sam2-geo.yaml", f"{base}/samgeo")
    before = stats()
    out3 = invoke_model(
        sam,
        inputs={"image": "any.tif"},
        capabilities=caps_cpu,  # 纯 CPU 池，samgeo 要 1xT4 → 必须拒绝
    )
    after = stats()
    zero_bytes = before == after and after.get("/samgeo", 0) == 0
    ok3 = (
        out3.status == "failed"
        and out3.error_code == "no_compatible_compute"
        and bool(out3.reasons)
        and zero_bytes
    )
    note("T3 gate rejection + zero bytes", ok3, f"error_code={out3.error_code} reasons={out3.reasons[:2]} stats_delta={ {k: after.get(k,0)-before.get(k,0) for k in after} }")

    # ---- T4 prithvi 批作业（batch provider + retarget 改址）----
    pri = _card_with_endpoint(None, "cards/model/prithvi.eo2-600m-tl.yaml", f"{base}/prithvi/jobs")
    caps_gpu = [ComputeCapability(node_url=f"{base}/prithvi/jobs", cpu=32, memory_gb=128, gpu="1xA100")]
    providers = {
        "inference": InferenceProvider(base),   # 泛化起点，靠门禁结论 retarget
        "batch": BatchProvider(base, poll_interval=0.2),
    }
    out4 = invoke_model(
        pri,
        inputs={"chips": ["hls_a.tif", "hls_b.tif"], "time_indices": [1, 2], "head": "flood", "bbox": [114.0, 30.2, 114.7, 30.9]},
        capabilities=caps_gpu,
        providers=providers,
    )
    ok4 = out4.status == "succeeded" and "class_map" in out4.outputs and out4.provider == "batch"
    note("T4 prithvi batch job", ok4, f"status={out4.status} provider={out4.provider} compute={out4.compute_node} class_map={out4.outputs.get('class_map')}")

    # ---- T5 注册中心算力发现 ----
    reg_ok = False
    try:
        from geonexus.registry import RegistryClient
        from geonexus.registry.server import RegistryServer

        srv_obj = RegistryServer(name="sdg-p2-registry")
        reg = _serve(srv_obj.create_app(), "127.0.0.1", args.reg_port)
        assert _wait(f"http://127.0.0.1:{args.reg_port}/health"), "registry not up"
        with RegistryClient(f"http://127.0.0.1:{args.reg_port}") as rc:
            for rel in ("cards/compute/local.cpu-batch.yaml", "cards/compute/local.gpu-a10.yaml"):
                c = _card_with_endpoint(None, rel, base)  # node_url 指向本地演示服务
                rc.register(c, node_url=base, status="approved")
            n = len(rc.search(type="compute"))
        out5 = invoke_model(osdg, inputs={"text": "水与卫生"}, registry_url=f"http://127.0.0.1:{args.reg_port}")
        reg_ok = out5.status == "succeeded" and bool(out5.compute_node)
        note("T5 registry compute discovery", reg_ok, f"compute_cards={n} status={out5.status} retargeted_to={out5.compute_node} err={out5.error}")
        reg.should_exit = True
    except Exception as exc:  # noqa: BLE001
        note("T5 registry compute discovery", False, f"exception: {exc}")

    svc.should_exit = True
    fails = [n for n, ok, _ in results if not ok]
    print(f"\n===== P2 验收：{len(results) - len(fails)}/{len(results)} PASS =====")
    for n in fails:
        print("  FAILED:", n)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
