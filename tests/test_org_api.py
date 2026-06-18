"""Sprint 2 — Organization API and pilot bootstrap."""

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


class TestOrgAPI:
    def test_create_org_and_list(self, client):
        reg = _register(client)
        token = reg["token"]

        created = client.post(
            "/api/orgs",
            json={"display_name": "Acme Pilot"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert created.status_code == 200
        body = created.json()
        assert body["org"]["display_name"] == "Acme Pilot"
        assert body["org"]["tenant_id"].startswith("org:")
        assert body["token"]

        listed = client.get("/api/orgs", headers={"Authorization": f"Bearer {body['token']}"})
        assert listed.status_code == 200
        orgs = listed.json()["organizations"]
        assert len(orgs) == 1
        assert orgs[0]["role"] == "org_admin"

    def test_invite_member(self, client):
        admin = _register(client, "admin_org")
        member = _register(client, "member_org")

        org = client.post(
            "/api/orgs",
            json={"display_name": "Invite Test"},
            headers={"Authorization": f"Bearer {admin['token']}"},
        ).json()
        admin_token = org["token"]
        org_id = org["org"]["org_id"]

        invited = client.post(
            f"/api/orgs/{org_id}/members",
            json={"username": "member_org", "role": "member", "dept_id": "finance"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert invited.status_code == 200
        assert invited.json()["member"]["dept_id"] == "finance"

        members = client.get(
            f"/api/orgs/{org_id}/members",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert members.status_code == 200
        names = [m["username"] for m in members.json()["members"]]
        assert "admin_org" in names
        assert "member_org" in names

        # Member sees org in workspaces
        member_ws = client.get(
            "/api/workspaces/list",
            headers={"Authorization": f"Bearer {member['token']}"},
        )
        tids = [w["tenant_id"] for w in member_ws.json()["workspaces"]]
        assert org["org"]["tenant_id"] in tids

    def test_non_admin_cannot_invite(self, client):
        admin = _register(client, "adm2")
        member = _register(client, "mem2")

        org = client.post(
            "/api/orgs",
            json={"display_name": "Perm Test"},
            headers={"Authorization": f"Bearer {admin['token']}"},
        ).json()
        org_id = org["org"]["org_id"]

        client.post(
            f"/api/orgs/{org_id}/members",
            json={"username": "mem2", "role": "member"},
            headers={"Authorization": f"Bearer {org['token']}"},
        )

        denied = client.post(
            f"/api/orgs/{org_id}/members",
            json={"username": "adm2", "role": "member"},
            headers={"Authorization": f"Bearer {member['token']}"},
        )
        assert denied.status_code == 403


class TestPilotBootstrap:
    def test_bootstrap_dry_run(self):
        import subprocess
        import sys

        r = subprocess.run(
            [sys.executable, "scripts/pilot_bootstrap.py", "--dry-run"],
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert "pilot_admin" in r.stdout

    def test_bootstrap_creates_org(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("SKILLOS_LEGACY_MODE", "false")
        monkeypatch.setenv("SKILLOS_JWT_SECRET", "test-secret")
        import skillos.db as db_mod
        db_mod._local.conns = {}
        import skillos.marketplace.auth as auth_mod
        auth_mod._local.conn = None

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pilot_bootstrap",
            __import__("pathlib").Path(__file__).resolve().parents[1] / "scripts" / "pilot_bootstrap.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        assert mod.bootstrap(org_name="Pilot Corp") == 0
        manifest = tmp_path / "data" / "pilot" / "manifest.json"
        assert manifest.exists()
        import json
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["org_name"] == "Pilot Corp"
        assert len(data["users"]) == 7
