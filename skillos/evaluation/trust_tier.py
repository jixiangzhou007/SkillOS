"""Trust Tier — Dual Gate product contract (Draft / Provisional / Verified)."""

from __future__ import annotations

from typing import Any

TIER_DRAFT = "draft"
TIER_PROVISIONAL = "provisional"
TIER_VERIFIED = "verified"

DOMAIN_SMOKE_MIN = 80


def _int(d: dict[str, Any] | None, key: str, default: int = 0) -> int:
    if not d:
        return default
    try:
        return int(d.get(key) if d.get(key) is not None else default)
    except (TypeError, ValueError):
        return default


def evaluate_epistemic_gate(epistemic: dict[str, Any] | None) -> tuple[bool, str]:
    """Gate A: at least one verified claim and no recorded errors."""
    ep = epistemic or {}
    errors = _int(ep, "errors", 0)
    if errors > 0:
        return False, f"errors={errors}"
    verified = _int(ep, "verified", 0)
    if verified >= 1:
        return True, f"verified={verified}"
    total = _int(ep, "total_claims", 0)
    if total == 0:
        return False, "no_claims"
    return False, f"verified=0 pending={_int(ep, 'pending', 0)}"


def normalize_outcome_from_gate(gate_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten apply_save_gate / bench_quality save_gate into smoke_pass + min score."""
    gate = dict(gate_meta or {})
    if gate.get("skipped") == "no_domain_task":
        return {
            "smoke_pass": False,
            "min_with_score": 0,
            "tasks": [],
            "skipped": "no_domain_task",
            "gate_enabled": gate.get("gate_enabled", True),
        }

    suite = gate.get("domain_smoke_suite") or []
    tasks = list(gate.get("tasks") or [])
    min_score = gate.get("min_with_score")
    if suite:
        min_score = min(int(r.get("with_score") or 0) for r in suite)
        if not tasks:
            tasks = [r.get("task_id") for r in suite if r.get("task_id")]
    if min_score is None:
        smoke = gate.get("domain_smoke") or {}
        min_score = int(smoke.get("with_score") or 0) if smoke else 0

    min_score = int(min_score or 0)
    if "smoke_pass" in gate and gate["smoke_pass"] is not None and not suite:
        smoke_pass = bool(gate["smoke_pass"])
    else:
        smoke_pass = min_score >= DOMAIN_SMOKE_MIN and not gate.get("warning")

    # Explicit warning from apply_save_gate always fails outcome
    if gate.get("warning"):
        smoke_pass = False

    return {
        "smoke_pass": smoke_pass,
        "min_with_score": min_score,
        "tasks": tasks,
        "gate_enabled": gate.get("gate_enabled", True),
        "warning": gate.get("warning"),
        "skipped": gate.get("skipped"),
    }


def evaluate_outcome_gate(gate_meta: dict[str, Any] | None) -> tuple[bool, str]:
    """Gate B: domain smoke suite min score ≥ 80."""
    if not gate_meta:
        return False, "outcome_not_run"
    if gate_meta.get("gate_enabled") is False:
        return False, "gate_disabled"
    norm = normalize_outcome_from_gate(gate_meta)
    if norm.get("skipped") == "no_domain_task":
        return False, "no_domain_task"
    if norm["smoke_pass"]:
        return True, f"min_score={norm['min_with_score']}"
    return False, f"min_score={norm['min_with_score']}<{DOMAIN_SMOKE_MIN}"


def compute_trust_tier(
    *,
    epistemic: dict[str, Any] | None = None,
    gate_meta: dict[str, Any] | None = None,
    draft: bool = False,
) -> dict[str, Any]:
    """Compute trust_tier and dual-gate snapshot for API / frontmatter."""
    if draft:
        return {
            "trust_tier": TIER_DRAFT,
            "gates": {
                "epistemic": {"passed": False, "detail": "draft"},
                "outcome": {"passed": False, "detail": "draft"},
            },
            "reasons": ["draft"],
        }

    ep_ok, ep_detail = evaluate_epistemic_gate(epistemic)
    out_ok, out_detail = evaluate_outcome_gate(gate_meta)
    outcome_norm = normalize_outcome_from_gate(gate_meta)

    if ep_ok and out_ok:
        tier = TIER_VERIFIED
    else:
        tier = TIER_PROVISIONAL

    reasons: list[str] = []
    if not ep_ok:
        reasons.append(f"epistemic:{ep_detail}")
    if not out_ok:
        reasons.append(f"outcome:{out_detail}")

    return {
        "trust_tier": tier,
        "gates": {
            "epistemic": {"passed": ep_ok, "detail": ep_detail},
            "outcome": {
                "passed": out_ok,
                "detail": out_detail,
                "smoke_pass": outcome_norm.get("smoke_pass"),
                "min_with_score": outcome_norm.get("min_with_score"),
                "tasks": outcome_norm.get("tasks") or [],
            },
        },
        "reasons": reasons,
    }


def enrich_epistemic_with_trust(ep: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach trust_tier/gates to an epistemic API payload from skill meta."""
    out = dict(ep or {})
    m = meta or {}
    if m.get("trust_tier"):
        out["trust_tier"] = m["trust_tier"]
    if m.get("gates"):
        out["gates"] = m["gates"]
    if out.get("trust_tier") and out.get("gates"):
        return out
    bq = m.get("bench_quality") or {}
    gate = bq.get("save_gate") or m.get("save_gate")
    snap = compute_trust_tier(epistemic=out, gate_meta=gate, draft=bool(m.get("draft")))
    out["trust_tier"] = snap["trust_tier"]
    out["gates"] = snap["gates"]
    out["trust_reasons"] = snap.get("reasons") or []
    return out
