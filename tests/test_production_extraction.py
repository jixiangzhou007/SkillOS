"""Production-grade extraction flow tests (no live LLM)."""

from unittest.mock import patch

import pytest


class TestSessionDraftIsolation:
    def test_save_draft_does_not_write_skills_dir(self, tmp_path, monkeypatch):
        from skillos.skills.agent import SkillExtractionAgent, Phase

        monkeypatch.setattr(
            "skillos.skills.session_draft._DRAFT_ROOT",
            tmp_path / "session_drafts",
        )
        agent = SkillExtractionAgent()
        agent.set_team_context(session_id="sess-iso-1")
        agent._phase = Phase.REFINING

        with patch("skillos.skills.skill_store.save_skill") as save_skill:
            agent._save_draft("测试技能", "# 技能名称：测试\n## S_body\n1. step")

        save_skill.assert_not_called()
        draft_file = tmp_path / "session_drafts" / "sess-iso-1.json"
        assert draft_file.exists()
        assert agent.draft_name == "测试技能"

    def test_finalize_clears_session_draft(self, tmp_path, monkeypatch):
        from skillos.skills.session_draft import save_session_draft, load_session_draft
        from skillos.skills.agent import SkillExtractionAgent, Phase

        monkeypatch.setattr(
            "skillos.skills.session_draft._DRAFT_ROOT",
            tmp_path / "session_drafts",
        )
        save_session_draft("sess-clear", "工单", "body", goal="工单")
        agent = SkillExtractionAgent()
        agent.set_team_context(session_id="sess-clear")
        agent._phase = Phase.GENERATING
        agent._clear_session_draft()
        assert load_session_draft("sess-clear") is None


class TestSkillNameLocking:
    def test_lock_from_topic_on_start(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent.start("我想创建一个合同审核的技能")
        assert agent.locked_name == "合同审核"

    def test_resolve_keeps_locked_name(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent._lock_skill_name("技术支持工单处理")
        assert agent._resolve_skill_name("工单分流") == "技术支持工单处理"

    def test_parse_dual_response_uses_locked_name(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent._lock_skill_name("技术支持工单处理")
        raw = (
            "<QUESTION>继续</QUESTION>\n<SKILL_DRAFT>\n```skill_doc\n"
            "# 技能名称：别的名字\n## S_body\n1. x\n```\n</SKILL_DRAFT>"
        )
        _, draft = agent._parse_dual_response(raw)
        assert draft is not None
        assert draft[0] == "技术支持工单处理"


class TestDispatchDraftMetadata:
    def test_finalize_response_marks_in_session_draft(self):
        from skillos.api.skills import _finalize_extraction_response
        from skillos.skills.agent import SkillExtractionAgent, Phase
        from skillos.skills.session_manager import Session

        agent = SkillExtractionAgent()
        agent._phase = Phase.REFINING
        agent._lock_skill_name("合同审核")
        agent._draft_content = "# x"
        session = Session("test-draft-meta")

        out = _finalize_extraction_response(session, "继续补充", agent)
        assert out["draft_in_session"] is True
        assert out["draft_preview"] == "合同审核"
        assert out.get("skill_saved") is None


class TestP0FinalizeGate:
    def test_should_start_false_when_finalizing_with_skill_keyword(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        assert agent.should_start("够了，生成技能吧") is False

    def test_explicit_finalize_not_blocked_early(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent._turn = 1
        agent._context = ["用户说：退款流程"]
        assert agent._should_block_finalize("可以了，生成技能文档") is False

    def test_ambiguous_finalize_blocked_without_context(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent._turn = 1
        assert agent._should_block_finalize("好") is True

    def test_handle_explicit_finalize_generates_from_exploring(self):
        from skillos.skills.agent import Phase, SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent._phase = Phase.EXPLORING
        agent._goal = "退款处理"
        agent._context = ["用户说：查订单再退款"]
        agent._lock_skill_name("退款处理")

        with patch.object(agent, "_generate", return_value=("ok", {"name": "退款处理", "content": "body"})) as gen:
            reply, doc = agent.handle("够了，直接生成技能文档", [], ("k", "u", "m", {}))

        gen.assert_called_once()
        assert doc is not None


class TestEnsureSkillParams:
    def test_fills_missing_s_params_from_body_hints(self):
        from skillos.skills.portable_skill import ensure_skill_params, finalize_portable_skill

        body = (
            "# 技能名称：退款\n## S_body\n1. 查订单号\n2. 核实金额后退款\n"
            "## S_trigger\n- keywords: 退款, 退货\n"
        )
        out = ensure_skill_params(body)
        assert "## S_params" in out
        assert "order_id" in out
        assert "## S_outputs" in out

    def test_finalize_portable_includes_inputs(self):
        from skillos.skills.portable_skill import finalize_portable_skill

        body = (
            "# 技能名称：CSV清洗\n## S_body\n1. 读取 CSV 文件\n"
            "## S_trigger\n- keywords: csv, 清洗\n"
        )
        fin = finalize_portable_skill("CSV清洗", body)
        assert "## Inputs" in fin["body"]
        assert "file_path" in fin["body"] or "user_message" in fin["body"]
