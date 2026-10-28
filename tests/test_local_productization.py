"""Local productization — finalize/install/seed wiring (no LLM)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_health_reports_llm_readiness():
    from skillos.api.server import health

    body = await health()
    assert body["status"] == "ok"
    assert "llm" in body
    assert "provider_ready" in body["llm"]
    assert body["llm"]["mode"] in ("cloud", "ollama", "missing", "error", "unknown")


@pytest.mark.asyncio
async def test_known_issues_doc():
    from skillos.api.docs_api import known_issues

    body = await known_issues()
    assert body["format"] == "markdown"
    assert "DEEPSEEK" in body["content"] or "Trust Tier" in body["content"]
    assert body["title"]


@pytest.fixture
def client():
    from skillos.api.skills import router as skills_router

    app = FastAPI()
    app.include_router(skills_router, prefix="/api/skills")
    return TestClient(app)


class TestCreateInstallContent:
    def test_create_with_content_persists_without_llm(self, client, tmp_path, monkeypatch):
        from skillos.api import skills_extract

        md = "---\nname: Local Install Demo\ntrust_tier: draft\n---\n\n# Body\n\nDo X then Y.\n"
        fake_ep = {
            "skill_name": "Local Install Demo",
            "trust_tier": "draft",
            "gates": {},
            "verified": 0,
            "pending": 0,
            "total_claims": 0,
        }

        with patch.object(skills_extract, "_persist_created_skill", return_value=fake_ep) as persist:
            with patch.object(skills_extract, "_tenant_context_from_auth", return_value=None):
                with patch.object(skills_extract, "_reset_tenant"):
                    resp = client.post(
                        "/api/skills/create",
                        json={"text": "Local Install Demo", "content": md},
                    )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["skill_saved"] == "Local Install Demo"
        assert data.get("trust_tier") == "draft"
        persist.assert_called_once()
        args, kwargs = persist.call_args
        assert args[0] == "Local Install Demo"
        assert "Do X then Y" in args[1]
        assert kwargs.get("source_type") == "marketplace"


class TestFinalizePersist:
    def test_finalize_uses_persist_pipeline(self, client):
        from skillos.api import skills_extract

        agent = MagicMock()
        agent.is_active = True
        agent._context = ["u", "a", "u2", "a2"]
        agent._phase = MagicMock()
        agent._phase.name = "GENERATING"
        agent._turn = 3
        agent.draft_name = "Demo Skill"
        agent._assess_draft_quality.return_value = {"pct": 80}
        agent.handle.return_value = (
            "已生成",
            {"name": "Demo Skill", "content": "---\nname: Demo Skill\n---\n\n# Hi\n"},
        )
        agent._domain_template_id = ""
        agent._domain_template_ids = []

        session = MagicMock()
        session.id = "sess-1"
        session.agent = agent
        session.tenant_id = ""
        session.org_id = ""
        session.dept_id = ""
        session.user_id = ""
        session.channel = ""
        session.chat_id = ""
        session.add_turn = MagicMock()

        mgr = MagicMock()
        mgr.get.return_value = session

        fake_ep = {
            "skill_name": "Demo Skill",
            "trust_tier": "provisional",
            "gates": {"epistemic": {"passed": False}, "outcome": {"passed": False}},
            "verified": 0,
            "pending": 1,
            "total_claims": 1,
            "portable_slug": "demo-skill",
            "install_paths": {},
        }

        with patch("skillos.skills.session_manager.get_session_manager", return_value=mgr):
            with patch("skillos.skills.skill_store.list_skills", return_value=[]):
                with patch.object(skills_extract, "_persist_created_skill", return_value=fake_ep) as persist:
                    with patch.object(skills_extract, "_tenant_context_from_auth", return_value=None):
                        with patch.object(skills_extract, "_reset_tenant"):
                            with patch("skillos.config.get_config") as gc:
                                gc.return_value.to_llm_args.return_value = ()
                                resp = client.post("/api/skills/finalize?session_id=sess-1")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("skill_saved") == "Demo Skill"
        assert data.get("epistemic_summary", {}).get("trust_tier") == "provisional"
        persist.assert_called_once()


class TestHubSeed:
    def test_seed_idempotent_when_not_empty(self, tmp_path, monkeypatch):
        from skillos.marketplace import seed as seed_mod

        with patch.object(seed_mod, "seed_hub_from_local_skills", wraps=seed_mod.seed_hub_from_local_skills):
            with patch("skillos.marketplace.registry.get_stats", return_value={"total": 3}):
                result = seed_mod.seed_hub_from_local_skills()
        assert result["seeded"] == 0
        assert result["skipped"] == "catalog_not_empty"
