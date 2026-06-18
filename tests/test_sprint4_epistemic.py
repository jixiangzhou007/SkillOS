"""Sprint 4 — epistemic UI API, dedup, quick mode."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("SKILLOS_DATA_DIR", str(data))
    monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
    monkeypatch.setenv("SKILLOS_JWT_SECRET", "test-secret")
    import skillos.db as db_mod
    db_mod._local.conns = {}
    import skillos.marketplace.auth as auth_mod
    auth_mod._local.conn = None
    from skillos.api.server import app
    return TestClient(app)


class TestEpistemicAPI:
    def test_pending_and_confirm(self, tmp_path):
        from skillos.knowledge.epistemology import isolated_epistemic_store
        from skillos.knowledge.epistemic_bridge import apply_epistemics_to_skill

        body = """## S_body
1. 退款前必须核对订单号与支付渠道是否一致
2. 超过七天的退款需要主管审批
"""
        with isolated_epistemic_store(tmp_path / "ep.json"):
            enriched, summary = apply_epistemics_to_skill(
                body,
                skill_name="ep-ui-test",
                source="test",
                source_type="test_result",
                llm_args=None,
                run_falsify=False,
            )
            assert summary.pending >= 1
            pending_id = summary.pending_ids[0]

            from skillos.skills import skill_store
            skill_store.save_skill(
                "ep-ui-test", enriched, meta=summary.to_meta(), epistemic=False,
            )

            from skillos.api.server import app
            c = TestClient(app)
            r = c.get("/api/skills/ep-ui-test/epistemic/pending")
            assert r.status_code == 200
            data = r.json()
            assert data["epistemic_summary"]["pending"] >= 1
            assert any(p["claim_id"] == pending_id for p in data["pending_claims"])

            conf = c.post(
                "/api/skills/ep-ui-test/epistemic/confirm",
                json={"claim_ids": [pending_id]},
            )
            assert conf.status_code == 200
            assert conf.json()["promoted"] >= 1


class TestDedup:
    def test_find_similar_by_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store
        from skillos.skills.dedup import find_similar_skills

        t = TenantContext.personal("u1")
        body = "## S_body\n1. refund step"
        skill_store.save_skill("淘宝退款处理", body, epistemic=False, tenant=t)
        skill_store.save_skill("淘宝退款流程", body, epistemic=False, tenant=t)

        similar = find_similar_skills("淘宝退款处理", body, tenant=t)
        assert any(s["name"] == "淘宝退款流程" for s in similar)

        skill_store.delete_skill("淘宝退款处理", tenant=t)
        skill_store.delete_skill("淘宝退款流程", tenant=t)


class TestQuickMode:
    def test_agent_quick_start(self):
        from skillos.skills.agent import SkillExtractionAgent, Phase

        agent = SkillExtractionAgent()
        long_text = "退款流程：" + ("详细步骤描述。" * 80)
        reply = agent.start(long_text, quick_mode=True)
        assert agent._phase == Phase.REFINING
        assert "快速模式" in reply

    def test_dispatch_quick_mode_flag(self, client):
        from unittest.mock import MagicMock, patch

        mock_agent = MagicMock()
        mock_agent.is_active = False
        mock_agent.start.return_value = "快速模式已启动"
        shared_mgr = __import__("skillos.skills.session_manager", fromlist=["SessionManager"]).SessionManager()

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent), patch(
            "skillos.skills.session_manager.SessionManager", return_value=shared_mgr
        ):
            r = client.post(
                "/api/skills/dispatch",
                json={"message": "帮我沉淀退款流程" + ("详细描述。" * 100), "mode": "chat"},
            )
        assert r.status_code == 200
        assert r.json().get("quick_mode") is True
        mock_agent.start.assert_called_once()
        assert mock_agent.start.call_args[1].get("quick_mode") is True
