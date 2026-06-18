"""Sprint 3 — approval flow, Feishu webhook, MCP tenant."""


import uuid
from unittest.mock import MagicMock, patch

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


def _register(client, name: str | None = None) -> dict:
    name = name or f"u_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200
    return r.json()


class TestApprovalFlow:
    def test_draft_submit_approve(self, client):
        admin = _register(client, "adm_appr")
        org = client.post(
            "/api/orgs",
            json={"display_name": "Approval Co"},
            headers={"Authorization": f"Bearer {admin['token']}"},
        ).json()
        token = org["token"]
        tenant_id = org["org"]["tenant_id"]

        from skillos.identity.context import TenantContext
        from skillos.identity.users import to_platform_user_id
        from skillos.skills import skill_store

        skill_name = "Refund Flow"
        body = "## S_body\n1. Check order\n## S_trigger\n- keywords: refund"
        tenant = TenantContext.organization(org["org"]["org_id"], user_id=to_platform_user_id(admin["user"]["user_id"]))
        skill_store.save_skill(skill_name, body, meta={"draft": True}, epistemic=False, tenant=tenant)

        slug = skill_store._slugify(skill_name)
        q = client.get("/api/approval/queue", headers={"Authorization": f"Bearer {token}"})
        assert q.status_code == 200
        assert any(s["skill_slug"] == slug for s in q.json()["drafts"])

        sub = client.post(f"/api/approval/{slug}/submit", headers={"Authorization": f"Bearer {token}"})
        assert sub.status_code == 200
        assert sub.json()["status"] == "pending"

        appr = client.post(
            f"/api/approval/{slug}/approve",
            json={"notes": "LGTM"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert appr.status_code == 200
        assert appr.json()["status"] == "published"

        raw = skill_store.load_skill_raw(skill_name, tenant=tenant)
        assert raw["meta"].get("visibility") == "team"
        assert "draft" not in raw["meta"] or not raw["meta"].get("draft")

        skill_store.delete_skill(skill_name, tenant=tenant)

    def test_member_cannot_approve(self, client):
        admin = _register(client, "adm_appr2")
        member = _register(client, "mem_appr2")
        org = client.post(
            "/api/orgs",
            json={"display_name": "Perm Co"},
            headers={"Authorization": f"Bearer {admin['token']}"},
        ).json()
        client.post(
            f"/api/orgs/{org['org']['org_id']}/members",
            json={"username": "mem_appr2", "role": "member"},
            headers={"Authorization": f"Bearer {org['token']}"},
        )

        from skillos.identity.context import TenantContext
        from skillos.identity.users import to_platform_user_id
        from skillos.skills import skill_store

        tenant = TenantContext.organization(org["org"]["org_id"])
        skill_name = "Pending Skill"
        skill_store.save_skill(skill_name, "## S_body\n1. x", meta={"draft": True}, epistemic=False, tenant=tenant)
        slug = skill_store._slugify(skill_name)

        client.post(f"/api/approval/{slug}/submit", headers={"Authorization": f"Bearer {org['token']}"})

        sw = client.post(
            "/api/workspaces/switch",
            json={"tenant_id": org["org"]["tenant_id"]},
            headers={"Authorization": f"Bearer {member['token']}"},
        )
        member_token = sw.json()["token"]

        denied = client.post(
            f"/api/approval/{slug}/approve",
            json={"notes": ""},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert denied.status_code == 403
        skill_store.delete_skill(skill_name, tenant=tenant)


class TestFeishuWebhook:
    def test_url_verification(self, client):
        r = client.post("/api/channels/feishu", json={"type": "url_verification", "challenge": "abc123"})
        assert r.status_code == 200
        assert r.json()["challenge"] == "abc123"

    def test_extract_message(self, client):
        mock_agent = MagicMock()
        mock_agent.start.return_value = "开始沉淀。"

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent):
            r = client.post(
                "/api/channels/feishu",
                json={
                    "header": {"event_type": "im.message.receive_v1"},
                    "event": {
                        "message": {
                            "chat_id": "oc_test",
                            "content": '{"text":"帮我沉淀退款流程"}',
                        },
                        "sender": {"sender_id": {"open_id": "ou_test"}},
                    },
                },
            )
        assert r.status_code == 200
        data = r.json()
        assert data.get("intent") == "extract"
        assert "开始" in data.get("reply", "")


class TestMcpTenant:
    def test_mcp_token_scopes_list_skills(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
        monkeypatch.setenv("SKILLOS_JWT_SECRET", "test-secret")

        import skillos.db as db_mod
        db_mod._local.conns = {}
        import skillos.marketplace.auth as auth_mod
        auth_mod._local.conn = None

        from skillos.marketplace.auth import create_user
        from skillos.identity.workspaces import ensure_personal_workspace
        from skillos.identity.middleware import issue_auth_token
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store
        from skillos.identity.mcp_context import mcp_tenant_context

        user = create_user("mcp_user", "pass1234", "member")
        ws = ensure_personal_workspace(user.user_id)
        token = issue_auth_token(user, tenant_id=ws.tenant_id)
        monkeypatch.setenv("SKILLOS_MCP_TOKEN", token)

        pid = ws.tenant_id.split(":", 1)[1]
        tenant = TenantContext.personal(pid)
        skill_store.save_skill("__mcp_only__", "## S_body\n1. a", epistemic=False, tenant=tenant)
        skill_store.save_skill("__legacy_other__", "## S_body\n1. b", epistemic=False)

        with mcp_tenant_context():
            names = skill_store.list_skills()
        assert "__mcp_only__" in names
        assert "__legacy_other__" not in names

        skill_store.delete_skill("__mcp_only__", tenant=tenant)
        skill_store.delete_skill("__legacy_other__")
