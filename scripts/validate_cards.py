#!/usr/bin/env python3
"""SDGNode 卡片库与 Recipe 库校验（P0 质量门）。

四层校验：
  L1 JSON Schema    SDK schemas/geocard.schema.json（draft 2020-12，严格校验）
  L2 SDGNode Profile 命名规范(profile/naming.yaml) + 能力词表(profile/capabilities-vocabulary.yaml)
                     + geonexus:sdg 扩展(profile/sdg-extension.schema.json) + 合规最低要求
                     + 模型卡 provider 协议映射（MODEL.md：未知协议 SDK 会明确报错 → 这里提前拦截）
  L3 SDK 实加载      geonexus.geocard.load_geocard（官方 loader + pydantic 模型）
                     + ContractValidator 自检（卡对自身声明的 bbox/时间窗必须 satisfied）
                     + effective_visibility（复合卡可见性继承，missing 组件 → 警告）
  L4 Recipe          geonexus.recipe.load_recipe + materialize 冒烟（样例参数 → RunPlan 拓扑序）
                     + requires/引用完整性

用法：
    python scripts/validate_cards.py [--sdk-src D:\\Repos\\GeoNexus\\GeoNexus-SDK\\src]
环境变量：GEONEXUS_SDK_SRC 覆盖 SDK 源码路径。
退出码：0 = 通过（允许 WARN/INFO）；1 = 存在 ERROR。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

# 模型卡 access.protocol → provider 映射（docs/MODEL.md §5.3；其余协议 SDK 明确报错）
MODEL_PROTOCOLS = {"http", "https", "rest", "inference", "batch", "job", "oge-job", "https+batch", ""}


def load_profile(profile_dir: Path) -> tuple[dict, set[str], dict]:
    ext_schema = json.loads((profile_dir / "sdg-extension.schema.json").read_text(encoding="utf-8"))
    vocab_doc = yaml.safe_load((profile_dir / "capabilities-vocabulary.yaml").read_text(encoding="utf-8"))
    vocab = {t for dom in vocab_doc["domains"].values() for t in dom["terms"]}
    naming = yaml.safe_load((profile_dir / "naming.yaml").read_text(encoding="utf-8"))
    return ext_schema, vocab, naming


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdk-src", default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"))
    ap.add_argument("--cards-dir", default=str(ROOT / "cards"))
    ap.add_argument("--recipes-dir", default=str(ROOT / "recipes"))
    ap.add_argument("--profile-dir", default=str(ROOT / "profile"))
    ap.add_argument("--sample-params", default='{"year": 2020, "city": "武汉"}')
    args = ap.parse_args()

    sdk_src = Path(args.sdk_src)
    if sdk_src.exists():
        sys.path.insert(0, str(sdk_src))  # 本地 SDK 源码优先于已安装的发布版

    import jsonschema

    schema_path = sdk_src.parent / "schemas" / "geocard.schema.json"
    geocard_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    known_sections = set(geocard_schema["properties"])
    ext_schema, vocab, naming = load_profile(Path(args.profile_dir))
    id_patterns = {k: re.compile(v) for k, v in naming["id_patterns"].items()}

    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    card_files = sorted(Path(args.cards_dir).rglob("*.yaml"))
    if not card_files:
        print(f"no card files under {args.cards_dir}", file=sys.stderr)
        return 1

    raw: dict[str, tuple[Path, dict[str, Any]]] = {}

    # ---------- L1 + L2 ----------
    validator = jsonschema.Draft202012Validator(geocard_schema)
    ext_validator = jsonschema.Draft202012Validator(ext_schema)
    for f in card_files:
        rel = f.relative_to(ROOT).as_posix()
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            errors.append(f"{rel}: YAML 解析失败: {e}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{rel}: 卡片必须是 mapping")
            continue
        cid = str(doc.get("id", "<missing>"))
        if cid in raw:
            errors.append(f"{rel}: [L2 唯一性] id '{cid}' 与 {raw[cid][0].name} 重复")
        raw[cid] = (f, doc)

        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            loc = "/".join(map(str, err.path)) or "<root>"
            errors.append(f"{rel}: [L1 schema] {loc}: {err.message}")

        ctype = doc.get("type")
        pat = id_patterns.get(ctype)
        if pat is None:
            errors.append(f"{rel}: [L2 命名] 未知 type '{ctype}'")
        elif not pat.match(cid):
            errors.append(f"{rel}: [L2 命名] id '{cid}' 不符合 {ctype} 规范 /{naming['id_patterns'][ctype]}/")

        for k, val in doc.items():
            if k in known_sections:
                continue
            if not isinstance(val, (dict, list)):
                errors.append(f"{rel}: [L2 扩展] 顶层扩展键 '{k}' 必须是 object/array（GeoCard 扩展政策）")
            if not (k.startswith("geonexus:") or k.startswith("sdgnode:")):
                warnings.append(f"{rel}: [L2 扩展] 顶层键 '{k}' 未命名空间化（建议 geonexus:* / sdgnode:*）")

        sdg = doc.get("geonexus:sdg")
        if sdg is not None:
            for err in ext_validator.iter_errors(sdg):
                loc = "/".join(map(str, err.path)) or "<root>"
                errors.append(f"{rel}: [L2 geonexus:sdg] {loc}: {err.message}")
            for cap in sdg.get("requires_capabilities", []) or []:
                if cap not in vocab:
                    errors.append(f"{rel}: [L2 词表] requires_capabilities '{cap}' 不在词表 v0")

        for cap in doc.get("capabilities") or []:
            name = cap["name"] if isinstance(cap, dict) else cap
            if name not in vocab:
                errors.append(f"{rel}: [L2 词表] capability '{name}' 不在词表 v0")

        if ctype in ("data", "model"):
            if "license" not in doc:
                warnings.append(f"{rel}: [L2 合规] {ctype} 卡缺少 license")
            if "compliance" not in doc:
                warnings.append(f"{rel}: [L2 合规] {ctype} 卡缺少 compliance")

        if ctype == "model":
            proto = (doc.get("access") or {}).get("protocol", "")
            if proto not in MODEL_PROTOCOLS:
                errors.append(f"{rel}: [L2 model] access.protocol '{proto}' 无 provider 映射（SDK 将明确报错）")
            if "runtime" not in doc:
                errors.append(f"{rel}: [L2 model] 缺 runtime —— 算力门禁 match_resource 依赖该声明")
            if not any(i.get("required") for i in doc.get("inputs") or []):
                warnings.append(f"{rel}: [L2 model] inputs 无 required 项 —— 输入契约无法拒绝空请求")

    # ---------- L3 SDK 实加载 ----------
    loaded: dict[str, Any] = {}
    sdk_ok = True
    try:
        from geonexus.geocard import ContractValidator, effective_visibility, load_geocard
    except Exception as e:  # pragma: no cover
        sdk_ok = False
        warnings.append(f"[L3] geonexus SDK 导入失败，跳过 SDK 层校验: {e}")

    if sdk_ok:
        for cid, (f, _doc) in raw.items():
            rel = f.relative_to(ROOT).as_posix()
            try:
                loaded[cid] = load_geocard(f)  # validate=True：SDK 官方 schema 校验再走一遍
            except Exception as e:
                errors.append(f"{rel}: [L3 SDK load] {e}")

        cv = ContractValidator()
        for cid, card in loaded.items():
            sp = getattr(card, "spatial", None)
            tp = getattr(card, "temporal", None)
            if sp is not None and getattr(sp, "bbox", None) and tp is not None and getattr(tp, "start", None):
                try:
                    res = cv.check(
                        card,
                        bbox=list(sp.bbox),
                        crs=sp.crs or "EPSG:4326",
                        start=str(tp.start),
                        end=str(tp.end) if getattr(tp, "end", None) else None,
                    )
                    if not getattr(res, "satisfied", True):
                        errors.append(f"{cid}: [L3 自检] ContractValidator 对自身声明不满足: {res.reasons}")
                except Exception as e:
                    warnings.append(f"{cid}: [L3 自检] 跳过（{type(e).__name__}: {e}）")

        for cid, card in loaded.items():
            if getattr(card, "type", None) == "workflow":
                try:
                    rep = effective_visibility(card, lambda i: loaded.get(i))
                    infos.append(
                        f"{cid}: [L3 可见性] effective={rep.visibility} visible={rep.visible} missing={rep.missing}"
                    )
                    if not rep.visible:
                        warnings.append(
                            f"{cid}: [L3 可见性] 内容组件 {rep.missing} 不可解析 → 复合卡对客户端不可见（404 语义）"
                        )
                except Exception as e:
                    warnings.append(f"{cid}: [L3 可见性] 检查失败（{type(e).__name__}: {e}）")

    # ---------- 引用完整性（composition / related_cards） ----------
    for cid, (f, doc) in raw.items():
        rel = f.relative_to(ROOT).as_posix()
        for comp in (doc.get("composition") or {}).get("components") or []:
            ref = comp.get("id")
            required = comp.get("required", True)
            if ref not in raw:
                suffix = "（required=true → 依可见性继承整卡不可见，注册应拒绝）" if required else "（required=false → 不参与门控）"
                (errors if required else infos).append(f"{rel}: [引用] composition 组件 '{ref}' 未在卡库解析{suffix}")
        for ref in (doc.get("geonexus:sdg") or {}).get("related_cards") or []:
            if str(ref).startswith("recipe://"):
                continue  # recipe 地址在 L4 校验
            if ref not in raw:
                warnings.append(f"{rel}: [引用] geonexus:sdg.related_cards '{ref}' 未在卡库解析（外部/待注册）")

    # ---------- L4 Recipe ----------
    recipes_dir = Path(args.recipes_dir)
    recipe_files = sorted(recipes_dir.rglob("*.yaml")) if recipes_dir.exists() else []
    recipe_sdk = True
    try:
        from geonexus.recipe import load_recipe, materialize
    except Exception as e:  # pragma: no cover
        recipe_sdk = False
        if recipe_files:
            warnings.append(f"[L4] geonexus.recipe 导入失败，退化为结构自检: {e}")

    sample_params = json.loads(args.sample_params)
    for f in recipe_files:
        rel = f.relative_to(ROOT).as_posix()
        if recipe_sdk:
            try:
                recipe = load_recipe(f)
            except Exception as e:
                errors.append(f"{rel}: [L4 load_recipe] {e}")
                continue
            for rid in getattr(recipe, "requires", None) or []:
                if rid not in raw:
                    warnings.append(f"{rel}: [L4 requires] '{rid}' 不在卡库（外部/待注册）")
            try:
                plan = materialize(recipe, dict(sample_params), run_id="validate-smoke")
                order = plan.graph.topological_order()
                infos.append(f"{rel}: [L4 materialize] OK → {order}")
            except Exception as e:
                errors.append(f"{rel}: [L4 materialize] {e}")
        else:
            try:
                doc = yaml.safe_load(f.read_text(encoding="utf-8"))
                steps = {s["id"] for s in doc.get("steps", [])}
                if doc.get("entrypoint") not in steps:
                    errors.append(f"{rel}: [L4 结构] entrypoint 无效")
                names = {p["name"] for p in doc.get("params", [])}
                for s in doc.get("steps", []):
                    for d in s.get("depends_on") or []:
                        if d not in steps:
                            errors.append(f"{rel}: [L4 结构] step {s['id']} 依赖不存在的 {d}")
                    for v in list((s.get("params") or {}).values()):
                        m = re.fullmatch(r"\$\{params\.(\w+)\}", str(v))
                        if m and m.group(1) not in names:
                            errors.append(f"{rel}: [L4 结构] step {s['id']} 引用未声明参数 {m.group(1)}")
            except Exception as e:
                errors.append(f"{rel}: [L4 结构] {e}")

    # ---------- 汇总 ----------
    types: dict[str, int] = {}
    for _cid, (_f, doc) in raw.items():
        types[doc.get("type", "?")] = types.get(doc.get("type", "?"), 0) + 1
    tsum = ", ".join(f"{k}={v}" for k, v in sorted(types.items()))
    print(f"卡片 {len(raw)} 张（{tsum}）；Recipe {len(recipe_files)} 份；SDK: {'本地源码 ' + str(sdk_src) if sdk_ok else '不可用'}")
    for m in infos:
        print(f"  [INFO] {m}")
    for m in warnings:
        print(f"  [WARN] {m}")
    for m in errors:
        print(f"  [FAIL] {m}")
    print(f"\n结果: {len(errors)} errors / {len(warnings)} warnings / {len(infos)} infos")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
