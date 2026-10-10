#!/usr/bin/env python3
"""最终验收 · 单进程串起 P0/P1/P2 全链路（线程内服务，跑完即停，不留驻进程）。

P0：registry(38+卡 pending→approve) + GeoNode(装载卡/技能/Recipe) + MCP 桥 → 发现链路
P1：geo.plan→materialize；公共算子 geo.execute；e2e 已在 run_recipe_e2e 验收（此处做轻量复核）
P2：invoke_model 成功/门禁拒绝/批作业/注册中心算力发现（复用 check_model_invoke 服务面）
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import httpx  # noqa: E402
import uvicorn  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def _serve(app_obj, host: str, port: int) -> uvicorn.Server:
    srv = uvicorn.Server(uvicorn.Config(app_obj, host=host, port=port, log_level="error"))
    threading.Thread(target=srv.run, daemon=True).start()
    return srv


def _wait(url: str, timeout: float = 20.0):
    for _ in range(int(timeout * 5)):
        try:
            r = httpx.get(url, timeout=1.5)
            if r.status_code < 500:
                return r
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    raise RuntimeError(f"service not ready: {url}")


def note(name: str, ok: bool, msg: str = ""):
    RESULTS.append((name, ok, msg))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg[:200]}")


def _port_free(p: int, host: str = "127.0.0.1") -> bool:
    import socket

    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((host, p)) != 0


def _pick(base: int) -> int:
    p = base
    while not _port_free(p):
        p += 1
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry-port", type=int, default=8790)
    ap.add_argument("--node-port", type=int, default=8791)
    ap.add_argument("--mcp-port", type=int, default=9000)
    ap.add_argument("--svc-port", type=int, default=8801)
    ap.add_argument("--api-key", default="sdgnode-dev-key")
    ap.add_argument("--sdk-src", default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"))
    args = ap.parse_args()
    import logging

    for noisy in ("httpx", "httpcore", "mcp", "geonexus", "uvicorn"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    sys.path.insert(0, args.sdk_src)
    sys.path.insert(0, str(ROOT))

    from geonexus.geocard import load_geocard
    from geonexus.geomcp.client import GeoMCPClient
    from geonexus.geonode import GeoNode
    from geonexus.recipe import RecipeRegistry, load_recipe
    from geonexus.registry import RegistryClient
    from geonexus.registry.server import RegistryServer

    from sdgnode_skills import register_all

    rport, nport, mport, sport = args.registry_port, args.node_port, args.mcp_port, args.svc_port
    rurl, nurl, surl = f"http://127.0.0.1:{rport}", f"http://127.0.0.1:{nport}", f"http://127.0.0.1:{sport}"

    # ---------- 拉起（registry 若在跑则复用；node/桥/模型服务择空闲端口新起）----------
    reg_reuse = reg = None
    try:
        h = httpx.get(f"{rurl}/health", timeout=2).json()
        reg_reuse = h.get("service") == "geonexus-registry"
    except Exception:  # noqa: BLE001
        pass
    if not reg_reuse:
        rport = _pick(rport)
        rurl = f"http://127.0.0.1:{rport}"
        reg_app = RegistryServer(name="sdg-final", persist_path=str(ROOT / "state" / "registry.json"),
                                 api_keys=[args.api_key],
                                 recipe_persist_path=str(ROOT / "state" / "recipes.json")).create_app()
        reg = _serve(reg_app, "127.0.0.1", rport)
    _wait(f"{rurl}/health")
    print(f"[final] registry @ {rurl} ({'复用' if reg_reuse else '新起'})")

    nport = _pick(8792)
    nurl = f"http://127.0.0.1:{nport}"
    node = GeoNode(name="sdg-node-final", host="127.0.0.1", port=nport,
                   recipe_registry=RecipeRegistry(ROOT / "state" / "recipes.json"))
    cards = [load_geocard(f) for f in sorted((ROOT / "cards").rglob("*.yaml"))]
    node.register_geocards(cards)
    n_skills = register_all(node, ROOT)
    node_svr = node.start_in_thread("127.0.0.1", nport)
    node_svr.wait_until_ready()

    from geonexus.mcp_adapter import create_streamable_http_app

    mport = _pick(9001)
    mcp = _serve(create_streamable_http_app(node.server), "127.0.0.1", mport)
    _wait(f"http://127.0.0.1:{mport}/mcp", 5) if False else None  # MCP 根探测不可用 GET，交给桥测试

    sport = _pick(8801)
    surl = f"http://127.0.0.1:{sport}"
    from services.model_provider import app as model_app

    svc = _serve(model_app, "127.0.0.1", sport)
    _wait(f"{surl}/health")
    print(f"[final] up: cards={len(cards)} skills={n_skills} node={nport} mcp={mport} svc={sport}")

    # ---------- P0 · 注册治理 ----------
    files = sorted((ROOT / "cards").rglob("*.yaml"))
    with RegistryClient(rurl, api_key=args.api_key) as rc:
        fresh = 0
        for f in files:
            c = load_geocard(f)
            try:
                rc.unregister(c.id)
            except Exception:  # noqa: BLE001
                pass
            try:
                rc.register(c, node_url=nurl, status="pending")
                fresh += 1
            except Exception as exc:  # noqa: BLE001
                print("  reg skip", c.id, exc)
        pend = len(rc.list_cards(status="pending"))
        note("P0 pending queue", pend == len(files), f"pending={pend}/{len(files)}")
        for f in files:
            c = load_geocard(f)
            try:
                rc.approve(c.id, note="最终验收（含 P2 实测模型卡）", by="sdgnode-ci")
            except Exception:  # noqa: BLE001
                pass
        approved = len(rc.list_cards())
        note("P0 approved count", approved >= len(files), f"approved={approved}")
        hit = rc.search(capability="pm25-estimation")
        note("P0 search capability", len(hit) >= 1, f"pm25-estimation hits={len(hit)}")

    # ---------- P0 · GeoMCP 发现 ----------
    with GeoMCPClient(nurl) as gc:
        caps = gc.capabilities()
        note("P0 geo.capabilities", len(caps.get("geocards", [])) >= len(files) and "geo.plan" in caps.get("methods", []),
             f"geocards={len(caps.get('geocards', []))} methods={len(caps.get('methods', []))}")
        pl = gc.plan("recipe://sdg/11-3-1-lcrpgr@1.0.0", {"year": 2020, "city": "武汉"}, run_id="final")
        note("P0/P1 geo.plan materialize", len(pl.get("tasks", [])) == 4, f"tasks={len(pl.get('tasks', []))} fixed={list(pl.get('fixed_params', {}))}")

    # ---------- P1 · geo.execute ----------
    from sdgnode_skills import synth

    d = synth.ensure("武汉", ROOT / "state" / "demo")
    with GeoMCPClient(nurl) as gc:
        try:
            ex = gc.execute(skill="sdg.skill.raster.zonal-statistics",
                            params={"raster": d["built_up_t1"], "zones": d["aoi"], "stats": "mean,sum"})
            note("P1 geo.execute zonal", ex.get("status") == "ok", str(ex)[:120])
        except Exception as exc:  # noqa: BLE001
            note("P1 geo.execute zonal", False, str(exc))

    # ---------- P2 · 模型闭环 ----------
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_model_invoke as cmi  # 复用其卡片改写与断言逻辑（导入无副作用，main 有 __main__ 守护）

    from geonexus.model import BatchProvider, InferenceProvider, invoke_model
    from geonexus.resource import ComputeCapability

    osdg = cmi._card_with_endpoint(None, "cards/model/osdg.classifier-v2.yaml", f"{surl}/osdg/invoke")
    out = invoke_model(osdg, inputs={"text": "空气污染影响城市公共健康"}, capabilities=[ComputeCapability(node_url=f"{surl}/osdg/invoke", cpu=16, memory_gb=64, gpu=None)])
    note("P2 osdg via invoke_model", out.status == "succeeded", f"matched={out.outputs.get('matched_sdgs')}")

    sam = cmi._card_with_endpoint(None, "cards/model/sam.sam2-geo.yaml", f"{surl}/samgeo")
    before = httpx.get(f"{surl}/__stats", timeout=5).json()
    out2 = invoke_model(sam, inputs={"image": "x.tif"}, capabilities=[ComputeCapability(node_url=f"{surl}/osdg/invoke", cpu=16, memory_gb=64, gpu=None)])
    after = httpx.get(f"{surl}/__stats", timeout=5).json()
    note("P2 gate rejection zero-bytes", out2.error_code == "no_compatible_compute" and before == after, f"code={out2.error_code} reasons={len(out2.reasons)}")

    pri = cmi._card_with_endpoint(None, "cards/model/prithvi.eo2-600m-tl.yaml", f"{surl}/prithvi/jobs")
    out3 = invoke_model(pri, inputs={"chips": ["a.tif"], "time_indices": [1], "head": "flood"},
                        capabilities=[ComputeCapability(node_url=f"{surl}/prithvi/jobs", cpu=32, memory_gb=128, gpu="1xA100")],
                        providers={"batch": BatchProvider(surl, poll_interval=0.2), "inference": InferenceProvider(surl)})
    note("P2 batch submit→collect", out3.status == "succeeded" and out3.provider == "batch", f"node={out3.compute_node}")

    # ---------- P2 · 算力发现（registry 里的 compute 卡）----------
    with RegistryClient(rurl, api_key=args.api_key) as rc:
        for cid in ("sdg.compute.local.cpu-batch", "sdg.compute.local.gpu-a10"):
            try:
                rc.unregister(cid)
            except Exception:  # noqa: BLE001
                pass
        for rel in ("cards/compute/local.cpu-batch.yaml", "cards/compute/local.gpu-a10.yaml"):
            c = cmi._card_with_endpoint(None, rel, surl)
            rc.register(c, node_url=surl, status="approved")
    out4 = invoke_model(osdg, inputs={"text": "水与卫生设施"}, registry_url=rurl)
    note("P2 compute discovery via registry", out4.status == "succeeded" and bool(out4.compute_node), f"retarget={out4.compute_node}")

    # 恢复 compute 卡的正式端点元数据（演示改写不落盘）
    with RegistryClient(rurl, api_key=args.api_key) as rc:
        for cid in ("sdg.compute.local.cpu-batch", "sdg.compute.local.gpu-a10"):
            try:
                rc.unregister(cid)
            except Exception:  # noqa: BLE001
                pass
        for rel in ("cards/compute/local.cpu-batch.yaml", "cards/compute/local.gpu-a10.yaml"):
            rc.register(load_geocard(ROOT / rel), node_url=nurl, status="approved")

    # ---------- MCP 桥 ----------
    import asyncio

    async def bridge_probe():
        import mcp.client.streamable_http as sh
        from mcp import ClientSession

        ctx = getattr(sh, "streamablehttp_client", None) or sh.streamable_http_client
        async with ctx(f"http://127.0.0.1:{mport}/mcp") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                tl = await session.list_tools()
                return sorted(t.name for t in tl.tools)

    try:
        names = asyncio.run(bridge_probe())
        note("P0 mcp bridge tools", {"geo_capabilities", "geo_plan", "geo_describe"} <= set(names), f"tools={names}")
    except BaseException as exc:  # noqa: BLE001
        note("P0 mcp bridge tools", False, str(exc)[:150])

    for s in (svc, mcp, reg):
        if s is not None:
            s.should_exit = True
    node_svr.stop()

    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n===== 最终验收：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS =====")
    for n in fails:
        print("  FAILED:", n)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
