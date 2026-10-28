"""Trust Tier Dual Gate contract tests."""

from skillos.evaluation.trust_tier import (
    TIER_DRAFT,
    TIER_PROVISIONAL,
    TIER_VERIFIED,
    compute_trust_tier,
    normalize_outcome_from_gate,
)


def test_draft_tier():
    r = compute_trust_tier(draft=True)
    assert r["trust_tier"] == TIER_DRAFT


def test_verified_requires_both_gates():
    r = compute_trust_tier(
        epistemic={"verified": 3, "pending": 1, "errors": 0, "total_claims": 4},
        gate_meta={
            "gate_enabled": True,
            "domain_smoke_suite": [
                {"task_id": "workflow-064", "with_score": 100},
            ],
        },
    )
    assert r["trust_tier"] == TIER_VERIFIED
    assert r["gates"]["epistemic"]["passed"] is True
    assert r["gates"]["outcome"]["passed"] is True


def test_provisional_when_smoke_fails():
    r = compute_trust_tier(
        epistemic={"verified": 5, "pending": 0, "errors": 0, "total_claims": 5},
        gate_meta={
            "gate_enabled": True,
            "domain_smoke_suite": [
                {"task_id": "software-dependency-audit", "with_score": 50},
            ],
            "warning": "域内烟测未达 80 分",
        },
    )
    assert r["trust_tier"] == TIER_PROVISIONAL
    assert r["gates"]["epistemic"]["passed"] is True
    assert r["gates"]["outcome"]["passed"] is False


def test_provisional_when_no_verified_claims():
    r = compute_trust_tier(
        epistemic={"verified": 0, "pending": 4, "errors": 0, "total_claims": 4},
        gate_meta={
            "gate_enabled": True,
            "domain_smoke_suite": [{"task_id": "t1", "with_score": 100}],
        },
    )
    assert r["trust_tier"] == TIER_PROVISIONAL
    assert r["gates"]["epistemic"]["passed"] is False


def test_normalize_outcome_from_apply_save_gate():
    norm = normalize_outcome_from_gate(
        {
            "gate_enabled": True,
            "domain_smoke_suite": [
                {"task_id": "a", "with_score": 90},
                {"task_id": "b", "with_score": 70},
            ],
            "warning": "域内烟测未达 80 分",
        }
    )
    assert norm["smoke_pass"] is False
    assert norm["min_with_score"] == 70


def test_enrich_from_stored_meta():
    from skillos.evaluation.trust_tier import enrich_epistemic_with_trust

    ep = enrich_epistemic_with_trust(
        {"verified": 2, "pending": 0, "errors": 0},
        {"trust_tier": "verified", "gates": {"epistemic": {"passed": True}, "outcome": {"passed": True}}},
    )
    assert ep["trust_tier"] == "verified"


def test_skill_response_includes_trust_tier():
    from skillos.api.skills import SkillResponse

    s = SkillResponse(name="x", trust_tier="verified")
    assert s.model_dump()["trust_tier"] == "verified"
    assert SkillResponse(name="y").trust_tier == "draft"
