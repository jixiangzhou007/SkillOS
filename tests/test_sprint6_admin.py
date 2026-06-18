"""Sprint 6 — org admin console, departments, skill copy, search."""

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


def _register(client, name: str | None = None) -> dict:
    name = name or f"u_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200
    return r.json()


def _create_org(client, token: str, name: str = "S6 Corp") -> dict:
    r = client.post(
        "/api/orgs",
        json={"display_name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    return r.json()


class TestOrgAdmin:
    def test_admin_overview_and_departments(self, client):
        reg = _register(client)
        org = _create_org(client, reg["token"])
        token = org["token"]
        org_id = org["org"]["org_id"]

        dept = client.post(
            f"/api/orgs/{org_id}/departments",
            json={"name": "Engineering"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dept.status_code == 200
        assert dept.json()["name"] == "Engineering"

        listed = client.get(
            f"/api/orgs/{org_id}/departments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listed.status_code == 200
        assert len(listed.json()["departments"]) == 1

        overview = client.get(
            f"/api/orgs/{org_id}/admin/overview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert overview.status_code == 200
        body = overview.json()
        assert body["members_count"] >= 1
        assert body["departments_count"] == 1

    def test_quota_update(self, client):
        reg = _register(client)
        org = _create_org(client, reg["token"])
        token = org["token"]
        org_id = org["org"]["org_id"]

        r = client.patch(
            f"/api/orgs/{org_id}/admin/quota",
            json={"max_skills": 100, "max_llm_monthly": 500},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["quota"]["max_skills"] == 100


class TestSkillCopyAndSearch:
    def test_copy_personal_skill_to_org(self, client):
        reg = _register(client)
        personal_tid = reg["workspace"]["tenant_id"]
        platform_uid = personal_tid.split(":", 1)[1]

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        personal = TenantContext.personal(platform_uid)
        skill_store.save_skill("my-workflow", "## S_body\n1. step", epistemic=False, tenant=personal)

        org = _create_org(client, reg["token"])
        org_id = org["org"]["org_id"]

        copied = client.post(
            "/api/skills/my-workflow/copy-to-org",
            json={"org_id": org_id},
            headers={"Authorization": f"Bearer {reg['token']}"},
        )
        assert copied.status_code == 200
        assert copied.json()["skill_saved"] == "my-workflow"
        assert copied.json()["approval_status"] == "draft"

        org_tenant = TenantContext.organization(org_id)
        assert skill_store.skill_exists("my-workflow", tenant=org_tenant)

        skill_store.delete_skill("my-workflow", tenant=personal)
        skill_store.delete_skill("my-workflow", tenant=org_tenant)

    def test_skill_list_search(self, client):
        reg = _register(client)
        org = _create_org(client, reg["token"])
        token = org["token"]
        org_id = org["org"]["org_id"]
        tenant = __import__("skillos.identity.context", fromlist=["TenantContext"]).TenantContext.organization(org_id)

        from skillos.skills import skill_store
        skill_store.save_skill("refund-flow", "## S_body\n1. x", epistemic=False, tenant=tenant)
        skill_store.save_skill("other-skill", "## S_body\n1. y", epistemic=False, tenant=tenant)

        r = client.get(
            "/api/skills/?q=refund",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "refund-flow" in names
        assert "other-skill" not in names

        skill_store.delete_skill("refund-flow", tenant=tenant)
        skill_store.delete_skill("other-skill", tenant=tenant)


class TestPersonalToOrgConversion:
    def test_create_org_from_personal(self, client):
        reg = _register(client, "convert_user")
        org = _create_org(client, reg["token"], "Converted Team")
        assert org["org"]["display_name"] == "Converted Team"

        listed = client.get(
            "/api/orgs",
            headers={"Authorization": f"Bearer {org['token']}"},
        )
        assert listed.status_code == 200
        assert any(o["display_name"] == "Converted Team" for o in listed.json()["organizations"])
