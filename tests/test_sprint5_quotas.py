"""Sprint 5 — quotas, cross-tenant security, usage API."""


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


class TestSkillQuota:
    def test_personal_skill_limit(self, client):
        reg = _register(client)
        tenant_id = reg["workspace"]["tenant_id"]
        platform_uid = tenant_id.split(":", 1)[1]

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store
        from skillos.billing.usage import QuotaExceededError, PERSONAL_FREE_MAX_SKILLS

        tenant = TenantContext.personal(platform_uid)
        for i in range(PERSONAL_FREE_MAX_SKILLS):
            skill_store.save_skill(f"qskill_{i}", "## S_body\n1. x", epistemic=False, tenant=tenant)

        with pytest.raises(QuotaExceededError) as exc:
            skill_store.save_skill("qskill_overflow", "## S_body\n1. x", epistemic=False, tenant=tenant)
        assert exc.value.code == "skill_limit"

        for i in range(PERSONAL_FREE_MAX_SKILLS):
            skill_store.delete_skill(f"qskill_{i}", tenant=tenant)

    def test_usage_api(self, client):
        reg = _register(client)
        r = client.get("/api/usage/me", headers={"Authorization": f"Bearer {reg['token']}"})
        assert r.status_code == 200
        data = r.json()
        assert data["plan"] == "personal_free"
        assert data["skills"]["limit"] == 10
        assert data["llm_calls"]["limit"] == 50


class TestCrossTenantSecurity:
    def test_cannot_read_other_tenant_skill(self, client):
        user_a = _register(client, "tenant_a")
        user_b = _register(client, "tenant_b")

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        tid_a = user_a["workspace"]["tenant_id"].split(":", 1)[1]
        tenant_a = TenantContext.personal(tid_a)
        skill_store.save_skill("secret-skill-a", "## S_body\n1. secret", epistemic=False, tenant=tenant_a)

        r = client.get(
            "/api/skills/secret-skill-a",
            headers={"Authorization": f"Bearer {user_b['token']}"},
        )
        assert r.status_code == 404

        r_ok = client.get(
            "/api/skills/secret-skill-a",
            headers={"Authorization": f"Bearer {user_a['token']}"},
        )
        assert r_ok.status_code == 200

        skill_store.delete_skill("secret-skill-a", tenant=tenant_a)


class TestByok:
    def test_byok_exempt_llm_quota(self, client):
        from skillos.billing.usage import (
            PERSONAL_FREE_MAX_LLM_MONTHLY,
            QuotaExceededError,
            check_llm_quota,
            record_llm_usage,
            set_user_byok,
        )

        reg = _register(client)
        tid = reg["workspace"]["tenant_id"]
        uid = reg["user"]["user_id"]

        for _ in range(PERSONAL_FREE_MAX_LLM_MONTHLY):
            record_llm_usage(tid, f"usr_{uid}")

        with pytest.raises(QuotaExceededError):
            check_llm_quota(tid, f"usr_{uid}")

        set_user_byok(uid, enabled=True, api_key="sk-test-key-12345678")
        check_llm_quota(tid, f"usr_{uid}")  # should not raise
