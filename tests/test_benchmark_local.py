"""Local benchmark lookup tests."""

from pathlib import Path

from skillos.benchmark_local import (
    REFERENCE_QUICK8_SKILLS,
    _select_quick8_tasks,
    latest_bench_regression,
    latest_quick8_for_skill,
    local_bench_summary,
    reference_bench_dashboard,
)


def test_latest_quick8_for_refund_skill():
    row = latest_quick8_for_skill("电商客服退款处理")
    if row is None:
        return
    assert row.get("skill") == "电商客服退款处理"
    assert "improvement_pct" in row
    assert row.get("task_ids")


def test_local_bench_summary():
    summary = local_bench_summary("CSV数据清洗助手")
    assert summary["skill"] == "CSV数据清洗助手"
    assert "latest_quick8" in summary
    assert "quick8_history" in summary


def test_reference_bench_dashboard():
    dash = reference_bench_dashboard()
    assert "reference_skills" in dash
    assert "generalize_skills" in dash
    assert len(dash["reference_skills"]) == len(REFERENCE_QUICK8_SKILLS)
    assert "latest_regression" in dash


def test_latest_bench_regression():
    reg = latest_bench_regression()
    if reg is None:
        return
    assert "summary" in reg
    assert "quick8" in reg
    assert "domain_smoke" in reg
    assert "generalize_domain_quick8" in reg
    if reg.get("generalize_domain_quick8"):
        assert reg["summary"].get("generalize_pass") is not None


def test_generalize_bench_dashboard():
    from skillos.benchmark_local import generalize_bench_dashboard
    from skillos.skills.bench_cohorts import GENERALIZE_SKILL_NAMES

    rows = generalize_bench_dashboard()
    assert len(rows) == len(GENERALIZE_SKILL_NAMES)
    for row in rows:
        assert row.get("skill") in GENERALIZE_SKILL_NAMES
        assert row.get("domain_template")


def test_latest_post_extract_regression_optional():
    from skillos.benchmark_local import latest_post_extract_regression

    reg = latest_post_extract_regression()
    if reg is None:
        return
    assert "all_pass" in reg or "report" in reg


def test_sync_reference_packs():
    from scripts.repair_reference_packs import REFERENCE_TEMPLATES, sync_reference_packs

    rows = sync_reference_packs(dry_run=True)
    assert len(rows) == len(REFERENCE_TEMPLATES)
    assert all(r.get("ok") for r in rows)


def test_select_domain_tasks_refund():
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS
    from skillos.knowledge.skill_routing import load_skill_routing_info

    md = Path(__file__).resolve().parents[1] / "skills" / "电商客服退款处理" / "SKILL.md"
    if not md.exists():
        return
    info = load_skill_routing_info(str(md))
    tasks = _select_quick8_tasks(
        info["name"], info["content"], info["bench_categories"], SKILLSBENCH_TASKS, domain_only=True,
    )
    ids = [t.task_id for t in tasks]
    assert "workflow-064" in ids


def test_task_compare_rows_single_skill_format():
    from skillos.benchmark_local import _task_compare_rows

    rows = _task_compare_rows({"task_compare": {"skill": "a", "delta": 1}})
    assert len(rows) == 1 and rows[0]["skill"] == "a"
