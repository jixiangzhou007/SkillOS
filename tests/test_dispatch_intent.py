"""Phase 3 — unified dispatch intent routing tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestIntentRouter:
    def test_classify_extract(self):
        from skillos.skills.intent_router import DispatchIntent, classify_message_intent

        assert classify_message_intent("帮我沉淀退款流程") == DispatchIntent.EXTRACT
        assert classify_message_intent("整理成标准技能") == DispatchIntent.EXTRACT

    def test_meta_extraction_question(self):
        from skillos.skills.intent_router import is_meta_extraction_question

        assert is_meta_extraction_question("你不是沉淀技能吗")
        assert is_meta_extraction_question("怎么还不生成技能？")
        assert not is_meta_extraction_question("帮我沉淀合同审核流程")

    def test_extract_topic_ignores_meta(self):
        from skillos.skills.agent import SkillExtractionAgent

        assert SkillExtractionAgent._extract_topic("你不是沉淀技能吗") == ""

    def test_restore_and_meta_reply(self):
        from skillos.skills.agent import SkillExtractionAgent, Phase

        agent = SkillExtractionAgent()
        history = [
            {"role": "user", "content": "我想创建一个合同审核的技能"},
            {"role": "assistant", "content": "好的，我们来沉淀「合同审核」的技能。"},
            {"role": "user", "content": "销售合同，文件名带 contract 触发"},
            {"role": "assistant", "content": "收到，付款条款和验收标准需要重点看吗？"},
        ]
        assert agent.restore_from_history(history) is True
        assert agent.is_active
        assert "合同" in agent._goal
        reply = agent.reply_to_meta_question()
        assert "合同" in reply
        assert "你不是" not in reply

    def test_classify_confirm(self):
        from skillos.skills.intent_router import DispatchIntent, classify_message_intent

        assert classify_message_intent("确认待审") == DispatchIntent.CONFIRM_CLAIMS
        assert classify_message_intent("确认 1,2") == DispatchIntent.CONFIRM_CLAIMS
        assert classify_message_intent("confirm pending") == DispatchIntent.CONFIRM_CLAIMS

    def test_confirm_before_extract(self):
        """Bare 确认 in extraction should not steal extract — needs 待审 or indices."""
        from skillos.skills.intent_router import DispatchIntent, classify_message_intent

        assert classify_message_intent("确认，生成最终文档") == DispatchIntent.CHAT

    def test_parse_indices(self):
        from skillos.skills.intent_router import parse_confirm_claim_selection

        pending = ["c-a", "c-b", "c-c"]
        assert parse_confirm_claim_selection("确认 1,3", pending) == ["c-a", "c-c"]
        assert parse_confirm_claim_selection("确认待审", pending) == pending

    def test_parse_claim_ids(self):
        from skillos.skills.intent_router import parse_confirm_claim_selection

        assert parse_confirm_claim_selection("确认 claim_abc123", []) == ["claim_abc123"]


class TestDispatchFeishuSession:
    def test_feishu_channel_builds_session(self):
        from skillos.api.server import app
        from skillos.skills.session_manager import get_session_manager

        get_session_manager().delete("feishu:oc_test:ou_test")

        with patch("skillos.llm_client.call", return_value="合同审核通常包含条款比对和风险识别，你觉得呢？"):
            client = TestClient(app)
            resp = client.post(
                "/api/skills/dispatch",
                json={
                    "message": "帮我沉淀退款流程",
                    "channel": "feishu",
                    "chat_id": "oc_test",
                    "user_id": "ou_test",
                    "mode": "create",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["session_id"] == "feishu:oc_test:ou_test"


class TestDispatchConfirmClaims:
    def test_dispatch_confirm_promotes(self, tmp_path):
        from skillos.knowledge.epistemology import isolated_epistemic_store
        from skillos.knowledge.epistemic_bridge import apply_epistemics_to_skill
        from skillos.api.server import app

        sample_body = """## S_body
1. 在处理退款前必须核对订单号与支付渠道是否一致
2. 超过七天的退款需要主管审批并留下书面记录
"""
        with isolated_epistemic_store(tmp_path / "epistemic.json"):
            body, summary = apply_epistemics_to_skill(
                sample_body,
                skill_name="dispatch-confirm-test",
                source="test://dispatch",
                source_type="test_result",
                llm_args=None,
                run_falsify=False,
            )
            assert summary.pending >= 1
            pending_id = summary.pending_ids[0]

            from skillos.skills import skill_store

            skill_store.save_skill(
                "dispatch-confirm-test",
                body,
                meta=summary.to_meta(),
                epistemic=False,
            )

            client = TestClient(app)
            resp = client.post(
                "/api/skills/dispatch",
                json={"message": "确认待审", "history": [], "mode": "chat"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("intent") == "confirm_claims"
            assert data.get("promoted", 0) >= 1
            assert pending_id in data.get("claim_ids", [])


class TestShouldStart:
    def test_finalize_phrase_does_not_restart(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        assert agent.should_start("可以了，生成技能文档吧") is False
        assert agent.should_start("帮我沉淀退款流程") is True


class TestDispatchExtract:
    def test_dispatch_extract_starts_session(self):
        from skillos.api.server import app
        from skillos.skills.session_manager import get_session_manager

        get_session_manager().delete("")

        mock_agent = MagicMock()
        mock_agent.is_active = True
        mock_agent.draft_name = ""
        mock_agent.should_start.return_value = True
        mock_agent.handle.return_value = ("好的，我们从退款流程的目标开始。", None)

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent):
            client = TestClient(app)
            resp = client.post(
                "/api/skills/dispatch",
                json={"message": "帮我沉淀退款流程", "history": [], "mode": "create"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("skill_active") is True
            mock_agent.handle.assert_called_once()

    def test_dispatch_attaches_option_buttons(self):
        from skillos.api.server import app

        mock_agent = MagicMock()
        mock_agent.is_active = False
        mock_agent.handle.return_value = (
            "选一个风险等级：\n[选项] 高风险 | risk_high\n[选项] 低风险 | risk_low",
            None,
        )

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent):
            client = TestClient(app)
            resp = client.post(
                "/api/skills/dispatch",
                json={"message": "合同审核", "mode": "create"},
            )
            data = resp.json()
            assert len(data.get("actions", [])) == 2
            assert data["actions"][0]["action"] == "risk_high"

    def test_meta_question_does_not_restart_extraction(self):
        from skillos.api.server import app
        from skillos.skills.session_manager import get_session_manager

        sid = "test-meta-no-restart"
        get_session_manager().delete(sid)

        client = TestClient(app)
        r1 = client.post(
            "/api/skills/dispatch",
            json={"message": "我想创建一个合同审核的技能", "session_id": sid, "mode": "create"},
        )
        assert r1.status_code == 200
        assert "合同" in r1.json()["reply"]

        client.post(
            "/api/skills/dispatch",
            json={"message": "销售合同，文件名带 contract 触发", "session_id": sid, "mode": "create"},
        )
        client.post(
            "/api/skills/dispatch",
            json={"message": "是的", "session_id": sid, "mode": "create"},
        )

        with patch("skillos.llm_client.call", return_value="继续补充验收条款即可。"):
            r4 = client.post(
                "/api/skills/dispatch",
                json={"message": "你不是沉淀技能吗", "session_id": sid, "mode": "create"},
            )
        assert r4.status_code == 200
        reply = r4.json()["reply"]
        assert "合同" in reply
        assert "你不是沉淀技能吗" not in reply
        assert r4.json().get("skill_active") is True


class TestMcpConfirmPendingClaims:
    def test_mcp_confirm_all(self, tmp_path):
        from skillos.knowledge.epistemology import isolated_epistemic_store
        from skillos.knowledge.epistemic_bridge import apply_epistemics_to_skill
        from skillos.mcp_server import confirm_pending_claims

        body = "## S_body\n1. 发布前必须运行完整测试套件并检查覆盖率报告"
        with isolated_epistemic_store(tmp_path / "ep_mcp.json"):
            _, summary = apply_epistemics_to_skill(
                body,
                skill_name="mcp-confirm-test",
                source="test://mcp",
                source_type="test_result",
                llm_args=None,
                run_falsify=False,
            )
            assert summary.pending >= 1

            out = confirm_pending_claims(confirm_all=True, skill_name="mcp-confirm-test")
            assert "Promoted:" in out
