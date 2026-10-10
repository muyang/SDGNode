#!/usr/bin/env python3
"""P0 · 批量注册与评审治理：38 卡 + 1 Recipe → 共享 Registry。

流程（对齐 DATA_REGISTRATION.md 治理语义）：
  ① register(status="pending")   —— 评审前对发现不可见
  ② list_cards(status="pending") —— 管理员评审队列
  ③ approve(...)                 —— 批准后进入 search/geo.describe
  ④ Recipe：HTTP 模式注册（pending→approve）；注册中心未开 recipe 目录时回退文件目录模式
  ⑤ search 冒烟：capability / type / bbox（武汉）三查
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _hit_ids(hits) -> list[str]:
    """search 命中项形如 {"entry": {"card": {...}}} —— 防御性取 id。"""
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8790")
    ap.add_argument("--api-key", default=os.environ.get("SDGNODE_REGISTRY_KEY", "sdgnode-dev-key"))
    ap.add_argument("--node-url", default="http://127.0.0.1:8791")
    ap.add_argument("--recipes-catalogue", default=str(ROOT / "state" / "recipes.json"))
    ap.add_argument("--by", default="sdgnode-ci")
    ap.add_argument("--refresh", action="store_true", help="先注销再重注册（更新 node_url 元数据）")
    ap.add_argument(
        "--sdk-src",
        default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"),
    )
    args = ap.parse_args()
    sys.path.insert(0, args.sdk_src)

    from geonexus.geocard import load_geocard
    from geonexus.recipe import load_recipe
    from geonexus.registry import RegistryClient

    files = sorted((ROOT / "cards").rglob("*.yaml"))
    cards = [load_geocard(f) for f in files]
    print(f"loaded {len(cards)} cards from {len(files)} files")

    registered = skipped = approved = 0
    with RegistryClient(args.url, api_key=args.api_key) as rc:
        print("registry health:", rc.health())

        # ① pending 注册（--refresh 先注销，规避 409 并更新 node_url；重复注册按冲突容错计数）
        for card in cards:
            if args.refresh:
                try:
                    rc.unregister(card.id)
                except Exception:  # noqa: BLE001
                    pass
            try:
                rc.register(card, node_url=args.node_url, status="pending")
                registered += 1
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                print(f"  register skip {card.id}: {exc}")

        # ② 评审队列
        pending = rc.list_cards(status="pending")
        print(f"review queue: {len(pending)} pending card(s)")

        # ③ 批准
        for card in cards:
            try:
                rc.approve(card.id, note="P0 批量准入（scripts/validate_cards.py 四层质量门通过）", by=args.by)
                approved += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  approve skip {card.id}: {exc}")

        # ④ Recipe 注册与批准
        recipe = load_recipe(ROOT / "recipes" / "sdg-11-3-1-lcrpgr.yaml")
        recipe_http_ok = False
        try:
            res = rc.register_recipe(
                recipe.to_dict(),
                node_url="sdgnode",
                status="pending",
                submitted_by=args.by,
                replace=True,
            )
            try:
                rc.approve_recipe(recipe.id, note="P0 准入", by=args.by)
            except TypeError:
                rc.approve_recipe(recipe.id)
            recipe_http_ok = True
            print(f"recipe registered via HTTP: {res.get('id', recipe.id)}")
        except Exception as exc:  # noqa: BLE001
            print(f"recipe HTTP registration failed ({exc}) → fallback to file catalogue")

        if not recipe_http_ok:
            from geonexus.recipe import RecipeRegistry

            reg = RecipeRegistry(args.recipes_catalogue)
            reg.register(recipe, provider_url="sdgnode", status="pending", submitted_by=args.by, replace=True)
            for m in ("approve_recipe", "approve"):
                if hasattr(reg, m):
                    getattr(reg, m)(recipe.id, note="P0 准入", by=args.by) if m == "approve_recipe" else getattr(reg, m)(recipe.id)
                    break
            print(f"recipe registered via file catalogue: {args.recipes_catalogue}")

        # ⑤ 检索冒烟（只返回 approved）
        n_approved = len(rc.list_cards())
        s1 = rc.search(capability="water-extent-change")
        s2 = rc.search(type="model")
        s3 = rc.search(bbox=[114.0, 30.3, 114.6, 30.8])  # 武汉
        print("\n--- search smoke ---")
        print(f"approved total : {n_approved}")
        print(f"cap=water-extent-change : {_hit_ids(s1)}")
        print(f"type=model              : {_hit_ids(s2)}")
        print(f"bbox=Wuhan              : {_hit_ids(s3)}")
        try:
            recipes = rc.list_recipes()
            print(f"recipes in registry     : {_recipe_ids(recipes)}")
        except Exception as exc:  # noqa: BLE001
            print(f"list_recipes: {exc}")

    print(f"\nDONE: registered={registered} skipped={skipped} approved={approved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
