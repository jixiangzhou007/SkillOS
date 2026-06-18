"""Sprint 1 — JWT auth, workspaces, register flow."""


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


class TestJWT:
    def test_issue_and_verify(self):
        from skillos.identity.jwt_auth import issue_jwt, verify_jwt

        token = issue_jwt({"sub": "u1", "tenant_id": "personal:usr_u1"})
        payload = verify_jwt(token)
        assert payload["sub"] == "u1"


class TestRegisterLogin:
    def test_register_returns_jwt_and_personal_workspace(self, client):
        name = f"user_{uuid.uuid4().hex[:8]}"
        r = client.post("/api/auth/register", json={"username": name, "password": "pass1234", "email": "a@b.c"})
        assert r.status_code == 200
        data = r.json()
        assert data["token_type"] == "Bearer"
        assert data["workspace"]["tenant_type"] == "personal"
        assert "personal:usr_" in data["workspace"]["tenant_id"]

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
        assert me.status_code == 200
        assert me.json()["user"]["username"] == name

    def test_login(self, client):
        name = f"login_{uuid.uuid4().hex[:8]}"
        client.post("/api/auth/register", json={"username": name, "password": "secret5678"})
        r = client.post("/api/auth/login", json={"username": name, "password": "secret5678"})
        assert r.status_code == 200
        assert "token" in r.json()


class TestWorkspaces:
    def test_switch_workspace_org(self, client):
        from skillos.identity.models import create_organization

        name = f"ws_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        token = reg.json()["token"]
        user_id = reg.json()["user"]["user_id"]

        org, _, _ = create_organization(f"Org-{name}", owner_user_id=user_id)

        listed = client.get("/api/workspaces/list", headers={"Authorization": f"Bearer {token}"})
        assert listed.status_code == 200
        tids = [w["tenant_id"] for w in listed.json()["workspaces"]]
        assert f"org:{org.org_id}" in tids

        sw = client.post(
            "/api/workspaces/switch",
            json={"tenant_id": f"org:{org.org_id}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sw.status_code == 200
        assert sw.json()["workspace"]["tenant_type"] == "organization"


class TestDispatchTenantAuth:
    """Sprint 2 — JWT injects tenant into dispatch/create (DoD)."""

    def test_dispatch_session_gets_tenant_from_jwt(self, client):
        from unittest.mock import MagicMock, patch

        from skillos.skills.session_manager import SessionManager

        name = f"disp_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]

        mock_agent = MagicMock()
        mock_agent.is_active = False
        mock_agent.start.return_value = "开始。"
        shared_mgr = SessionManager()

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent), patch(
            "skillos.skills.session_manager.SessionManager", return_value=shared_mgr
        ):
            resp = client.post(
                "/api/skills/dispatch",
                json={"message": "帮我沉淀退款流程", "mode": "chat"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        sid = resp.json()["session_id"]
        session = shared_mgr.get(sid)
        assert session is not None
        assert session.tenant_id == tenant_id

    def test_create_skill_writes_personal_tenant_dir(self, client):
        from unittest.mock import MagicMock, patch

        name = f"create_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]
        platform_uid = tenant_id.split(":", 1)[1]

        skill_name = f"skill_{uuid.uuid4().hex[:6]}"
        body = f"## S_body\n1. step\n## S_trigger\n- keywords: t\nname: {skill_name}"
        mock_agent = MagicMock()
        mock_agent.is_active = True
        mock_agent.handle.return_value = ("完成", {"name": skill_name, "content": body})

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent):
            resp = client.post(
                "/api/skills/create",
                json={"text": "创建测试技能"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert resp.json().get("skill_saved") == skill_name

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        tenant = TenantContext.personal(platform_uid)
        assert skill_store.skill_exists(skill_name, tenant=tenant)
        raw = skill_store.load_skill_raw(skill_name, tenant=tenant)
        assert raw["meta"].get("tenant_id") == tenant_id
        skill_store.delete_skill(skill_name, tenant=tenant)
