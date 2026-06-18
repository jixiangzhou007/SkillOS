"""Tests for Path B auto cold-start."""

from __future__ import annotations

from skillos.skills.cold_start import (
    generate_heritage_body,
    has_static_heritage,
    insert_heritage_section,
    pattern_to_guidance,
    repair_domain_pack,
    should_run_cold_start,
)
from skillos.skills.domain_pack import get_smoke_task_ids, save_domain_pack


def test_pattern_to_guidance_reject():
    g = pattern_to_guidance("拒绝|退回")
    assert "拒绝" in g or "退回" in g


def test_should_run_cold_start_new_domain():
    assert should_run_cold_start("finance-expense-audit", {"domain_smoke": {"passed": False}})
    assert not should_run_cold_start("workflow-refund", {"domain_smoke": {"passed": False}})


def test_has_static_heritage():
    assert has_static_heritage("workflow-refund")
    assert not has_static_heritage("finance-expense-audit")


def test_generate_heritage_from_rubric():
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    task = next(t for t in SKILLSBENCH_TASKS if t.task_id == "workflow-082")
    body = generate_heritage_body("财务报销审计助手", [task], {"workflow-082": ["拒绝|退回"]})
    assert "应答" in body or "拒绝" in body or "超标" in body


def test_insert_heritage_section():
    base = "## S_trigger\nfoo\n\n## S_body\nbar\n"
    out = insert_heritage_section(base, "- rule one")
    assert "应答速查" in out
    assert "rule one" in out


def test_domain_pack_smoke_tasks(tmp_path, monkeypatch):
    from skillos.skills import domain_pack as dp

    monkeypatch.setattr(dp, "_PACKS_DIR", tmp_path)
    save_domain_pack({
        "domain_template": "test-domain",
        "smoke_tasks": ["workflow-082", "workflow-083"],
        "heritage_body": "test heritage",
        "anchor_tasks": ["workflow-082"],
    })
    assert get_smoke_task_ids("test-domain") == ("workflow-082", "workflow-083")


def test_pack_is_stale():
    from skillos.skills.domain_pack import pack_is_stale

    pack = {"anchor_tasks": ["workflow-064"]}
    assert pack_is_stale(pack, "finance-expense-audit")
    pack_ok = {"anchor_tasks": ["workflow-082", "workflow-083"]}
    assert not pack_is_stale(pack_ok, "finance-expense-audit")


def test_seed_missed_from_rubric():
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS
    from skillos.skills.cold_start import _seed_missed_from_rubric

    task = next(t for t in SKILLSBENCH_TASKS if t.task_id == "workflow-082")
    missed = _seed_missed_from_rubric([task])
    assert "workflow-082" in missed
    assert "拒绝|退回" in missed["workflow-082"]


def test_task_passes_expand_filter_finance():
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS
    from skillos.skills.domain_pack import task_passes_expand_filter

    by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
    assert task_passes_expand_filter(by_id["workflow-082"], "finance-expense-audit")
    assert task_passes_expand_filter(by_id["workflow-070"], "finance-expense-audit")
    assert not task_passes_expand_filter(by_id["workflow-064"], "finance-expense-audit")
    assert not task_passes_expand_filter(by_id["workflow-079"], "finance-expense-audit")


def test_prune_pack_quick8_tasks():
    from skillos.skills.domain_pack import prune_pack_quick8_tasks

    pack = {
        "anchor_tasks": ["workflow-082", "workflow-083"],
        "quick8_tasks": ["workflow-082", "workflow-083", "workflow-064", "workflow-079"],
    }
    removed = prune_pack_quick8_tasks(pack, "finance-expense-audit")
    assert "workflow-064" in removed
    assert "workflow-079" in removed
    assert pack["quick8_tasks"] == ["workflow-082", "workflow-083"]


def test_repair_domain_pack_finance():
    from skillos.skills.domain_pack import load_domain_pack

    pack_before = load_domain_pack("finance-expense-audit")
    if not pack_before or "workflow-064" not in (pack_before.get("quick8_tasks") or []):
        return
    result = repair_domain_pack("finance-expense-audit")
    assert result.get("changed")
    assert "workflow-064" in result.get("removed", [])
    pack_after = load_domain_pack("finance-expense-audit")
    assert "workflow-064" not in (pack_after.get("quick8_tasks") or [])
    assert "处理客户退款" not in (pack_after.get("heritage_body") or "")
