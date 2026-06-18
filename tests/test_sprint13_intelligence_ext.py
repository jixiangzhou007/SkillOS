"""Sprint 13 — DAG viz, role templates, SkillOpt CLI."""


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


class TestPipelineMermaid:
    def test_pipeline_to_mermaid(self):
        from skillos.skills.metaskill import PipelineStep, pipeline_to_mermaid

        steps = [
            PipelineStep(name="a", skill_name="skill-a"),
            PipelineStep(name="b", skill_name="skill-b", depends_on=["a"]),
        ]
        chart = pipeline_to_mermaid(steps)
        assert "flowchart TD" in chart
        assert "a-->b" in chart.replace(" ", "")


class TestRoleTemplates:
    def test_list_role_templates(self, client):
        r = client.get("/api/intelligence/role-templates")
        assert r.status_code == 200
        templates = r.json()["templates"]
        assert len(templates) >= 5
        assert any(t["role_id"] == "customer_service" for t in templates)

    def test_role_recommendations_with_blueprint(self, client):
        r = client.get("/api/intelligence/role-templates/customer_service/recommendations")
        assert r.status_code == 200
        body = r.json()
        assert body["role_id"] == "customer_service"
        assert body["metaskill_blueprint"] is not None
        assert "flowchart TD" in body["metaskill_blueprint"]["mermaid"]

    def test_metaskill_api_includes_mermaid(self, client, tmp_path):
        name = f"u_{uuid.uuid4().hex[:8]}"
        reg = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]
        uid = tenant_id.split(":", 1)[1]

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        meta_name = f"meta_{uuid.uuid4().hex[:6]}"
        doc = """---
type: metaskill
---
# MetaSkill: test-dag
## Goal
test
## Pipeline
```pipeline
s1: helper
s2: helper  # depends_on: [s1]
```
"""
        skill_store.save_skill(meta_name, doc, meta={"type": "metaskill"}, epistemic=False, tenant=TenantContext.personal(uid))

        r = client.get(
            f"/api/skills/{meta_name}/metaskill",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "mermaid" in r.json()
        assert "flowchart TD" in r.json()["mermaid"]


class TestSkillOptRunner:
    def test_validate_bundle(self, tmp_path):
        from skillos.evolution.skillopt_runner import validate_bundle

        d = tmp_path / "bundle"
        d.mkdir()
        (d / "best_skill.md").write_text("# skill", encoding="utf-8")
        (d / "manifest.json").write_text("{}", encoding="utf-8")
        info = validate_bundle(d)
        assert info["ok"] is True

    def test_cli_export(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))
        from skillos.skills import skill_store
        from skillos.evolution.skillopt_export import export_for_skillopt
        from skillos.evolution.skillopt_runner import validate_bundle

        name = "cli-test-skill"
        skill_store.save_skill(name, "## S_body\n1. step\n", epistemic=False)
        result = export_for_skillopt(name, output_dir=tmp_path / "out")
        assert validate_bundle(result.export_dir)["ok"] is True

    def test_skillopt_run_api_dry(self, client, tmp_path, monkeypatch):
        reg = client.post("/api/auth/register", json={"username": f"u_{uuid.uuid4().hex[:6]}", "password": "pass1234"})
        token = reg.json()["token"]
        tenant_id = reg.json()["workspace"]["tenant_id"]
        uid = tenant_id.split(":", 1)[1]

        from skillos.identity.context import TenantContext
        from skillos.skills import skill_store

        name = f"cliapi_{uuid.uuid4().hex[:6]}"
        skill_store.save_skill(name, "## S_body\n1. x\n", epistemic=False, tenant=TenantContext.personal(uid))

        monkeypatch.setattr(
            "skillos.evolution.skillopt_export.DEFAULT_EXPORT_ROOT",
            tmp_path / "exports",
        )

        r = client.post(
            f"/api/evolution/{name}/skillopt-run?dry_run=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["dry_run"] is True
