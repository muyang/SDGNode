#!/usr/bin/env python3
"""P0 · MCP 桥（Streamable HTTP）：把 SDGNode 能力面暴露给 MCP 客户端（LLM 助手）。

与 start_sdg_node.py 装载同一套卡/Recipe，另起一个进程跑官方 mcp_adapter.run_http：
LLM 客户端由此获得 geo_capabilities / geo_describe / geo_execute / geo_plan 等 MCP 工具。
"""
from __future__ import annotations

import argparse
import inspect
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from start_sdg_node import ROOT, build_node  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--name", default="sdg-node-mcp")
    ap.add_argument("--recipes", default=str(ROOT / "state" / "recipes.json"))
    ap.add_argument("--with-skills", action="store_true", help="注册 sdgnode_skills 算子（geo_execute 可经 MCP 调用）")
    ap.add_argument(
        "--sdk-src",
        default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"),
    )
    args = ap.parse_args()

    node, cards, rr = build_node(args.name, args.host, args.port, args.recipes, args.sdk_src, args.with_skills)
    from geonexus.mcp_adapter import run_http

    sig = inspect.signature(run_http)
    kwargs: dict = {}
    if "host" in sig.parameters:
        kwargs["host"] = args.host
    if "port" in sig.parameters:
        kwargs["port"] = args.port
    print(
        f"[mcp-bridge] cards={len(cards)} recipes={len(rr) if rr is not None else 0} "
        f"→ MCP Streamable HTTP http://{args.host}:{args.port} (run_http params: {list(sig.parameters)})",
        flush=True,
    )
    run_http(node.server, **kwargs)  # 阻塞
    return 0


if __name__ == "__main__":
    sys.exit(main())
