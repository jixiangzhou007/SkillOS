"""Tests for MCP extract pipeline and channel session IDs."""

from unittest.mock import MagicMock, patch


SAMPLE_PROCEDURE = """
## 退款处理流程
1. 收到退款请求后必须先核对订单号与支付渠道是否一致
2. 超过七天的退款需要主管审批并留下书面记录
3. 退款完成后更新 CRM 状态并发送确认邮件给客户
"""


class TestChannelSessionIds:
    def test_feishu_session_id(self):
        from skillos.channels.session_ids import feishu_session_id, parse_channel_session

        sid = feishu_session_id("oc_abc", "ou_xyz")
        assert sid == "feishu:oc_abc:ou_xyz"
        parsed = parse_channel_session(sid)
        assert parsed == {"channel": "feishu", "chat_id": "oc_abc", "user_id": "ou_xyz"}

    def test_resolve_session_id(self):
        from skillos.channels.session_ids import resolve_session_id

        assert resolve_session_id("custom-id") == "custom-id"
        assert resolve_session_id(
            channel="feishu", chat_id="oc_1", user_id="ou_2"
        ) == "feishu:oc_1:ou_2"


class TestMcpExtract:
    def test_empty_content_fails(self):
        from skillos.mcp_extract import run_mcp_extract

        r = run_mcp_extract("")
        assert r.ok is False
        assert "empty" in r.error.lower()

    def test_skill_pipeline_success(self, tmp_path, monkeypatch):
        from skillos.mcp_extract import run_mcp_extract

        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "skills"))
        monkeypatch.setenv("SKILLOS_WORKSPACE_SKILLS", str(tmp_path / "workspace-skills"))

        sample_doc = {
            "name": "phase4-refund",
            "content": "# Skill Name: phase4-refund\n## S_body\n1. 核对订单号与支付渠道",
            "pipeline_log": ["初识: ok", "理解: ok", "沉淀: ok"],
        }
        mock_agent = MagicMock()
        mock_agent.learn_from_url.return_value = ("✅ 学习完成", sample_doc)

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent), \
             patch("skillos.knowledge.epistemic_bridge.apply_epistemics_to_skill") as mock_apply, \
             patch("skillos.mcp_extract._classify_mode", return_value="skill"):
            from skillos.knowledge.epistemic_bridge import EpistemicSummary

            summary = EpistemicSummary(skill_name="phase4-refund", total=2, pending=2)
            mock_apply.return_value = (sample_doc["content"], summary)

            result = run_mcp_extract(SAMPLE_PROCEDURE, mode="skill")

        assert result.ok is True
        assert result.name == "phase4-refund"
        assert len(result.pipeline_log) == 3
        assert result.skill_path
        assert result.workspace_path

    def test_format_includes_pipeline_and_epistemic(self):
        from skillos.mcp_extract import ExtractResult

        r = ExtractResult(
            ok=True,
            name="demo",
            content="# Skill",
            summary="✅ done",
            pipeline_log=["step1: ok"],
            epistemic_summary={"verified": 1, "pending": 2, "total_claims": 3},
            skill_path="/tmp/skills/demo/SKILL.md",
        )
        text = r.format_mcp_response()
        assert "Pipeline log" in text
        assert "认识论" in text
        assert "demo" in text


class TestExtractSkillTool:
    def test_mcp_tool_delegates(self):
        from skillos.mcp_server import extract_skill
        from skillos.mcp_extract import ExtractResult

        fake = ExtractResult(ok=False, error="unit test error", pipeline_log=["初识: skip"])
        with patch("skillos.mcp_extract.run_mcp_extract", return_value=fake):
            out = extract_skill("hello", mode="skill")
        assert "Extraction failed" in out
        assert "Pipeline log" in out
