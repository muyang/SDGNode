#!/usr/bin/env python3
"""P1 · 管线 1：STAC collection 级采集 → GeoCard（fixture 离线模式 + live 网络模式）。

- fixture（默认，离线可用）：读 SDK examples/stac/sentinel2_item_example.json，
  走 adapters.stac.stac_item_to_geocard 转换 → 重写为 SDGNode 命名 → 写 cards/harvest/。
- live：--url 指定 STAC API（如 CDSE/EarthSearch 的 items URL），httpx 拉一页
  features → 同管线转换（本沙箱 GitHub/外网受限，失败时给出明确提示）。
- 产出的卡立即用 SDK schema 复核（jsonschema + load_geocard）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_DEFAULT = os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src")


def _slug(text: str) -> str:
    return re.sub(r"[._-]+", "-", text.lower()).strip("-")[:60]


def _to_card_dict(item: dict, collection: str | None) -> dict:
    from geonexus.adapters.stac import stac_item_to_geocard

    try:
        card = stac_item_to_geocard(item, collection=collection) if collection else stac_item_to_geocard(item)
    except TypeError:
        card = stac_item_to_geocard(item)
    d = card.to_dict() if hasattr(card, "to_dict") else card.dict()
    base = collection or str(item.get("collection") or item.get("id", "item"))
    d["id"] = f"sdg.data.harvest.{_slug(base)}"
    d.setdefault("tags", []).append("harvested")
    d.setdefault("provenance", {})["lineage"] = f"pipeline-1 STAC harvest ({'fixture' if not base.startswith('http') else 'live'})"
    # 采集来源未声明合规 → 按"未知永不 public"原则默认 restricted，评审批准后再收紧
    comp = d.setdefault("compliance", {})
    comp.setdefault("sensitivity", "restricted")
    comp.setdefault("sovereignty", "intl")
    return d


def _emit(card_dict: dict, out_dir: Path) -> Path:
    import yaml

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{card_dict['id'].split('sdg.data.harvest.')[-1]}.yaml"
    path.write_text(
        "# P1 管线1 · STAC 采集产物（harvest_stac.py 生成，勿手改）\n"
        + yaml.safe_dump(card_dict, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _verify(path: Path) -> str:
    from geonexus.geocard import load_geocard

    card = load_geocard(path)
    return f"{card.id} ({card.type}) OK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="live 模式：STAC API items/collection URL")
    ap.add_argument("--collection", default=None)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--fixture", default=r"D:\Repos\GeoNexus\GeoNexus-SDK\examples\stac\sentinel2_item_example.json")
    ap.add_argument("--out", default=str(ROOT / "cards" / "harvest"))
    ap.add_argument("--sdk-src", default=SDK_DEFAULT)
    args = ap.parse_args()
    sys.path.insert(0, args.sdk_src)

    out_dir = Path(args.out)
    items: list[dict] = []
    if args.url:
        try:
            import httpx

            resp = httpx.get(args.url, params={"limit": args.limit}, timeout=20)
            resp.raise_for_status()
            items = resp.json().get("features", [])
            print(f"live: fetched {len(items)} item(s) from {args.url}")
        except Exception as exc:  # noqa: BLE001
            print(f"live 模式失败（沙箱网络受限属预期）：{exc}\n→ 回退 fixture 模式")
    if not items:
        fx = Path(args.fixture)
        if not fx.exists():
            print(f"fixture 不存在：{fx}", file=sys.stderr)
            return 1
        items = [json.loads(fx.read_text(encoding="utf-8"))]
        print(f"fixture: loaded {fx}")

    written = []
    for it in items:
        try:
            cd = _to_card_dict(it, args.collection)
        except Exception as exc:  # noqa: BLE001
            print(f"转换失败（不产出半成品卡）：{exc}")
            return 1
        p = _emit(cd, out_dir)
        written.append(_verify(p))
    print(f"\nharvest OK：{len(written)} 张卡 → {out_dir}")
    for w in written:
        print("  ", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
