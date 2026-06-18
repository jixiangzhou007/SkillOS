"""MoE evaluation — mock LLM, no live API key required."""

import json
from unittest.mock import patch

import pytest

SAMPLE_SKILL = """---
name: demo
description: Demo skill
---

# Demo

## When to use
- keywords: demo, test

## Instructions
1. Do step one
2. If error then retry

## Decision routes
| 条件 | 动作 | 备注 |
| a | b | c |

## Inputs
- x: string, 必填
"""


def _expert_json(score: int) -> str:
    return json.dumps({"overall": score, "summary": "ok", "passed": score >= 70})


class TestMoEEngine:
    def test_evaluate_skill_aggregates_six_experts(self):
        from skillos.evaluation.moe import evaluate_skill

        scores = [80, 75, 70, 85, 78, 72]
        calls = {"i": 0}

        def fake_call(prompt, **kwargs):
            i = calls["i"]
            calls["i"] += 1
            return _expert_json(scores[i % len(scores)])

        with patch("skillos.llm_client.call", side_effect=fake_call):
            report = evaluate_skill(SAMPLE_SKILL, "demo", ("key", "url", "model"))

        assert len(report.experts) == 6
        assert 60 <= report.overall_score <= 100
        assert report.confidence == 0.7
        assert "structure" in report.dimensions

    def test_cross_model_flags_disagreement(self):
        from skillos.evaluation.moe import evaluate_skill

        primary = [85] * 6
        cross = [50] * 6
        phase = {"n": 0}

        def fake_call(prompt, **kwargs):
            model = kwargs.get("model", "")
            idx = phase["n"] % 6
            phase["n"] += 1
            score = cross[idx] if model == "cheap" else primary[idx]
            return _expert_json(score)

        with patch("skillos.llm_client.call", side_effect=fake_call):
            report = evaluate_skill(
                SAMPLE_SKILL, "demo", ("k", "u", "primary"),
                cross_model="cheap",
            )

        assert report.cross_model_used is True
        assert len(report.warnings) >= 1


class TestMoEApiSmoke:
    def test_evaluate_endpoint_mock_llm(self, tmp_path, monkeypatch):
        from skillos.skills import skill_store
        from skillos.api.server import app
        from fastapi.testclient import TestClient

        monkeypatch.setattr(skill_store, "resolve_skills_root", lambda tenant=None: tmp_path)
        skill_store.save_skill("moe-api-test", SAMPLE_SKILL, meta={"draft": False}, epistemic=False)

        def fake_call(prompt, **kwargs):
            return _expert_json(82)

        with patch("skillos.llm_client.call", side_effect=fake_call):
            client = TestClient(app)
            resp = client.get("/api/skills/moe-api-test/evaluate")

        assert resp.status_code == 200
        data = resp.json()
        assert "error" not in data
        assert data["overall_score"] >= 70
        assert data["passed"] is True
        assert len(data["experts"]) == 6

    def test_evaluate_markdown_endpoint_mock_llm(self, tmp_path, monkeypatch):
        from skillos.skills import skill_store
        from skillos.api.server import app
        from fastapi.testclient import TestClient

        monkeypatch.setattr(skill_store, "resolve_skills_root", lambda tenant=None: tmp_path)
        skill_store.save_skill("moe-md-test", SAMPLE_SKILL, meta={"draft": False}, epistemic=False)

        with patch("skillos.llm_client.call", return_value=_expert_json(75)):
            client = TestClient(app)
            resp = client.get("/api/skills/moe-md-test/evaluate/markdown")

        assert resp.status_code == 200
        assert "MoE 技能评价报告" in resp.text


class TestUnifiedQuality:
    def test_heuristic_layer_not_official(self):
        from skillos.evaluation.quality import evaluate_heuristic, OFFICIAL_LAYER

        result = evaluate_heuristic(SAMPLE_SKILL, "demo")
        assert result["layer"] == "heuristic"
        assert result["official"] is False
        assert OFFICIAL_LAYER == "moe"

    def test_build_quality_payload_prefers_moe_as_official(self):
        from skillos.evaluation.quality import build_quality_payload

        payload = build_quality_payload(
            skill_name="demo",
            body=SAMPLE_SKILL,
            moe={"overall_score": 78, "passed": True, "confidence": 0.7, "dimensions": {}},
        )
        assert payload["official_layer"] == "moe"
        assert payload["official_score"] == 78
        assert payload["official_grade"] == "B"
        assert payload["heuristic"]["total"] > 0

    def test_draft_readiness_labels(self):
        from skillos.evaluation.quality import draft_readiness_label

        assert draft_readiness_label(1) == "空白/缺失"
        assert draft_readiness_label(5) == "就绪可生成"
