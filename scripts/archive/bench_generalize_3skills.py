#!/usr/bin/env python3
"""Benchmark cold-start generalized skills vs reference baseline."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if val and key not in os.environ:
            os.environ[key] = val

from skillos.skills.bench_cohorts import GENERALIZE_SKILLS as GENERALIZE_COHORT

# Generalization cohort (new domains)
GENERALIZE_SKILLS: list[dict[str, Any]] = list(GENERALIZE_COHORT)

# Original reference cohort (for comparison)
REFERENCE_SKILLS: list[dict[str, Any]] = [
    {"name": "电商客服退款处理", "anchor_tasks": ("workflow-064",)},
    {"name": "GitHub Pull", "anchor_tasks": ("software-dependency-audit", "code-review-002")},
    {"name": "CSV数据清洗助手", "anchor_tasks": ("data-processing-036", "data-processing-037")},
]


def _eval_anchor_tasks(
    skill_name: str,
    content: str,
    task_ids: tuple[str, ...],
    categories: tuple[str, ...],
    *,
    domain_template: str | None = None,
) -> list[dict]:
    from skillos.skillsbench_tasks import run_task_evaluation

    rows = []
    for tid in task_ids:
        w = run_task_evaluation(
            tid,
            skill_content=content,
            model="",
            route_by_category=True,
            bench_categories=list(categories),
            skill_name=skill_name,
            domain_template=domain_template,
        )
        wo = run_task_evaluation(tid, skill_content="", model="")
        rows.append({
            "task_id": tid,
            "with_score": w.get("score"),
            "without_score": wo.get("score"),
            "delta": (w.get("score") or 0) - (wo.get("score") or 0),
            "skill_used": w.get("skill_used"),
            "missed": (w.get("dimensions") or {}),
        })
    return rows


def _bench_skill(spec: dict[str, Any]) -> dict[str, Any]:
    from skillos.benchmark_local import run_quick8_for_skill
    from skillos.evaluation.save_gate import run_domain_smoke_suite
    from skillos.knowledge.skill_routing import load_skill_routing_info
    from skillos.skills.pattern_miner import check_dna_compliance
    from skillos.skills.post_extraction_bench import repair_skill
    from skillos.skills.skill_store import load_skill_raw

    name = spec["name"]
    path = ROOT / "skills" / name / "SKILL.md"
    if not path.exists():
        return {"skill": name, "error": "skill_not_found"}

    repair = repair_skill(name, preserve_moe=True)
    raw = load_skill_raw(name)
    meta = raw.get("meta") or {}
    body = raw.get("body", "")
    info = load_skill_routing_info(str(path))
    content = info["content"]
    categories = meta.get("bench_categories") or info["bench_categories"]

    dna = check_dna_compliance(content)
    smoke = run_domain_smoke_suite(
        name, body,
        bench_categories=categories,
        domain_template=meta.get("domain_template") or spec.get("domain_template"),
    )
    q8_full = run_quick8_for_skill(name, domain_only=False)
    q8_domain = run_quick8_for_skill(name, domain_only=True)

    anchors = _eval_anchor_tasks(
        name, content,
        spec.get("anchor_tasks", ()),
        tuple(categories) if categories else spec.get("bench_categories", ()),
        domain_template=meta.get("domain_template") or spec.get("domain_template"),
    )
    anchor_delta = sum(a["delta"] for a in anchors)
    anchor_max = len(anchors) * 100

    full_delta = q8_full["with_skill_score"] - q8_full["without_skill_score"]
    domain_delta = q8_domain.get("domain_delta") or (
        q8_domain["with_skill_score"] - q8_domain["without_skill_score"]
    )

    return {
        "skill": name,
        "domain_template": meta.get("domain_template") or spec.get("domain_template"),
        "bench_categories": categories,
        "dna_compliance": dna.get("score"),
        "dna_passed": dna.get("passed"),
        "bench_quality": meta.get("bench_quality"),
        "repair": {"dna_score": repair.get("dna_score")},
        "smoke_suite": smoke,
        "smoke_min": min((r["with_score"] for r in smoke), default=0),
        "quick8_full": {
            "delta": full_delta,
            "improvement_pct": q8_full.get("improvement_pct"),
            "skills_injected": q8_full.get("skills_injected"),
            "tasks": q8_full.get("tasks"),
            "per_task": q8_full.get("per_task"),
        },
        "quick8_domain": {
            "delta": domain_delta,
            "improvement_pct": q8_domain.get("domain_improvement_pct"),
            "skills_injected": q8_domain.get("skills_injected"),
            "tasks": q8_domain.get("tasks"),
        },
        "anchor_tasks": anchors,
        "anchor_delta_total": anchor_delta,
        "anchor_improvement_pp": round(anchor_delta / max(1, anchor_max - sum(a["without_score"] for a in anchors)) * 100, 1)
        if anchors else 0,
    }


def _summarize_cohort(rows: list[dict]) -> dict[str, Any]:
    valid = [r for r in rows if not r.get("error")]
    if not valid:
        return {"count": 0}
    full_deltas = [r["quick8_full"]["delta"] for r in valid]
    domain_deltas = [r["quick8_domain"]["delta"] for r in valid]
    anchor_deltas = [r["anchor_delta_total"] for r in valid]
    smoke_ok = sum(1 for r in valid if r.get("smoke_min", 0) >= 80)
    dna_ok = sum(1 for r in valid if (r.get("dna_passed") or 0) >= 5)
    inject_rates = []
    domain_inject_rates = []
    for r in valid:
        inj = r["quick8_full"].get("skills_injected") or 0
        tasks = r["quick8_full"].get("tasks") or 1
        inject_rates.append(inj / max(1, tasks))
        d_inj = r["quick8_domain"].get("skills_injected") or 0
        d_tasks = r["quick8_domain"].get("tasks") or 1
        domain_inject_rates.append(d_inj / max(1, d_tasks))
    return {
        "count": len(valid),
        "median_quick8_delta": sorted(full_deltas)[len(full_deltas) // 2],
        "median_quick8_domain_delta": sorted(domain_deltas)[len(domain_deltas) // 2],
        "mean_quick8_delta": round(sum(full_deltas) / len(full_deltas), 1),
        "median_anchor_delta": sorted(anchor_deltas)[len(anchor_deltas) // 2],
        "smoke_pass_rate": round(smoke_ok / len(valid), 2),
        "dna_pass_rate": round(dna_ok / len(valid), 2),
        "mean_inject_rate": round(sum(inject_rates) / len(inject_rates), 2),
        "mean_domain_inject_rate": round(sum(domain_inject_rates) / len(domain_inject_rates), 2),
    }


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        print("ERROR: DEEPSEEK_API_KEY required")
        return 1

    ts = int(time.time())
    print("=== Generalization benchmark ===\n")

    print("--- New domains (cold start) ---")
    gen_rows = []
    for spec in GENERALIZE_SKILLS:
        print(f"  Benchmarking {spec['name']}…")
        gen_rows.append(_bench_skill(spec))

    print("\n--- Reference skills (baseline) ---")
    ref_rows = []
    for spec in REFERENCE_SKILLS:
        print(f"  Benchmarking {spec['name']}…")
        ref_rows.append(_bench_skill(spec))

    gen_summary = _summarize_cohort(gen_rows)
    ref_summary = _summarize_cohort(ref_rows)

    payload = {
        "timestamp": ts,
        "experiment": "generalization_cold_start",
        "generalize": {"skills": gen_rows, "summary": gen_summary},
        "reference": {"skills": ref_rows, "summary": ref_summary},
        "comparison": {
            "delta_quick8_gen_vs_ref": gen_summary.get("median_quick8_delta", 0) - ref_summary.get("median_quick8_delta", 0),
            "generalization_verdict": _verdict(gen_summary, ref_summary),
        },
    }

    out = ROOT / "data" / "benchmarks" / f"generalize_bench_{ts}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print("\n=== Summary ===")
    print(f"  新领域 median Quick8 Δ: {gen_summary.get('median_quick8_delta')} (domain: {gen_summary.get('median_quick8_domain_delta')}, ref: {ref_summary.get('median_quick8_delta')})")
    print(f"  新领域 inject率: full={gen_summary.get('mean_inject_rate')} domain={gen_summary.get('mean_domain_inject_rate')}")
    print(f"  新领域 anchor Δ total median: {gen_summary.get('median_anchor_delta')}")
    print(f"  新领域 smoke pass: {gen_summary.get('smoke_pass_rate')}  DNA≥5: {gen_summary.get('dna_pass_rate')}")
    print(f"  判定: {payload['comparison']['generalization_verdict']}")
    print(f"\nSaved: {out}")
    return 0


def _verdict(gen: dict, ref: dict) -> str:
    g_delta = gen.get("median_quick8_delta") or 0
    g_domain = gen.get("median_quick8_domain_delta") or 0
    r_delta = ref.get("median_quick8_delta") or 0
    smoke = gen.get("smoke_pass_rate") or 0
    anchor = gen.get("median_anchor_delta") or 0
    if g_domain >= 40 or g_delta >= 40:
        return "strong_generalization"
    if g_domain >= 50 or g_delta >= 25 or (g_delta >= r_delta * 0.5 and g_delta > 0):
        return "partial_generalization"
    if g_delta >= 0 and smoke >= 1.0 and anchor >= 20:
        return "partial_generalization"
    if g_delta > 0:
        return "weak_positive"
    if g_delta >= 0 and smoke >= 0.66:
        return "weak_positive"
    return "failed_generalization"


if __name__ == "__main__":
    raise SystemExit(main())
