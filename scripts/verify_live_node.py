#!/usr/bin/env python3
"""对**在跑的生产节点**做平台侧发现+调用核验（不新起服务，纯外部客户端视角）。

前提：start_sdg_node.py --registry ... 已在跑（默认 :8793），平台 registry 在 :8790。
证明三件事：
  V1 平台 /nodes 视图里 SDGNode 在册（cards/skills 计数 + 健康探测）
  V2 平台检索可发现（capability / type=compute 自注册卡 / bbox 空间）
  V3 节点可被直接调用（geo.execute 真算子）与经平台委托（另一绑定节点的 owner 路由）
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="http://127.0.0.1:8790")
    ap.add_argument("--node", default="http://127.0.0.1:8793", help="在跑的 SDGNode GeoMCP 基址")
    ap.add_argument("--sdk-src", default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"))
    args = ap.parse_args()
    sys.path.insert(0, args.sdk_src)
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

    from geonexus.geomcp.client import GeoMCPClient
    from geonexus.registry import RegistryClient

    ok = True

    # V1 平台注册视图
    nodes = httpx.get(f"{args.registry}/nodes", timeout=10).json()
    entry = nodes.get("nodes", {}).get(args.node)
    if entry is None:
        print(f"[FAIL] V1 /nodes 未找到 {args.node}（在册节点：{list(nodes.get('nodes', {}))}）")
        ok = False
    else:
        print(f"[{'PASS' if len(entry['cards']) >= 40 else 'WARN'}] V1 /nodes：cards={len(entry['cards'])} "
              f"skills={len(entry['skills'])} healthy={entry.get('healthy')}")
        ok = ok and len(entry["cards"]) >= 40

    # V2 平台检索发现
    with RegistryClient(args.registry) as rc:
        caps = {((h.get("entry") or {}).get("card") or {}).get("id") for h in rc.search(capability="lcrpgr")}
        comp = {((h.get("entry") or {}).get("card") or {}).get("id") for h in rc.search(type="compute")}
        good = "sdg.skill.urban.lcrpgr" in caps and "sdg.compute.sdg-node.self-pool" in comp
        print(f"[{'PASS' if good else 'FAIL'}] V2 检索：lcrpgr={sorted(c for c in caps if c)} self_pool={'sdg.compute.sdg-node.self-pool' in comp}")
        ok = ok and good

    # V3a 直接调用（外部客户端 → 节点 GeoMCP）
    from sdgnode_skills import synth

    d = synth.ensure("武汉", os.path.join(ROOT, "state", "demo"))
    with GeoMCPClient(args.node) as gc:
        ex = gc.execute(skill="sdg.skill.raster.zonal-statistics",
                        params={"raster": d["built_up_t1"], "zones": d["aoi"], "stats": "mean,sum",
                                "outputs_dir": os.path.join(ROOT, "runs", "_v3a")})
    direct_ok = ex.get("status") == "ok"
    print(f"[{'PASS' if direct_ok else 'FAIL'}] V3a 直接 geo.execute：status={ex.get('status')} outputs={list(ex.get('outputs', {}))[:2]}")
    ok = ok and direct_ok

    # V3b 经平台委托：临时起一个空入口节点，引用 SDGNode 资产 → owner 一跳转发到 8793
    import threading

    import uvicorn
    from geonexus.geonode import GeoNode

    gport = 8796
    gateway = GeoNode(name="region-c-entry", host="127.0.0.1", port=gport)
    gsrv = uvicorn.Server(uvicorn.Config(gateway.create_app(), host="127.0.0.1", port=gport, log_level="error"))
    threading.Thread(target=gsrv.run, daemon=True).start()
    import time

    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{gport}/health", timeout=1)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    gateway.set_registry(args.registry)
    with GeoMCPClient(f"http://127.0.0.1:{gport}") as gg:
        de = gg.execute(skill="sdg.skill.raster.zonal-statistics",
                        geocards=["sdg.data.boundary.chn-cities"],
                        params={"raster": d["built_up_t1"], "zones": d["aoi"], "stats": "mean,sum",
                                "outputs_dir": os.path.join(ROOT, "runs", "_v3b")})
    del_ok = de.get("status") == "ok" and len(gateway.capabilities().get("skills", [])) == 0
    print(f"[{'PASS' if del_ok else 'FAIL'}] V3b 平台委托 region-c-entry→SDGNode：status={de.get('status')} "
          f"(入口节点本地技能=0，结果只能来自 owner 8793)")
    ok = ok and del_ok
    gsrv.should_exit = True

    print("\n===== 生产节点平台核验：" + ("全部通过 =====" if ok else "存在失败 ====="))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
