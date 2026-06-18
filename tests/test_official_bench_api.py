"""Official SkillsBench API service tests."""
from pathlib import Path

from skillos.official_skillsbench.service import export_skill_to_dir, latest_for_skill, plan_for_skill, trigger_official_ci


def test_plan_for_csv_skill():
    plan = plan_for_skill("CSV数据清洗助手")
    assert "sales-pivot-analysis" in plan["suggested_official_tasks"]
    assert plan["commands"]["agent_compare"]
    summary = latest_for_skill("CSV数据清洗助手")
    assert summary["skill"] == "CSV数据清洗助手"
    assert "plan" in summary
    assert "latest_quick8" in summary
    assert "quick8_history" in summary


def test_bench_summary_endpoint():
    from fastapi.testclient import TestClient

    from skillos.api.server import app

    client = TestClient(app)
    r = client.get("/api/bench/official/summary")
    assert r.status_code == 200
    body = r.json()
    assert "reference_skills" in body
    assert len(body["reference_skills"]) >= 1
    assert "latest_regression" in body


def test_regression_latest_endpoint():
    from fastapi.testclient import TestClient

    from skillos.api.server import app

    client = TestClient(app)
    r = client.get("/api/bench/official/regression/latest")
    if r.status_code == 404:
        return
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body


def test_post_extract_regression_endpoint():
    from fastapi.testclient import TestClient

    from skillos.api.server import app

    client = TestClient(app)
    r = client.get("/api/bench/official/regression/post-extract/latest")
    assert r.status_code in (200, 404)


def test_bench_summary_includes_post_extract():
    from fastapi.testclient import TestClient

    from skillos.api.server import app

    client = TestClient(app)
    r = client.get("/api/bench/official/summary")
    assert r.status_code == 200
    assert "latest_post_extract" in r.json()


def test_skill_smoke_endpoint():
    from fastapi.testclient import TestClient

    from skillos.api.server import app

    client = TestClient(app)
    r = client.get("/api/bench/official/skills/CSV数据清洗助手/smoke")
    if r.status_code == 404:
        return
    assert r.status_code == 200
    body = r.json()
    assert body["skill"] == "CSV数据清洗助手"
    assert "suite" in body


def test_export_skill_to_dir(tmp_path):
    try:
        out = export_skill_to_dir("CSV数据清洗助手", tmp_path)
    except FileNotFoundError:
        return
    assert out["skill"] == "CSV数据清洗助手"
    assert Path(out["exported_path"]).joinpath("SKILL.md").exists()


def test_trigger_ci_without_github_env():
    result = trigger_official_ci("CSV数据清洗助手")
    assert result["ok"] is False
    assert "manual" in result
    assert result["preset"] == "csv-sales-pivot"


def test_trigger_ci_refund_preset():
    result = trigger_official_ci("电商客服退款处理")
    assert result["preset"] == "refund-invoice-fraud"
    assert result["manual"]["compare_preset"] == "refund-invoice-fraud"
