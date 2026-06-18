"""Tests for MoE soft boost and save gate."""


from unittest.mock import MagicMock, patch

from skillos.evaluation.moe_boost import (
    MOE_PASS_THRESHOLD,
    MOE_SOFT_THRESHOLD,
    evaluate_and_boost,
)
from skillos.evaluation.moe import ExpertResult, MoEReport


def _report(score: int) -> MoEReport:
    return MoEReport(
        skill_name="t",
        overall_score=score,
        confidence=0.8,
        passed=score >= MOE_PASS_THRESHOLD,
        experts=[ExpertResult(
            expert_key="structure",
            expert_name="Structure",
            score=50,
            summary="weak",
            passed=False,
        )],
        dimensions={"structure": 50},
    )


class TestEvaluateAndBoostRounds:
    def test_no_boost_at_soft_threshold(self):
        with patch("skillos.evaluation.moe_boost.evaluate_skill", return_value=_report(82)):
            _, report, boosts = evaluate_and_boost("body", "t", ())
        assert report.overall_score == 82
        assert boosts == []

    def test_one_soft_round_between_pass_and_soft(self):
        calls = [_report(75), _report(82)]

        def fake_eval(*_a, **_k):
            return calls.pop(0) if calls else _report(82)

        with patch("skillos.evaluation.moe_boost.evaluate_skill", side_effect=fake_eval):
            with patch(
                "skillos.evaluation.moe_boost.boost_weakest_dimension",
                return_value=("patched", {"boosted": True, "expert_key": "structure"}),
            ):
                body, report, boosts = evaluate_and_boost("body", "t", ())
        assert report.overall_score == 82
        assert len(boosts) == 1
        assert boosts[0].get("soft_boost") is True

    def test_hard_rounds_below_pass(self):
        with patch("skillos.evaluation.moe_boost.evaluate_skill", return_value=_report(65)):
            with patch(
                "skillos.evaluation.moe_boost.boost_weakest_dimension",
                return_value=("body", {"boosted": False}),
            ):
                _, _, boosts = evaluate_and_boost("body", "t", (), max_rounds=2)
        assert len(boosts) == 1


class TestSaveGate:
    def test_smoke_passes_for_refund_skill(self):
        from pathlib import Path

        skill = "电商客服退款处理"
        md = Path(__file__).resolve().parent.parent / "skills" / skill / "SKILL.md"
        if not md.is_file():
            return
        from skillos.evaluation.save_gate import run_domain_smoke

        body = md.read_text(encoding="utf-8").split("---", 2)[-1]
        smoke = run_domain_smoke(skill, body, domain_template="workflow-refund")
        assert smoke is not None
        assert smoke["task_id"] == "workflow-064"
        assert smoke["with_score"] >= 80

    def test_smoke_suite_for_pr(self):
        from pathlib import Path

        skill = "GitHub Pull"
        md = Path(__file__).resolve().parent.parent / "skills" / skill / "SKILL.md"
        if not md.is_file():
            return
        from skillos.evaluation.save_gate import run_domain_smoke_suite

        body = md.read_text(encoding="utf-8").split("---", 2)[-1]
        suite = run_domain_smoke_suite(skill, body, domain_template="code-review-pr")
        assert len(suite) >= 1
        assert suite[0]["task_id"] == "software-dependency-audit"
