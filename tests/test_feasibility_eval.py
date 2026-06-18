"""Unit tests for feasibility evaluation (no LLM)."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "feasibility_dialogue_test",
    ROOT / "scripts" / "archive" / "feasibility_dialogue_test.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
evaluate = _mod.evaluate


SAMPLE_BODY = """# 技能名称：测试
## 核心问题
测试流程

## S_body
1. 第一步
2. 第二步
3. 第三步
4. 第四步

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 条件A | 动作A | |
| 条件B | 动作B | |

## S_trigger
- keywords: a, b
- context: 触发

## S_params
- x: string
"""


class TestFeasibilityEvaluate:
    def test_full_structure_with_s_route(self):
        ev = evaluate(SAMPLE_BODY, {"total_claims": 5, "verified": 3, "pending": 2}, [], ["第一步"])
        assert ev["structure_detail"]["S_route"] is True
        assert ev["structure_complete"] is True
        assert ev["has_route_table"] is True

    def test_missing_s_route_fails_structure_complete(self):
        body = SAMPLE_BODY.replace("## S_route\n| 用户意图/条件 | 执行动作 | 备注 |\n|------------|---------|------|\n| 条件A | 动作A | |\n| 条件B | 动作B | |\n\n", "")
        ev = evaluate(body, {"total_claims": 1}, [], [])
        assert ev["structure_detail"]["S_route"] is False
        assert ev["structure_complete"] is False

    def test_hallucination_probe_excludes_user_mentioned_terms(self):
        body = "# PR\nGitHub Pull Request review"
        log = [{"role": "user", "content": "GitHub Pull Request 流程"}]
        ev = evaluate(body, {}, log, ["GitHub"])
        assert "GitHub" not in ev["hallucination_flags"]


class TestEnsureSRoute:
    def test_ensure_s_route_noop_when_present(self):
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        content = SAMPLE_BODY
        assert agent._ensure_s_route(content, ("", "", "")) == content
