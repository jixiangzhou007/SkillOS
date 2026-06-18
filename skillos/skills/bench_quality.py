"""Bench quality snapshot for skill frontmatter (save gate, DNA compliance, smoke)."""

from __future__ import annotations

import time
from typing import Any


def build_bench_quality_meta(
    skill_name: str,
    body: str,
    *,
    meta: dict[str, Any] | None = None,
    gate_meta: dict[str, Any] | None = None,
    dna_compliance_meta: dict[str, Any] | None = None,
    moe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute bench_quality block for YAML frontmatter."""
    from skillos.evaluation.save_gate import run_domain_smoke_suite
    from skillos.knowledge.skill_routing import infer_bench_categories
    from skillos.skills.pattern_miner import check_dna_compliance

    m = meta or {}
    categories = m.get("bench_categories") or infer_bench_categories(skill_name, body)
    domain_tpl = m.get("domain_template") or m.get("domain_template_id")

    dna = dna_compliance_meta
    if dna is None:
        report = check_dna_compliance(body)
        dna = {
            "score": report.get("score"),
            "passed": report.get("passed"),
            "total": report.get("total"),
            "all_passed": report.get("all_passed"),
        }

    gate = gate_meta
    if gate is None:
        suite = run_domain_smoke_suite(
            skill_name,
            body,
            bench_categories=categories,
            domain_template=domain_tpl,
        )
        min_score = min((r["with_score"] for r in suite), default=0)
        gate = {
            "smoke_pass": min_score >= 80,
            "min_with_score": min_score,
            "tasks": [r["task_id"] for r in suite],
        }

    out: dict[str, Any] = {
        "checked_at": int(time.time()),
        "dna_compliance": dna,
        "save_gate": gate,
    }
    if moe:
        moe_block: dict[str, Any] = {}
        for key in ("overall_score", "passed", "confidence", "dimensions", "boost_rounds"):
            val = moe.get(key)
            if val is not None and val != "":
                moe_block[key] = val
        if moe_block:
            out["moe"] = moe_block
    return out
