#!/usr/bin/env python3
"""SDGNode · GeoNexus Platform 能力节点启动器。

能力节点三件事（默认开，可用开关关闭）：
1. **注册**：把本节点全部 GeoCard + GeoSkill `advertise` 到平台 registry
   （节点级重宣：先注销再注册，保证条目 node_url 指向本节点实时地址）；
2. **自述算力**：开机构造 type:compute 自注册卡（真实 CPU/内存探测，GPU 诚实声明），
   endpoint 指向同机模型服务基址，供 resolve_compute_capabilities / invoke_model 门禁发现；
3. **委托**：`set_registry` 绑定平台——引用非本节点资产的 geo.execute 请求按 owner 一跳转发，
   本节点也可作为任意已注册资产的联邦入口。

其余：装载 cards/ 全量 GeoCard、sdgnode_skills 算子（--with-skills）、Recipe 目录（geo.plan）。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_node(name: str, host: str, port: int, recipes: str | None, sdk_src: str, with_skills: bool = False):
    """构建装载了 SDGNode 卡库与 Recipe 目录的 GeoNode（供本脚本与 MCP 桥共用）。"""
    if sdk_src and Path(sdk_src).exists():
        sys.path.insert(0, sdk_src)
    from geonexus.geocard import load_geocard
    from geonexus.geonode import GeoNode

    recipe_registry = None
    if recipes and Path(recipes).exists():
        from geonexus.recipe import RecipeRegistry

        recipe_registry = RecipeRegistry(recipes)
    node = GeoNode(name=name, host=host, port=port, recipe_registry=recipe_registry)
    cards = [load_geocard(f) for f in sorted((ROOT / "cards").rglob("*.yaml"))]
    node.register_geocards(cards)
    n_skills = 0
    if with_skills:
        sys.path.insert(0, str(ROOT))
        from sdgnode_skills import register_all

        n_skills = register_all(node, ROOT)
    node._sdgnode_counts = (len(cards), n_skills)  # 供打印
    return node, cards, recipe_registry


def register_to_platform(node, registry_url: str, endpoint: str, api_key: str | None,
                        refresh: bool, self_compute_endpoint: str | None) -> dict:
    """平台注册：（可选重宣）+ 自注册算力卡 + advertise 卡与算子。返回摘要。

    算力卡特殊：它向平台申报的是"模型会在哪里运行"——resolve_compute_capabilities
    优先读条目的 node_url，所以这张卡单独以 node_url=模型服务基址 注册；
    随后的 node.advertise 对它撞 409 自动跳过，节点其余卡以 GeoMCP 地址为 node_url。
    """
    summary = {"endpoint": endpoint, "refreshed": 0, "self_compute": None}
    geo_card = None
    if self_compute_endpoint:
        sys.path.insert(0, str(ROOT))
        from sdgnode_skills.self_compute import build_self_compute_card

        card = build_self_compute_card(self_compute_endpoint, node.name, api_base=endpoint)
        from geonexus.geocard import GeoCard

        geo_card = GeoCard.model_validate(card)
        node.register_geocard(geo_card)  # 本地也装载：geo.describe 可见自己的算力声明

    from geonexus.registry import RegistryClient

    if refresh:
        with RegistryClient(registry_url, api_key=api_key) as rc:
            for c in node.geocard_registry.list_cards():
                try:
                    rc.unregister(c.id)
                    summary["refreshed"] += 1
                except Exception:  # noqa: BLE001
                    pass  # 不在平台上的卡，注册时新添即可
            for s in node.skill_registry.list_skills():
                try:
                    rc.unregister_skill(s.name)
                except Exception:  # noqa: BLE001
                    pass
    if geo_card is not None:
        with RegistryClient(registry_url, api_key=api_key) as rc:
            rc.register(geo_card, node_url=self_compute_endpoint, status="approved")
        summary["self_compute"] = self_compute_endpoint
    node.advertise(registry_url, endpoint=endpoint, api_key=api_key)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="sdg-node")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--endpoint", default=None, help="对外宣告的本节点地址（默认 http://host:port）")
    ap.add_argument("--recipes", default=str(ROOT / "state" / "recipes.json"))
    ap.add_argument("--registry", default=None, help="平台 Registry URL（注册+委托）")
    ap.add_argument("--api-key", default=os.environ.get("SDGNODE_REGISTRY_KEY"),
                    help="平台写端点 API-Key（advertise 需要）")
    ap.add_argument("--no-advertise", action="store_true", help="只委托不注册（默认带 --registry 即 advertise）")
    ap.add_argument("--refresh", action="store_true", help="重宣：先注销平台旧条目再注册（node_url 保持实时）")
    ap.add_argument("--with-skills", action="store_true", help="注册 sdgnode_skills 算子（geo.execute 可用）")
    ap.add_argument("--no-self-compute", action="store_true", help="不构造自注册算力卡")
    ap.add_argument("--model-endpoint", default="http://127.0.0.1:8801",
                    help="算力卡 endpoint=同机模型服务基址（门禁 retarget 目标）")
    ap.add_argument(
        "--sdk-src",
        default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"),
    )
    args = ap.parse_args()

    node, cards, rr = build_node(args.name, args.host, args.port, args.recipes, args.sdk_src, args.with_skills)
    endpoint = args.endpoint or f"http://{args.host}:{args.port}"

    if args.registry:
        node.set_registry(args.registry)  # 委托：非本节点资产 → owner 一跳转发
        if not args.no_advertise:
            model_ep = None if args.no_self_compute else args.model_endpoint
            info = register_to_platform(node, args.registry, endpoint, args.api_key, args.refresh, model_ep)
            print(f"[sdg-node] advertised to platform {args.registry} as {endpoint} "
                  f"(refreshed={info['refreshed']})", flush=True)

    n_recipes = len(rr) if rr is not None else 0
    n_skills = getattr(node, "_sdgnode_counts", (0, 0))[1]
    print(
        f"[sdg-node] cards={len(cards)} skills={n_skills} recipes={n_recipes} "
        f"→ GeoMCP {endpoint}/geomcp（阻塞运行，Ctrl-C 停止）",
        flush=True,
    )
    node.run()  # 阻塞
    return 0


if __name__ == "__main__":
    sys.exit(main())
