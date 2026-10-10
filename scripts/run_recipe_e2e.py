#!/usr/bin/env python3
"""P1 · 端到端执行 recipe://sdg/11-3-1-lcrpgr@1.0.0 —— 合成数据、真实契约链。

链路（每一步都走 SDK 真代码）：
  load_recipe → materialize(参数契约：reusable 传入 / fixed 默认注入)
  → 按拓扑序执行（handler 契约 = cards/skill/*.yaml；step:// 引用解析）
  → 报告产物 → GAAG report_card_from_run（来源四件套）
  → report_contract + validate_report（checksum/章节可核验）
  → 生成报告卡写入 cards/generated/ 并 load_geocard 复核
  → （registry 可达时）算子 skill 登记进共享 Registry
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="武汉")
    ap.add_argument("--year", type=int, default=2020)
    ap.add_argument("--registry", default="http://127.0.0.1:8790")
    ap.add_argument("--api-key", default=os.environ.get("SDGNODE_REGISTRY_KEY", "sdgnode-dev-key"))
    ap.add_argument("--node-url", default="http://127.0.0.1:8791")
    ap.add_argument(
        "--sdk-src",
        default=os.environ.get("GEONEXUS_SDK_SRC", r"D:\Repos\GeoNexus\GeoNexus-SDK\src"),
    )
    args = ap.parse_args()

    sys.path.insert(0, args.sdk_src)
    sys.path.insert(0, str(ROOT))

    from geonexus.gaag import (
        GAAGRegistry,
        ReportContractSource,
        register_report_contract,
        report_card_from_run,
        report_contract,
        scan_report,
        validate_report,
    )
    from geonexus.geocard import load_geocard
    from geonexus.recipe import load_recipe, materialize

    from sdgnode_skills import HANDLERS

    recipe = load_recipe(ROOT / "recipes" / "sdg-11-3-1-lcrpgr.yaml")
    run_id = f"run-sdg1131-{time.strftime('%Y%m%d-%H%M%S')}"
    plan = materialize(recipe, {"year": args.year, "city": args.city}, run_id=run_id)
    print(f"== plan {plan.run_id} ==")
    print("params:", json.dumps(plan.params, ensure_ascii=False))
    for t in plan.task_ids():
        print("task:", t, "→", plan.graph.task(t).spec["uses"])

    # 合成研究区（明确 synthetic；生产环境为 CAFE 下推）
    os.environ.setdefault("SDGNODE_DEMO_DIR", str(ROOT / "state" / "demo"))

    results: dict[str, dict] = {}
    source_meta = {
        "source_run": plan.run_id,
        "recipe": recipe.id,
        "params": plan.params,
        "data_snapshot": dict(recipe.data_snapshot or {}),
    }

    def resolve(ref: str):
        if str(ref).startswith("step://"):
            step, _, name = ref[len("step://"):].partition("/")
            return results.get(step, {}).get(name, ref)
        return ref

    for task_id in plan.task_ids():
        task = plan.graph.task(task_id)
        spec = task.spec
        step = task_id.split(":", 1)[1]
        uses = spec["uses"]
        handler = HANDLERS[uses]
        params = dict(spec.get("params") or {})
        params.setdefault("city", plan.params.get("city", args.city))
        # step:// 引用解析：task.inputs 是 TaskIO(ref/kind/from_task/field)
        resolved: dict[str, object] = {}
        for name, io in (getattr(task, "inputs", None) or {}).items():
            if getattr(io, "kind", "") == "task_output" and getattr(io, "from_task", None) in results:
                resolved[name] = results[io.from_task].get(io.field, getattr(io, "ref", name))
            else:
                resolved[name] = getattr(io, "ref", io)
        params["inputs"] = resolved
        for k, v in resolved.items():
            params.setdefault(k, v)
        out_dir = ROOT / "runs" / plan.run_id / step
        out_dir.mkdir(parents=True, exist_ok=True)
        params["outputs_dir"] = str(out_dir)
        if uses == "sdg.skill.report.render":
            params["source"] = source_meta
        ctx = type("Ctx", (), {"node_name": "sdgnode-local-runner", "run_id": plan.run_id})()
        outputs = handler(params, ctx)
        results[step] = outputs
        brief = {k: (v if not isinstance(v, str) else Path(v).name) for k, v in outputs.items()}
        print(f"[step {step}] {uses} → {json.dumps(brief, ensure_ascii=False, default=str)[:200]}")

    metrics = results["s3"]
    report_path = Path(results["s4"]["report"])
    print(f"\n== 指标结果（合成演示口径）==\nLCR={metrics['lcr']:.5f}/年  PGR={metrics['pgr']:.5f}/年  11.3.1={metrics['lcrpgr']:.3f}")

    # GAAG 报告合约链：卡 + 来源四件套 + 校验
    card = report_card_from_run(plan, report_path=str(report_path), title=f"SDG 11.3.1 {args.city} {args.year}", license="CC-BY-4.0")
    card.validate()
    src = ReportContractSource(
        source_run=plan.run_id,
        recipe=recipe.id,
        recipe_version=recipe.version,
        params=dict(plan.params),
        data_snapshot=dict(recipe.data_snapshot or {}),
        deliverables=recipe.deliverable_names(),
    )
    contract = report_contract(card, source=src, report_path=str(report_path))
    result = validate_report(contract)
    meta = scan_report(report_path)
    print(f"report contract satisfied={result.satisfied} reasons={getattr(result, 'reasons', [])}")
    print(f"checksum={meta['checksum'][:19]}… title={meta['title']!r} sections={meta['sections']}")
    if not result.satisfied:
        return 1

    greg = GAAGRegistry()
    contract2, reg_result = register_report_contract(greg, card, source=src, report_path=str(report_path))
    print(f"GAAG registered: {contract2.contract_id} (list={len(greg.list())})")

    gen_dir = ROOT / "cards" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    import yaml

    card_yaml = gen_dir / f"{card.id}.yaml"
    card_yaml.write_text(
        "# P1 运行产物 · GAAG report 合约卡（report_card_from_run 自动生成，勿手改）\n"
        + yaml.safe_dump(card.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    reloaded = load_geocard(card_yaml)
    print(f"generated report card: {reloaded.id} → {card_yaml} (load_geocard OK)")

    # 算子 skill 登记进共享 Registry（registry 可达时）
    try:
        from geonexus.registry import RegistryClient

        caps = {
            "sdg.skill.raster.clip-stack": ["raster-preprocess"],
            "sdg.skill.urban.lcrpgr": ["lcrpgr", "built-up-extent", "population-grid"],
            "sdg.skill.report.render": ["report-render"],
            "sdg.skill.raster.zonal-statistics": ["zonal-statistics"],
            "sdg.skill.index.ndvi": ["ndvi"],
            "sdg.skill.land.transition-matrix": ["transition-matrix"],
            "sdg.skill.water.water-extent": ["water-extent"],
        }
        with RegistryClient(args.registry, api_key=args.api_key) as rc:
            for name, cs in caps.items():
                try:
                    rc.register_skill(name, node_url=args.node_url, description=f"SDGNode operator {name}", capabilities=cs)
                except Exception as exc:  # noqa: BLE001
                    print(f"  skill register skip {name}: {exc}")
            skills = rc.list_skills()
            print(f"registry skills now: {len(skills)}")
    except Exception as exc:  # noqa: BLE001
        print(f"(registry 不可达，跳过 skill 登记: {exc})")

    print(f"\n== 证据链落盘 ==\nruns/{plan.run_id}/ (s1..s4) + report.html + cards/generated/{card.id}.yaml")
    print("E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
