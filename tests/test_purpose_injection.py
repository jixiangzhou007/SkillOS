"""Phase 2 — PURPOSE + playbook unified ingest context."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


PURPOSE_MARKER = "PHASE2_TEST_PURPOSE_SOUL"
PLAYBOOK_MARKER = "PHASE2_TEST_PLAYBOOK_STYLE"


@pytest.fixture
def purpose_and_playbook(tmp_path, monkeypatch):
    claude_dir = tmp_path / "skills" / ".claude"
    claude_dir.mkdir(parents=True)
    purpose_path = claude_dir / "PURPOSE.md"
    playbook_path = claude_dir / "PLAYBOOK.md"
    purpose_path.write_text(
        f"# Purpose\n\n{PURPOSE_MARKER}: serve the QA team.\n" + "x" * 80,
        encoding="utf-8",
    )
    playbook_path.write_text(
        f"# Playbook\n\n{PLAYBOOK_MARKER}: use concise Chinese.\n" + "y" * 120,
        encoding="utf-8",
    )
    monkeypatch.setattr("skillos.knowledge.playbook.PURPOSE_PATH", purpose_path)
    monkeypatch.setattr("skillos.knowledge.playbook.PLAYBOOK_PATH", playbook_path)
    return purpose_path, playbook_path


class TestKnowledgeContext:
    def test_get_ingest_context_includes_purpose_and_playbook(self, purpose_and_playbook):
        from skillos.knowledge.knowledge_context import get_ingest_context

        ctx = get_ingest_context()
        assert PURPOSE_MARKER in ctx
        assert PLAYBOOK_MARKER in ctx
        assert "PURPOSE.md" in ctx

    def test_get_ingest_context_empty_when_missing(self, monkeypatch, tmp_path):
        missing = tmp_path / "missing" / "PURPOSE.md"
        monkeypatch.setattr("skillos.knowledge.playbook.PURPOSE_PATH", missing)
        monkeypatch.setattr("skillos.knowledge.playbook.PLAYBOOK_PATH", missing)

        from skillos.knowledge.knowledge_context import get_ingest_context

        assert get_ingest_context() == ""


class TestDeepDigestPurposeInjection:
    def test_stage_scan_prompt_includes_purpose(self, purpose_and_playbook):
        captured: list[str] = []

        def fake_call(prompt, **kwargs):
            captured.append(prompt)
            return "类型: article\n标题: Phase2\n判定: 不值得"

        from skillos.knowledge.knowledge_context import get_ingest_context
        from skillos.knowledge.deep_digest import _stage_scan

        ingest_ctx = get_ingest_context()
        with patch("skillos.llm_client.call", side_effect=fake_call):
            _stage_scan("x" * 500, "https://example.com/doc", ("k", "u", "m", {}), ingest_ctx)

        assert captured
        assert PURPOSE_MARKER in captured[0]

    def test_deep_digest_loads_ingest_context_for_stages(self, purpose_and_playbook):
        prompts: list[str] = []

        def fake_call(prompt, **kwargs):
            prompts.append(prompt)
            if "快速浏览以下文档内容" in prompt:
                return "类型: article\n标题: Phase2\n判定: 不值得"
            return ""

        with patch("skillos.llm_client.call", side_effect=fake_call):
            from skillos.knowledge.deep_digest import deep_digest

            deep_digest("z" * 600, "https://example.com/phase2", llm_args=("k", "u", "m", {}))

        assert prompts
        assert any(PURPOSE_MARKER in p for p in prompts)


class TestAgentPurposeInjection:
    def test_ingest_ctx_on_agent(self, purpose_and_playbook):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        ctx = agent._ingest_ctx()
        assert PURPOSE_MARKER in ctx
        assert PLAYBOOK_MARKER in ctx

    def test_generate_appends_ingest_context(self, purpose_and_playbook):
        from skillos.skills.agent import SkillExtractionAgent, Phase

        agent = SkillExtractionAgent()
        agent._phase = Phase.GENERATING
        agent._goal = "合同审核流程"
        agent._context = ["用户说：需要审核采购合同"]
        agent._locked_name = "合同审核"
        agent._probes_completed = {"trigger", "input", "steps", "output", "exceptions", "tools"}

        captured: list[str] = []

        def fake_call(prompt, **kwargs):
            captured.append(prompt)
            return (
                "```skill_doc\n"
                "tool_name: contract-review\n"
                "tool_description: Reviews procurement contracts when user asks.\n\n"
                "# 技能名称：合同审核\n\n"
                "## 核心问题\n审核合同\n\n"
                "## S_body\n1. 读合同\n\n"
                "## S_route\n| 意图 | 动作 | 备注 |\n| a | b | c |\n| d | e | f |\n"
                "## S_trigger\n- keywords: 合同\n"
                "## S_params\n- file: string\n"
                "```"
            )

        with patch("skillos.llm_client.call", side_effect=fake_call), \
             patch.object(agent, "_diffuse_knowledge", return_value=[]):
            agent._generate([], ("k", "u", "m", {}))

        assert captured
        assert PURPOSE_MARKER in captured[0]
