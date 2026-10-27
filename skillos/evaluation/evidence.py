"""Minimal Evidence Card — claim counts + outcome smoke rows for Trust Tier UI."""

from __future__ import annotations

from typing import Any

from skillos.evaluation.trust_tier import compute_trust_tier, enrich_epistemic_with_trust
from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload


def build_evidence_card(
    skill_name: str,
    *,
    meta: dict[str, Any] | None = None,
    body: str = "",
) -> dict[str, Any]:
    """Assemble a compact evidence snapshot for API / result cards."""
    m = dict(meta or {})
    ep = enrich_epistemic_with_trust(format_epistemic_api_payload(m), m)
    gate = (m.get("bench_quality") or {}).get("save_gate") or m.get("save_gate") or {}
    suite = gate.get("domain_smoke_suite") or []
    if not suite and gate.get("tasks"):
        # Flatten stored save_gate (no full suite)
        min_score = gate.get("min_with_score")
        suite = [
            {
                "task_id": tid,
                "with_score": min_score if i == 0 else None,
                "passed": bool(gate.get("smoke_pass")) if i == 0 else None,
            }
            for i, tid in enumerate(gate.get("tasks") or [])
        ]

    smoke_rows: list[dict[str, Any]] = []
    for row in suite:
        smoke_rows.append(
            {
                "task_id": row.get("task_id"),
                "with_score": row.get("with_score"),
                "without_score": row.get("without_score"),
                "passed": row.get("passed"),
                "delta": row.get("delta"),
            }
        )

    trust = compute_trust_tier(
        epistemic=ep,
        gate_meta=gate if gate else None,
        draft=bool(m.get("draft")),
    )

    return {
        "skill": skill_name,
        "trust_tier": ep.get("trust_tier") or trust["trust_tier"],
        "gates": ep.get("gates") or trust["gates"],
        "claims": {
            "verified": ep.get("verified", 0),
            "pending": ep.get("pending", 0),
            "errors": ep.get("errors", 0),
            "total": ep.get("total_claims", 0),
        },
        "outcome": {
            "smoke_pass": (ep.get("gates") or trust["gates"]).get("outcome", {}).get("smoke_pass"),
            "min_with_score": (ep.get("gates") or trust["gates"]).get("outcome", {}).get("min_with_score"),
            "tasks": smoke_rows,
            "note": "Local domain smoke / Quick8 proxy - not official SkillsBench pass rate.",
        },
        "reasons": ep.get("trust_reasons") or trust.get("reasons") or [],
    }
