#!/usr/bin/env python3
"""P1 验收 · GeoNode 装载算子技能后，真实 geo.execute 走通公共算子。

单进程内：GeoNode(start_in_thread) → GeoMCPClient → geo.capabilities(skills) →
geo.execute zonal-statistics（合成两期建成区）→ 断言返回工件。
证明：cards/skill/*.yaml 契约与 sdgnode_skills handler 对齐，节点执行面可用。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sdk-src",
        default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"),
    )
    ap.add_argument("--port", type=int, default=0, help="0=随机端口")
    args = ap.parse_args()
    sys.path.insert(0, args.sdk_src)
    sys.path.insert(0, str(ROOT))

    os.environ.setdefault("SDGNODE_DEMO_DIR", str(ROOT / "state" / "demo"))

    # 直接构建带技能的节点
    from geonexus.geocard import load_geocard
    from geonexus.geomcp.client import GeoMCPClient
    from geonexus.geonode import GeoNode
    from sdgnode_skills import register_all, synth

    node = GeoNode(name="sdg-node-p1", host="127.0.0.1", port=args.port or 8899)
    cards = [load_geocard(f) for f in sorted((ROOT / "cards").rglob("*.yaml"))]
    node.register_geocards(cards)
    n_skills = register_all(node, ROOT)
    server = node.start_in_thread("127.0.0.1", args.port or 8899)
    server.wait_until_ready()
    port = server.port  # property
    base = f"http://127.0.0.1:{port}"
    print(f"[p1] node up: cards={len(cards)} skills={n_skills} at {base}")

    d = synth.ensure("武汉", ROOT / "state" / "demo")
    ok = True
    try:
        with GeoMCPClient(base) as gc:
            caps = gc.capabilities()
            skill_names = sorted(s["name"] for s in caps.get("skills", []))
            print(f"[p1] geo.capabilities → skills({len(skill_names)}): {skill_names}")
            assert "sdg.skill.urban.lcrpgr" in skill_names, "lcrpgr 未注册"

            res = gc.execute(
                skill="sdg.skill.raster.zonal-statistics",
                params={"raster": d["built_up_t1"], "zones": d["aoi"], "stats": "mean,sum"},
            )
            payload = json.dumps(res, ensure_ascii=False, default=str)
            print(f"[p1] geo.execute zonal-statistics → {payload[:260]}")
            outs = res.get("outputs") or res.get("result") or res
            table = (outs or {}).get("stats_table") if isinstance(outs, dict) else None
            if not (table and Path(str(table)).exists()):
                print("[p1] FAIL: stats_table 缺失")
                ok = False

            res2 = gc.execute(
                skill="sdg.skill.index.ndvi",
                params={"red": d["built_up_t0"], "nir": d["built_up_t1"]},
            )
            print(f"[p1] geo.execute ndvi(代理栅格) → {json.dumps(res2, ensure_ascii=False, default=str)[:200]}")
    finally:
        server.stop()

    print("P1 NODE OK" if ok else "P1 NODE FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
