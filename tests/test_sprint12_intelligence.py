"""Sprint 12 / Phase 4 — MetaSkill + SkillOpt portal integration."""


import uuid

import pytest
from fastapi.testclient import TestClient


META_DOC = """---
type: metaskill
name: phase4-pipeline
---

# MetaSkill: phase4-pipeline

## Goal
串联两个步骤的测试流水线

## Pipeline
```pipeline
step_a: helper-skill
step_b: helper-skill  # depends_on: [step_a]
```
"""


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


def _register(client) -> dict:
    name = f"u_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200
    return r.json()


def _save_tenant_skills(client, reg: dict) -> tuple[str, str]:
    from skillos.identity.context import TenantContext
    from skillos.skills import skill_store

    tenant_id = reg["workspace"]["tenant_id"]
    uid = tenant_id.split(":", 1)[1]
    tenant = TenantContext.personal(uid)

    helper = f"helper_{uuid.uuid4().hex[:6]}"
    skill_store.save_skill(
        helper,
        "## S_body\n1. 帮助步骤\n",
        meta={"type": "skill"},
        epistemic=False,
        tenant=tenant,
    )

    meta_name = f"meta_{uuid.uuid4().hex[:6]}"
    skill_store.save_skill(
        meta_name,
        META_DOC,
        meta={"type": "metaskill"},
        epistemic=False,
        tenant=tenant,
    )
    return reg["token"], meta_name


class TestMetaSkillAPI:
    def test_get_pipeline_structure(self, client):
        reg = _register(client)
        token, meta_name = _save_tenant_skills(client, reg)

        r = client.get(
            f"/api/skills/{meta_name}/metaskill",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert len(body["steps"]) == 2
        assert body["steps"][1]["depends_on"] == ["step_a"]

    def test_dry_run_pipeline(self, client):
        reg = _register(client)
        token, meta_name = _save_tenant_skills(client, reg)

        r = client.post(
            f"/api/skills/{meta_name}/metaskill/run",
            json={"user_input": "test", "dry_run": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["dry_run"] is True
        assert body["success"] is True
        assert len(body["trace"]) >= 2

    def test_skill_detail_flags_metaskill(self, client):
        reg = _register(client)
        token, meta_name = _save_tenant_skills(client, reg)

        r = client.get(
            f"/api/skills/{meta_name}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["is_metaskill"] is True


class TestSkillOptPortalAPI:
    def test_evolution_state_requires_auth(self, client):
        r = client.get("/api/evolution/no-skill/state")
        assert r.status_code == 401

    def test_export_skillopt_tenant_scoped(self, client, tmp_path, monkeypatch):
        reg = _register(client)
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        tenant_id = reg["workspace"]["tenant_id"]
        uid = tenant_id.split(":", 1)[1]
        tenant = TenantContext.personal(uid)
        name = f"opt_{uuid.uuid4().hex[:6]}"
        skill_store.save_skill(
            name,
            "## S_body\n1. 优化测试步骤\n",
            epistemic=False,
            tenant=tenant,
        )

        export_root = tmp_path / "exports"
        monkeypatch.setattr(
            "skillos.evolution.skillopt_export.DEFAULT_EXPORT_ROOT",
            export_root,
        )

        r = client.post(
            f"/api/evolution/{name}/export-skillopt",
            headers={"Authorization": f"Bearer {reg['token']}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert "skillopt" in body["export_dir"]

    def test_evolution_route_and_state(self, client):
        reg = _register(client)
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        tenant_id = reg["workspace"]["tenant_id"]
        uid = tenant_id.split(":", 1)[1]
        tenant = TenantContext.personal(uid)
        name = f"evo_{uuid.uuid4().hex[:6]}"
        skill_store.save_skill(name, "## S_body\n1. x\n", epistemic=False, tenant=tenant)
        token = reg["token"]
        headers = {"Authorization": f"Bearer {token}"}

        state = client.get(f"/api/evolution/{name}/state", headers=headers)
        assert state.status_code == 200
        assert state.json()["skill"] == name

        route = client.post(f"/api/evolution/{name}/route", headers=headers)
        assert route.status_code == 200
        assert "routing" in route.json()
