"""Tests for MoE boost loop (P2)."""


from unittest.mock import patch

from skillos.evaluation.moe import ExpertResult, MoEReport
from skillos.evaluation.moe_boost import (
    _merge_section,
    boost_weakest_dimension,
    evaluate_and_boost,
)


def _report(score: int, expert_scores: dict[str, int]) -> MoEReport:
    experts = [
        ExpertResult(
            expert_key=k, expert_name=k, score=s, passed=s >= 70, summary=f"weak {k}",
        )
        for k, s in expert_scores.items()
    ]
    return MoEReport(
        skill_name="test",
        overall_score=score,
        confidence=0.7,
        passed=score >= 70,
        dimensions=expert_scores,
        experts=experts,
    )


class TestMergeSection:
    def test_replaces_existing_section(self):
        body = "## S_params\n- old\n\n## Instructions\nstep"
        out = _merge_section(body, "S_params", "## S_params\n- order_id: string\n")
        assert "order_id" in out
        assert "old" not in out


class TestBoostWeakest:
    def test_skips_when_all_pass(self):
        body = "## Instructions\nok"
        report = _report(80, {"params": 75, "routing": 72})
        out, meta = boost_weakest_dimension(body, "t", (), report)
        assert out == body
        assert meta["boosted"] is False


class TestEvaluateAndBoost:
    def test_stops_when_threshold_met(self):
        good = _report(75, {"params": 72})
        with patch("skillos.evaluation.moe_boost.evaluate_skill", return_value=good):
            body, report, boosts = evaluate_and_boost("## x", "t", ())
        assert report.overall_score == 75
        assert boosts == []

    def test_boosts_when_below_threshold(self):
        weak = _report(60, {"params": 50, "routing": 65})
        improved = _report(72, {"params": 70, "routing": 68})
        patch_text = "## S_params\n- order_id: string\n"
        with patch("skillos.evaluation.moe_boost.evaluate_skill", side_effect=[weak, improved]):
            with patch("skillos.llm_client.call", return_value=patch_text):
                body, report, boosts = evaluate_and_boost(
                    "## Instructions\nstep\n", "t", ("k", "u", "m"),
                    max_rounds=1,
                )
        assert len(boosts) == 1
        assert "order_id" in body
        assert report.overall_score == 72
