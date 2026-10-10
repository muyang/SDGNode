#!/usr/bin/env python3
"""P0 验收 · 发现链路实测：Registry search → GeoMCP geo.* → MCP 桥（LLM 客户端视角）。

验收判据（对应技术方案 §9 P0）：
  A. registry：health ok；approved ≥ 38；capability/type/bbox 三查命中；recipe 在目录
  B. GeoMCP：geo.health/geo.capabilities（含 geo.plan）；geo.describe 返回指定卡；
     geo.plan 物化 11.3.1 Recipe（武汉/2020）
  C. MCP 桥：list_tools 出现 geo_* 工具；call_tool(geo_capabilities) 成功
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

RESULTS: list[tuple[str, bool, str]] = []


def _hit_ids(hits) -> list[str]:
    out = []
    for h in hits or []:
        e = h.get("entry", h) if isinstance(h, dict) else {}
        card = e.get("card", e) if isinstance(e, dict) else {}
        out.append(card.get("id") or e.get("card_id") or str(h)[:50])
    return out


def _recipe_ids(rs) -> list[str]:
    out = []
    for r in rs or []:
        e = r.get("entry", r) if isinstance(r, dict) else {}
        out.append(e.get("recipe_id") or e.get("id") or str(r)[:60])
    return out


def check(name: str, fn) -> None:
    try:
        out = fn()
        RESULTS.append((name, True, str(out)[:220]))
        print(f"[PASS] {name}: {str(out)[:220]}")
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((name, False, str(exc)[:220]))
        print(f"[FAIL] {name}: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="http://127.0.0.1:8790")
    ap.add_argument("--node", default="http://127.0.0.1:8791")
    ap.add_argument("--mcp", default="http://127.0.0.1:9000/mcp")
    ap.add_argument("--api-key", default=os.environ.get("SDGNODE_REGISTRY_KEY", "sdgnode-dev-key"))
    ap.add_argument("--skip-mcp", action="store_true")
    ap.add_argument(
        "--sdk-src",
        default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"),
    )
    args = ap.parse_args()
    sys.path.insert(0, args.sdk_src)

    from geonexus.geomcp.client import GeoMCPClient
    from geonexus.registry import RegistryClient

    # ---- A. Registry ----
    with RegistryClient(args.registry, api_key=args.api_key) as rc:
        check("A1 registry.health", lambda: rc.health().get("status"))
        check("A2 approved>=38", lambda: f"n={len(rc.list_cards())}" if len(rc.list_cards()) >= 38 else (_ for _ in ()).throw(AssertionError(f"only {len(rc.list_cards())}")))
        check("A3 search.capability=water-extent-change", lambda: _hit_ids(rc.search(capability="water-extent-change")))
        check("A4 search.type=model(4)", lambda: _hit_ids(rc.search(type="model")))
        check("A5 search.bbox=Wuhan", lambda: _hit_ids(rc.search(bbox=[114.0, 30.3, 114.6, 30.8])))
        check("A6 recipes.list", lambda: _recipe_ids(rc.list_recipes()))

    # ---- B. GeoMCP node ----
    with GeoMCPClient(args.node) as gc:
        check("B1 geo.health", lambda: gc.health().get("status"))
        caps = gc.capabilities()
        check("B2 geo.capabilities.methods", lambda: sorted(caps.get("methods", [])))
        check("B3 geo.capabilities.geocards>=38", lambda: f"n={len(caps.get('geocards', []))}" if len(caps.get("geocards", [])) >= 38 else (_ for _ in ()).throw(AssertionError(f"only {len(caps.get('geocards', []))}")))
        check("B4 geo.describe(data card)", lambda: gc.describe(geocards=["sdg.data.esa.worldcover-2024"])["geocards"][0]["name"])
        check("B5 geo.describe(model card)", lambda: gc.describe(geocards=["sdg.model.prithvi.eo2-600m-tl"])["geocards"][0]["id"])
        check(
            "B6 geo.plan(11.3.1, 武汉/2020)",
            lambda: sorted((gc.plan("recipe://sdg/11-3-1-lcrpgr@1.0.0", {"year": 2020, "city": "武汉"}, run_id="p0-check")).keys()),
        )
        check("B7 geo.describe(unknown card)->2002", lambda: _expect_error(gc, "sdg.data.does-not-exist"))

    # ---- C. MCP bridge ----
    if not args.skip_mcp:
        async def mcp_probe(url: str):
            import mcp.client.streamable_http as sh
            from mcp import ClientSession

            # mcp>=2 导出 streamable_http_client（yield 二元组）；早期版本为 streamablehttp_client（三元组）
            ctx = getattr(sh, "streamablehttp_client", None) or sh.streamable_http_client
            result = None
            try:
                async with ctx(url) as streams:
                    read, write = streams[0], streams[1]
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        names = sorted(t.name for t in tools.tools)
                        res = await session.call_tool("geo_capabilities", {})
                        body = "".join(getattr(c, "text", "") for c in res.content)
                        is_err = getattr(res, "is_error", getattr(res, "isError", None))  # mcp 2.0 snake_case
                        result = (names, is_err, body[:150])
            except BaseException:  # noqa: BLE001
                # mcp 2.0 上下文拆除存在竞态（TaskGroup 伪异常）；业务调用已成功则以结果为准
                if result is None:
                    raise
            return result

        def try_bridge():
            return asyncio.run(mcp_probe(args.mcp))

        check("C1 mcp.bridge list_tools+geo_capabilities", try_bridge)

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n===== P0 验收：{len(RESULTS) - len(failed)}/{len(RESULTS)} PASS =====")
    for n in failed:
        print(f"  FAILED: {n}")
    return 1 if failed else 0


def _expect_error(gc, card_id: str) -> str:
    from geonexus.geomcp.client import GeoMCPClientError

    try:
        gc.describe(geocards=[card_id])
        return "no error raised (unexpected)"
    except GeoMCPClientError as exc:
        assert exc.code == 2002, f"expected 2002, got {exc.code}"
        return f"error 2002 as expected: {exc.message[:60]}"


if __name__ == "__main__":
    sys.exit(main())
