"""Sprint 2 — Web portal v0: register → list tenant-scoped skills."""

from __future__ import annotations

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


class TestPortalE2E:
    def test_register_login_list_skills_scoped(self, client):
        name = f"portal_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        assert reg.status_code == 200
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]
        platform_uid = tenant_id.split(":", 1)[1]

        listed = client.get("/api/skills/", headers={"Authorization": f"Bearer {token}"})
        assert listed.status_code == 200
        assert listed.json() == []

        skill_name = f"web_{uuid.uuid4().hex[:6]}"
        body = f"## S_body\n1. step\n## S_trigger\n- keywords: t\nname: {skill_name}"
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        tenant = TenantContext.personal(platform_uid)
        skill_store.save_skill(skill_name, body, epistemic=False, tenant=tenant)

        listed2 = client.get("/api/skills/", headers={"Authorization": f"Bearer {token}"})
        names = [s["name"] for s in listed2.json()]
        assert skill_name in names

        skill_store.delete_skill(skill_name, tenant=tenant)

    def test_create_via_api_with_jwt(self, client):
        name = f"api_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]
        platform_uid = tenant_id.split(":", 1)[1]

        skill_name = f"created_{uuid.uuid4().hex[:6]}"
        doc_body = f"## S_body\n1. step\n## S_trigger\n- keywords: t\nname: {skill_name}"
        mock_agent = MagicMock()
        mock_agent.is_active = True
        mock_agent.handle.return_value = ("完成", {"name": skill_name, "content": doc_body})

        with patch("skillos.skills.agent.SkillExtractionAgent", return_value=mock_agent):
            r = client.post(
                "/api/skills/create",
                json={"text": "创建技能"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200
        assert r.json().get("skill_saved") == skill_name

        listed = client.get("/api/skills/", headers={"Authorization": f"Bearer {token}"})
        assert skill_name in [s["name"] for s in listed.json()]

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store
        skill_store.delete_skill(skill_name, tenant=TenantContext.personal(platform_uid))

    def test_login_page_served(self, client):
        r = client.get("/login.html")
        assert r.status_code == 200
        assert "注册账号" in r.text
        assert "/api/auth/login" in r.text

    def test_usage_and_export_with_jwt(self, client):
        name = f"portal_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]
        platform_uid = tenant_id.split(":", 1)[1]

        usage = client.get("/api/usage/me", headers={"Authorization": f"Bearer {token}"})
        assert usage.status_code == 200
        assert usage.json()["plan"] in ("personal_free", "personal_pro")

        rec = client.get(
            "/api/marketplace/recommendations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec.status_code == 200

        skill_name = f"exp_{uuid.uuid4().hex[:6]}"
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        tenant = TenantContext.personal(platform_uid)
        body = f"## S_body\n1. step\n## S_trigger\n- keywords: t\nname: {skill_name}"
        skill_store.save_skill(skill_name, body, epistemic=False, tenant=tenant)

        exp = client.get(
            f"/api/skills/{skill_name}/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert exp.status_code == 200
        assert exp.json().get("name") == skill_name

        sim = client.get(
            f"/api/skills/{skill_name}/similar",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sim.status_code == 200
        assert sim.json().get("skill") == skill_name

        skill_store.delete_skill(skill_name, tenant=tenant)
