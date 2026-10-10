#!/usr/bin/env python3
"""能力节点验收 · SDGNode 在 GeoNexus Platform 注册→被发现→被调用（含跨节点委托）。

单进程线程内服务，跑完即停：
  platform registry（若在跑则复用）· SDGNode（40+卡+8算子+自注册算力卡，advertise 到平台）
  · 模型服务（算力卡 endpoint 所指）· region-b-gateway（**空节点**，仅绑定平台，作联邦入口）

C1 注册视图：/nodes 里 SDGNode 出现，cards/skills 计数正确，健康探测通过
C2 平台发现：按 capability/type 检索命中 SDGNode 资产（含自注册 compute 卡）
C3 直接调用：SDGNode GeoMCP geo.execute 成功
C4 委托调用：gateway 本地 0 技能、不持有任何卡，收到引用 SDGNode 资产的
   geo.execute → 按平台 node_url 一跳委托 → SDGNode 契约门+执行 → 原路返回
C5 算力自注册闭环：门禁按 registry 目录发现 SDGNode 自注册算力 → retarget 到其
   声明的模型服务 → invoke_model 成功
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import httpx  # noqa: E402
import uvicorn  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def note(name: str, ok: bool, msg: str = ""):
    RESULTS.append((name, ok, msg))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg[:220]}")


def _serve(app_obj, port: int) -> uvicorn.Server:
    srv = uvicorn.Server(uvicorn.Config(app_obj, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=srv.run, daemon=True).start()
    return srv


def _wait(url: str, timeout: float = 20.0):
    for _ in range(int(timeout * 5)):
        try:
            if httpx.get(url, timeout=1.5).status_code < 500:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    raise RuntimeError(f"service not ready: {url}")


def _port_free(p: int) -> bool:
    import socket

    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", p)) != 0


def _pick(base: int) -> int:
    p = base
    while not _port_free(p):
        p += 1
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="http://127.0.0.1:8790")
    ap.add_argument("--api-key", default=os.environ.get("SDGNODE_REGISTRY_KEY", "sdgnode-dev-key"))
    ap.add_argument("--sdk-src", default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"))
    args = ap.parse_args()
    for noisy in ("httpx", "httpcore", "mcp", "geonexus", "uvicorn"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    sys.path.insert(0, args.sdk_src)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))

    from geonexus.geocard import load_geocard
    from geonexus.geomcp.client import GeoMCPClient
    from geonexus.geonode import GeoNode
    from geonexus.model import invoke_model
    from geonexus.registry import RegistryClient
    from geonexus.registry.server import RegistryServer

    from start_sdg_node import build_node, register_to_platform

    rurl = args.registry

    # ---------- 平台 registry（复用或新起，新起带健康探测）----------
    reg = None
    reuse = False
    try:
        reuse = httpx.get(f"{rurl}/health", timeout=2).json().get("service") == "geonexus-registry"
    except Exception:  # noqa: BLE001
        pass
    if not reuse:
        rport = _pick(int(rurl.rsplit(":", 1)[1]))
        rurl = f"http://127.0.0.1:{rport}"
        reg = _serve(RegistryServer(name="sdg-platform", persist_path=str(ROOT / "state" / "registry.json"),
                                    api_keys=[args.api_key], health_probe=True,
                                    recipe_persist_path=str(ROOT / "state" / "recipes.json")).create_app(), rport)
    _wait(f"{rurl}/health")
    print(f"[node2platform] platform registry @ {rurl} ({'复用' if reuse else '新起 health_probe=on'})")

    # ---------- 模型服务（自注册算力卡的 endpoint 所指）----------
    sport = _pick(8801)
    surl = f"http://127.0.0.1:{sport}"
    from services.model_provider import app as model_app

    svc = _serve(model_app, sport)
    _wait(f"{surl}/health")

    # ---------- SDGNode 能力节点：装载 → 起服务 → 注册平台（含自注册算力）→ 委托绑定 ----------
    nport = _pick(8792)
    nurl = f"http://127.0.0.1:{nport}"
    node, cards, rr = build_node("sdg-node", "127.0.0.1", nport, str(ROOT / "state" / "recipes.json"), args.sdk_src, with_skills=True)
    node_svr = node.start_in_thread("127.0.0.1", nport)
    node_svr.wait_until_ready()
    node.set_registry(rurl)
    info = register_to_platform(node, rurl, endpoint=nurl, api_key=args.api_key,
                                refresh=True, self_compute_endpoint=surl)
    n_cards = node.geocard_registry.count()
    n_skills = node.skill_registry.count()
    print(f"[node2platform] SDGNode @ {nurl} 已注册：cards={n_cards} skills={n_skills}（refreshed={info['refreshed']}）")

    # ---------- 联邦入口 gateway：空节点，仅绑定平台 ----------
    gport = _pick(8795)
    gurl = f"http://127.0.0.1:{gport}"
    gateway = GeoNode(name="region-b-gateway", host="127.0.0.1", port=gport)
    gateway_svr = gateway.start_in_thread("127.0.0.1", gport)
    gateway_svr.wait_until_ready()
    gateway.set_registry(rurl)

    # ---------- C1 注册视图 ----------
    try:
        nodes_doc = httpx.get(f"{rurl}/nodes", timeout=10).json()
        entries = nodes_doc.get("nodes", nodes_doc) if isinstance(nodes_doc, dict) else nodes_doc
        mine = None
        if isinstance(entries, list):
            for e in entries:
                if e.get("node_url") == nurl or e.get("url") == nurl or e.get("node") == nurl:
                    mine = e
                    break
        elif isinstance(entries, dict):
            mine = entries.get(nurl)
        ok = mine is not None and len(mine.get("cards", [])) >= len(cards) and len(mine.get("skills", [])) >= n_skills
        note("C1 /nodes 注册视图含 SDGNode", ok, f"entry_keys={list(mine)[:6] if mine else None} "
             f"cards={len(mine.get('cards', [])) if mine else 0} skills={len(mine.get('skills', [])) if mine else 0} "
             f"healthy={mine.get('healthy') if mine else None}")
    except Exception as exc:  # noqa: BLE001
        note("C1 /nodes 注册视图含 SDGNode", False, f"exception: {exc}")

    # ---------- C2 平台发现 ----------
    def _hit_ids(hits: list) -> set:
        out = set()
        for h in hits:
            c = (h.get("entry") or {}).get("card") or h.get("card") or h
            cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            if cid:
                out.add(cid)
        return out

    with RegistryClient(rurl, api_key=args.api_key) as rc:
        ids = _hit_ids(rc.search(capability="lcrpgr"))
        ok2 = "sdg.skill.urban.lcrpgr" in ids  # capability 检索命中本节点算子卡
        comp_ids = _hit_ids(rc.search(type="compute"))
        ok2 = ok2 and "sdg.compute.sdg-node.self-pool" in comp_ids  # 自注册算力卡被发现
        # 知识卡 11.3.1 走 geonexus:sdg.requires_capabilities（非顶层 capabilities），
        # 用 bbox 检索验证空间可发现性（武汉应命中边界/夜光等 data 卡）
        bbox_hits = _hit_ids(rc.search(type="data", bbox=[114.0, 30.2, 114.7, 30.9]))
        ok2 = ok2 and len(bbox_hits) >= 1
        note("C2 平台检索命中（capability+compute+bbox）", ok2,
             f"lcrpgr={sorted(ids)} self_pool={'sdg.compute.sdg-node.self-pool' in comp_ids} "
             f"wuhan_data_hits={len(bbox_hits)}")

    # ---------- C3 直接调用 ----------
    from sdgnode_skills import synth

    d = synth.ensure("武汉", ROOT / "state" / "demo")
    with GeoMCPClient(nurl) as gc:
        ex = gc.execute(skill="sdg.skill.raster.zonal-statistics",
                        params={"raster": d["built_up_t1"], "zones": d["aoi"], "stats": "mean,sum",
                                "outputs_dir": str(ROOT / "runs" / "_c3")})
        note("C3 SDGNode 直接 geo.execute", ex.get("status") == "ok", f"status={ex.get('status')} outputs={list(ex.get('outputs', {}))}")

    # ---------- C4 跨节点委托调用（平台路由：gateway → SDGNode）----------
    gw_caps = gateway.capabilities()
    gw_skills = len(gw_caps.get("skills", []))
    with GeoMCPClient(gurl) as gg:
        de = gg.execute(skill="sdg.skill.raster.zonal-statistics",
                        geocards=["sdg.data.boundary.chn-cities"],
                        params={"raster": d["built_up_t1"], "zones": d["aoi"], "stats": "mean,sum",
                                "outputs_dir": str(ROOT / "runs" / "_c4")},
                        request_id="delegate-demo")
    ok4 = gw_skills == 0 and de.get("status") == "ok" and de.get("outputs")
    note("C4 联邦委托 gateway→SDGNode", bool(ok4),
         f"gateway本地skills={gw_skills}(必须0) 结果status={de.get('status')} outputs={list(de.get('outputs', {}))[:2]} "
         f"(卡片资产 owner=SDGNode，gateway 经平台 node_url 一跳委托)")

    # ---------- C5 算力自注册 → invoke 闭环 ----------
    static_ids = ["sdg.compute.local.cpu-batch", "sdg.compute.local.gpu-a10"]
    with RegistryClient(rurl, api_key=args.api_key) as rc:
        for cid in static_ids:  # 暂时收起静态声明，确保门禁只能命中自注册卡
            try:
                rc.unregister(cid)
            except Exception:  # noqa: BLE001
                pass
    osdg = load_geocard(ROOT / "cards" / "model" / "osdg.classifier-v2.yaml")
    out = invoke_model(osdg, inputs={"text": "城市空气污染与公共健康治理"}, registry_url=rurl)
    ok5 = out.status == "succeeded" and out.compute_node and surl in out.compute_node
    note("C5 平台算力发现→门禁→retarget→invoke", ok5,
         f"status={out.status} compute={out.compute_node} matched_sdgs={out.outputs.get('matched_sdgs')} err={out.error}")
    with RegistryClient(rurl, api_key=args.api_key) as rc:  # 恢复静态卡正式声明
        for rel in ("cards/compute/local.cpu-batch.yaml", "cards/compute/local.gpu-a10.yaml"):
            try:
                rc.register(load_geocard(ROOT / rel), node_url=nurl, status="approved")
            except Exception:  # noqa: BLE001
                pass

    # ---------- 收尾停服（保留平台上的注册状态：SDGNode 已在平台在册）----------
    for s in (svc, reg):
        if s is not None:
            s.should_exit = True
    gateway_svr.stop()
    node_svr.stop()

    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n===== 能力节点验收：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS =====")
    for n in fails:
        print("  FAILED:", n)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
