"""Sprint 9–12 — Pro plan, audit export, catalog, SLA."""


import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("SKILLOS_DATA_DIR", str(data))
    monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
    monkeypatch.setenv("SKILLOS_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SKILLOS_PRO_BETA_CODE", "test-pro-code")
    monkeypatch.setenv("SKILLHUB_READONLY", "true")
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


class TestPersonalPro:
    def test_enable_pro_beta(self, client):
        reg = _register(client)
        bad = client.post(
            "/api/billing/enable-pro",
            json={"beta_code": "wrong"},
            headers={"Authorization": f"Bearer {reg['token']}"},
        )
        assert bad.status_code == 403

        ok = client.post(
            "/api/billing/enable-pro",
            json={"beta_code": "test-pro-code"},
            headers={"Authorization": f"Bearer {reg['token']}"},
        )
        assert ok.status_code == 200
        assert ok.json()["plan"] == "personal_pro"

        usage = client.get("/api/usage/me", headers={"Authorization": f"Bearer {reg['token']}"})
        assert usage.json()["plan"] == "personal_pro"
        assert usage.json()["llm_calls"]["limit"] == 500


class TestMarketplaceReadonly:
    def test_catalog_readonly(self, client):
        r = client.get("/api/marketplace/catalog")
        assert r.status_code == 200
        body = r.json()
        assert body["read_only"] is True
        assert body["ugc_publish"] is False
        assert "categories" in body

    def test_pricing_get_default(self, client):
        r = client.get("/api/marketplace/pricing/get?skill_id=sk_test")
        assert r.status_code == 200
        assert r.json()["model"] == "free"

    def test_pricing_set_blocked_in_readonly(self, client):
        reg = _register(client)
        r = client.post(
            "/api/marketplace/pricing/set",
            json={"skill_id": "sk_test", "model": "one_time", "price": 9.99},
            headers={"Authorization": f"Bearer {reg['token']}"},
        )
        assert r.status_code == 403

    def test_publish_blocked(self, client):
        reg = _register(client)
        r = client.post(
            "/api/marketplace/publish",
            json={"name": "x", "content": "# skill\nbody"},
            headers={"Authorization": f"Bearer {reg['token']}"},
        )
        assert r.status_code == 403

    def test_recommendations_excludes_owned(self, client):
        reg = _register(client)
        token = reg["token"]
        r = client.get(
            "/api/marketplace/recommendations?limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "recommendations" in body
        assert isinstance(body["recommendations"], list)


class TestAuditExport:
    def test_audit_csv(self, client):
        reg = _register(client)
        org = client.post(
            "/api/orgs",
            json={"display_name": "Audit Org"},
            headers={"Authorization": f"Bearer {reg['token']}"},
        ).json()
        token = org["token"]
        org_id = org["org"]["org_id"]

        r = client.get(
            f"/api/orgs/{org_id}/admin/audit/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "action" in r.text


class TestSLAAndPlatform:
    def test_sla_endpoint(self, client):
        client.get("/health")
        r = client.get("/api/analytics/sla")
        assert r.status_code == 200
        assert "uptime_percent" in r.json()

    def test_platform_overview(self, client):
        reg = _register(client)
        org = client.post(
            "/api/orgs",
            json={"display_name": "Scale Org"},
            headers={"Authorization": f"Bearer {reg['token']}"},
        ).json()
        r = client.get(
            "/api/analytics/platform",
            headers={"Authorization": f"Bearer {org['token']}"},
        )
        assert r.status_code == 200
        assert r.json()["skills"]["goal"] == 200
