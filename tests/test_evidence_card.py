"""Evidence card + trust enrich tests."""

from skillos.evaluation.evidence import build_evidence_card


def test_build_evidence_card_minimal():
    card = build_evidence_card(
        "demo-skill",
        meta={
            "epistemic": {"verified": 2, "pending": 1, "errors": 0, "total_claims": 3},
            "bench_quality": {
                "save_gate": {
                    "smoke_pass": True,
                    "min_with_score": 100,
                    "tasks": ["workflow-064"],
                }
            },
            "trust_tier": "verified",
            "gates": {
                "epistemic": {"passed": True},
                "outcome": {"passed": True, "min_with_score": 100, "tasks": ["workflow-064"]},
            },
        },
    )
    assert card["skill"] == "demo-skill"
    assert card["claims"]["verified"] == 2
    assert card["trust_tier"] in ("verified", "provisional")
    assert "outcome" in card
