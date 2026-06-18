"""Sprint 0 — tenant identity and skill path isolation."""


import os
from pathlib import Path

import pytest


@pytest.fixture
def tenant_env(tmp_path, monkeypatch):
    """Isolated data dir; legacy mode off for tenant tests."""
    data = tmp_path / "data"
    db = data / "skillhub.db"
    monkeypatch.setenv("SKILLOS_DATA_DIR", str(data))
    monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
    monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(tmp_path / "legacy_skills"))
    # Reset thread-local db connections
    import skillos.db as db_mod
    if hasattr(db_mod._local, "conns"):
        db_mod._local.conns = {}
    import skillos.marketplace.auth as auth_mod
    if hasattr(auth_mod._local, "conn"):
        auth_mod._local.conn = None
    yield data
    if hasattr(db_mod._local, "conns"):
        db_mod._local.conns = {}


class TestTenantContext:
    def test_personal_skills_root(self, tenant_env):
        from skillos.identity.context import TenantContext
        ctx = TenantContext.personal("alice")
        root = ctx.skills_root()
        assert root == tenant_env / "tenants" / "personal" / "usr_alice" / "skills"
        assert ctx.tenant_id == "personal:usr_alice"

    def test_org_skills_root(self, tenant_env):
        from skillos.identity.context import TenantContext
        ctx = TenantContext.organization("acme", user_id="bob", dept_id="fin")
        root = ctx.skills_root()
        assert "org" in str(root)
        assert "acme" in str(root)
        assert "departments" in str(root)
        assert ctx.tenant_id.startswith("org:")


class TestSkillStoreTenantIsolation:
    def test_personal_and_org_do_not_share_skills(self, tenant_env):
        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        body = "## S_body\n1. step\n## S_trigger\n- keywords: t"
        p = TenantContext.personal("u1")
        o = TenantContext.organization("o1", user_id="u2")

        skill_store.save_skill("__tenant_a__", body, epistemic=False, tenant=p)
        skill_store.save_skill("__tenant_b__", body, epistemic=False, tenant=o)

        assert skill_store.skill_exists("__tenant_a__", tenant=p)
        assert not skill_store.skill_exists("__tenant_a__", tenant=o)
        assert skill_store.skill_exists("__tenant_b__", tenant=o)
        assert skill_store.list_skills(tenant=p) == ["__tenant_a__"]
        assert skill_store.list_skills(tenant=o) == ["__tenant_b__"]

        raw = skill_store.load_skill_raw("__tenant_a__", tenant=p)
        assert raw["meta"].get("tenant_id") == p.tenant_id

        skill_store.delete_skill("__tenant_a__", tenant=p)
        skill_store.delete_skill("__tenant_b__", tenant=o)

    def test_legacy_mode_uses_legacy_dir(self, tmp_path, monkeypatch):
        legacy = tmp_path / "legacy"
        legacy.mkdir()
        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(legacy))
        monkeypatch.setenv("SKILLOS_LEGACY_MODE", "true")

        from skillos.identity.context import reset_tenant_context, set_tenant_context
        from skillos.skills.skill_store import resolve_skills_root, save_skill, skill_exists, delete_skill

        token = set_tenant_context(None)
        try:
            root = resolve_skills_root()
            assert root == legacy.resolve()
            save_skill("__legacy_test__", "## S_body\n1. x", epistemic=False)
            assert skill_exists("__legacy_test__")
            delete_skill("__legacy_test__")
        finally:
            reset_tenant_context(token)


class TestIdentityModels:
    def test_create_personal_tenant_idempotent(self, tenant_env):
        from skillos.identity.models import create_personal_tenant, get_tenant

        t1 = create_personal_tenant("carol")
        t2 = create_personal_tenant("carol")
        assert t1.tenant_id == t2.tenant_id
        assert get_tenant(t1.tenant_id) is not None

    def test_create_organization(self, tenant_env):
        import uuid
        from skillos.identity.models import create_organization, get_memberships

        label = f"ACME-{uuid.uuid4().hex[:6]}"
        org, tenant, mem = create_organization(label, owner_user_id="dave")
        assert org.display_name == label
        assert tenant.tenant_type == "organization"
        assert mem.role == "org_admin"
        memberships = get_memberships("dave")
        assert any(m.org_id == org.org_id for m in memberships)


class TestMigrationScript:
    def test_migrate_dry_run(self, tmp_path, monkeypatch):
        import importlib.util

        legacy = tmp_path / "skills"
        (legacy / "demo-skill").mkdir(parents=True)
        (legacy / "demo-skill" / "SKILL.md").write_text("# demo", encoding="utf-8")
        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(legacy))
        monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))

        script = Path(__file__).resolve().parents[1] / "scripts" / "migrate_legacy_skills.py"
        spec = importlib.util.spec_from_file_location("migrate_legacy_skills", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        r = mod.migrate(target="org:default", dry_run=True)
        assert r["copied"] == 1
