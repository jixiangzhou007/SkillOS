"""Tests for evolution engine modules."""

import pytest


class TestEvolutionEngine:
    def test_l3_evaluate(self):
        from skillos.evolution.engine import l3_evaluate, L3EvalResult
        old = "# Test\n## S_trigger\nkeywords: test\n## S_body\n1. Step\n## S_params\nmodel: gpt"
        new = "# Test\n## S_trigger\nkeywords: test, verify, check\n## S_body\n1. Step one\n2. Step two\n## S_params\nmodel: gpt\noutput: markdown"
        result = l3_evaluate(old, new, "test-skill", ("key", "url", "model", {}))
        assert isinstance(result, L3EvalResult)

    def test_evolution_trigger(self):
        from skillos.evolution.engine import EvolutionTrigger
        t = EvolutionTrigger(
            skill_name="test", trigger_type="score_decay",
            severity=0.7, detail="Score dropped", suggested_action="Optimize"
        )
        assert t.trigger_type == "score_decay"


class TestEvolver:
    def test_should_not_evolve_empty(self):
        from skillos.evolution.evolver import should_evolve
        ready, reason = should_evolve("nonexistent-skill-xyz")
        assert not ready
        assert "no traces" in reason.lower()


class TestSkillOpt:
    def test_opt_config(self):
        from skillos.evolution.skillopt import OptConfig
        config = OptConfig()
        assert config.initial_edit_budget == 4
        assert config.min_edit_budget == 1

    def test_edit_proposal(self):
        from skillos.evolution.skillopt import EditProposal
        ep = EditProposal(edit_type="replace", target="S_trigger",
                         old_text="old", new_text="new", reason="test")
        md = ep.to_markdown()
        assert "old" in md

    def test_elite_pool_tournament(self):
        from skillos.evolution.skillopt import ElitePool
        pool = ElitePool(skill_name="test", max_size=3)
        accepted, _ = pool.nominate("v1", 3.5, 1)
        assert accepted
        accepted2, _ = pool.nominate("v2", 4.2, 2)
        assert accepted2
        accepted3, _ = pool.nominate("v3", 3.8, 3)
        assert accepted3  # Pool fills to 3
        accepted4, _ = pool.nominate("v4", 4.5, 4)
        assert accepted4  # Beats weakest
        assert pool.champion["score"] == 4.5

    def test_compute_skill_state(self):
        from skillos.evolution.skillopt import compute_skill_state
        state = compute_skill_state("no-skill-xyz")
        assert state.trace_count == 0

    def test_route_moe(self):
        from skillos.evolution.skillopt import route, SkillState
        state = SkillState(skill_name="new", trace_count=3, score_variance=0.5, failure_diversity=1)
        decision = route(state)
        assert decision.primary.name in ("TRACE2SKILL", "SKILLOPT", "EVOSKILL")


class TestSkillHone:
    def test_record_decision(self):
        from skillos.evolution.skillhone import DecisionRecord, record_decision
        r = DecisionRecord(skill_name="test", diagnosis="Trigger too narrow")
        rid = record_decision(r)
        assert rid

    def test_build_decision_context(self):
        from skillos.evolution.skillhone import build_decision_context
        ctx = build_decision_context("nonexistent-skill-xyz")
        assert isinstance(ctx, str)

    def test_parse_sections(self):
        from skillos.evolution.skillhone import _parse_sections
        sections = _parse_sections("## S_trigger\nkeywords: test\n## S_body\n1. Step")
        assert "S_trigger" in sections
        assert "S_body" in sections

    def test_section_dimensions(self):
        from skillos.evolution.skillhone import _section_dimensions
        dims = _section_dimensions("S_trigger")
        assert "trigger_coverage" in dims
        dims2 = _section_dimensions("S_params")
        assert "param_abstraction" in dims2


class TestLearningTheory:
    def test_step_confidence(self):
        from skillos.evolution.learning_theory import StepConfidence
        sc = StepConfidence(step_name="S_body.步骤1", confidence=0.3)
        assert sc.needs_review
        assert not sc.is_certain


class TestLearningRecords:
    def test_step_record(self):
        from skillos.evolution.learning_records import StepRecord, LearningRecord
        sr = StepRecord(step="S_body.步骤1", status="learning", confidence=0.5)
        assert sr.status == "learning"
        lr = LearningRecord(skill_name="test")
        assert lr.skill_name == "test"
