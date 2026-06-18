"""Sprint 11 — governance verified rate, creator summary, backup."""


import uuid
import zipfile

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


def _create_org(client, token: str, name: str = "Gov Corp") -> dict:
    r = client.post(
        "/api/orgs",
        json={"display_name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    return r.json()


def _save_skill_with_epistemic(tenant, name: str, verified: int, pending: int) -> None:
    from skillos.skills import skill_store

    total = verified + pending
    meta = {
        "epistemic": {
            "total_claims": total,
            "verified": verified,
            "pending": pending,
            "pending_ids": [],
        }
    }
    skill_store.save_skill(
        name,
        f"## S_body\nTest skill {name}\n",
        meta=meta,
        epistemic=False,
        tenant=tenant,
    )


class TestOrgGovernance:
    def test_verified_rate_meets_target(self, client):
        reg = _register(client)
        org = _create_org(client, reg["token"])
        token = org["token"]
        org_id = org["org"]["org_id"]

        from skillos.identity.context import TenantContext

        tenant = TenantContext.organization(org_id)
        _save_skill_with_epistemic(tenant, "gov-good", verified=8, pending=2)
        _save_skill_with_epistemic(tenant, "gov-ok", verified=7, pending=3)

        r = client.get(
            f"/api/orgs/{org_id}/admin/governance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["skills_with_claims"] == 2
        assert body["org_verified_rate"] == 0.75
        assert body["meets_target"] is True
        assert body["skills_meeting_target"] == 2

    def test_at_risk_skills_listed(self, client):
        reg = _register(client)
        org = _create_org(client, reg["token"])
        token = org["token"]
        org_id = org["org"]["org_id"]

        from skillos.identity.context import TenantContext

        tenant = TenantContext.organization(org_id)
        _save_skill_with_epistemic(tenant, "gov-risk", verified=3, pending=7)

        r = client.get(
            f"/api/orgs/{org_id}/admin/governance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["meets_target"] is False
        assert len(body["at_risk_skills"]) == 1
        assert body["at_risk_skills"][0]["name"] == "gov-risk"


class TestPlatformGovernance:
    def test_platform_overview_includes_governance(self, client):
        reg = _register(client)
        org = _create_org(client, reg["token"])
        token = org["token"]
        org_id = org["org"]["org_id"]

        from skillos.identity.context import TenantContext

        tenant = TenantContext.organization(org_id)
        _save_skill_with_epistemic(tenant, "plat-gov", verified=9, pending=1)

        r = client.get(
            "/api/analytics/platform",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "governance" in body
        assert body["governance"]["platform_verified_rate"] == 0.9
        assert body["governance"]["meets_target"] is True


class TestCreatorSummary:
    def test_creator_summary_reserved(self, client):
        reg = _register(client)
        token = reg["token"]
        user_id = reg["user"]["user_id"]

        from skillos.marketplace.payments import create_purchase, set_price

        set_price("creator-skill", "one_time", 9.99)
        create_purchase("creator-skill", "buyer-x", author_id=user_id)

        r = client.get(
            "/api/billing/creator-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["payout_status"] == "reserved"
        assert body["total_sales"] >= 1


class TestBackupScript:
    def test_backup_creates_zip(self, tmp_path, monkeypatch):
        data = tmp_path / "data"
        data.mkdir()
        (data / "skillhub.db").write_text("fake", encoding="utf-8")
        tenants = data / "tenants" / "org" / "test"
        tenants.mkdir(parents=True)
        (tenants / "SKILL.md").write_text("# test", encoding="utf-8")

        monkeypatch.setenv("SKILLOS_DATA_DIR", str(data))
        out = tmp_path / "backup.zip"

        from scripts.backup_skillos_data import create_backup

        path = create_backup(out)
        assert path.exists()
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            assert any(n.endswith("skillhub.db") for n in names)
            assert any("tenants/" in n for n in names)
