"""Sprint 7–8 — desensitize, dept quota, funnel, stability."""


import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("SKILLOS_DATA_DIR", str(data))
    monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
    monkeypatch.setenv("SKILLOS_JWT_SECRET", "test-secret")
    monkeypatch.setenv("SKILLOS_SKIP_DESENSITIZE", "0")
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


class TestDesensitize:
    def test_redacts_pii(self):
        from skillos.security.desensitize import desensitize_text

        text = "联系 13800138000 或 test@example.com，key=sk-abcdefghijklmnopqrstuv"
        out = desensitize_text(text)
        assert "13800138000" not in out
        assert "test@example.com" not in out
        assert "sk-abc" not in out


class TestFunnel:
    def test_register_tracks_funnel(self, client):
        _register(client)
        from skillos.analytics.funnel import get_funnel_summary
        summary = get_funnel_summary(days=30)
        assert summary["steps"]["register"] >= 1

    def test_funnel_api(self, client):
        reg = _register(client)
        r = client.get("/api/analytics/funnel", headers={"Authorization": f"Bearer {reg['token']}"})
        assert r.status_code == 200
        assert "steps" in r.json()


class TestDeptQuota:
    def test_dept_skill_limit(self, client):
        reg = _register(client)
        org = client.post(
            "/api/orgs",
            json={"display_name": "Quota Org"},
            headers={"Authorization": f"Bearer {reg['token']}"},
        ).json()
        token = org["token"]
        org_id = org["org"]["org_id"]

        dept = client.post(
            f"/api/orgs/{org_id}/departments",
            json={"name": "Small Team"},
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        dept_id = dept["dept_id"]

        client.patch(
            f"/api/orgs/{org_id}/departments/{dept_id}/quota",
            json={"max_skills": 1, "max_llm_monthly": 5},
            headers={"Authorization": f"Bearer {token}"},
        )

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store
        from skillos.billing.usage import QuotaExceededError

        tenant = TenantContext.organization(org_id, dept_id=dept_id)
        skill_store.save_skill("dept-skill-1", "## S_body\n1. x", epistemic=False, tenant=tenant)

        with pytest.raises(QuotaExceededError) as exc:
            skill_store.save_skill("dept-skill-2", "## S_body\n1. y", epistemic=False, tenant=tenant)
        assert exc.value.code == "dept_skill_limit"

        skill_store.delete_skill("dept-skill-1", tenant=tenant)


class TestStability:
    def test_stability_endpoint(self, client):
        r = client.get("/api/analytics/stability")
        assert r.status_code == 200
        body = r.json()
        assert "error_rate" in body
        assert "target_under_1pct" in body


class TestDocs:
    def test_quickstart_doc(self, client):
        r = client.get("/api/docs/quickstart")
        assert r.status_code == 200
        assert "Personal Free" in r.json()["content"]

    def test_graph_clusters_schema(self, client):
        r = client.get("/api/knowledge/graph/clusters")
        assert r.status_code == 200
        body = r.json()
        assert "clusters" in body
        assert "total_nodes" in body
        assert "total_edges" in body
        for c in body["clusters"]:
            assert "label" in c
            assert "nodes" in c
            assert "cohesion" in c
