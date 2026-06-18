"""Ablation factorial helpers."""


from skillos.evaluation.ablation import (
    ABLATION_CONDITIONS,
    _marginal_effects,
    prepare_skill_content,
)
from skillos.knowledge.skill_routing import resolve_skill_injection
from skillos.skills.skill_structure import strip_heritage_sections


def test_strip_heritage_sections():
    body = "## S_body\nsteps\n\n## 应答速查（单条回复、可执行）\n- rule\n\n## S_route\nr\n"
    out = strip_heritage_sections(body)
    assert "应答速查" not in out
    assert "S_body" in out
    assert "S_route" in out


def test_prepare_skill_content_no_heritage():
    raw = {
        "meta": {"name": "t", "bench_categories": ["workflow"]},
        "body": "## S_body\nx\n\n## 应答速查\n- y\n",
    }
    md = prepare_skill_content(raw, heritage=False)
    assert "应答速查" not in md
    assert "S_body" in md


def test_marginal_effects_2x2():
    rows = [
        {"condition": "full", "domain_delta": 40},
        {"condition": "no_heritage", "domain_delta": 10},
        {"condition": "no_pack_scope", "domain_delta": 25},
        {"condition": "baseline", "domain_delta": 5},
    ]
    m = _marginal_effects(rows)
    assert m["heritage_marginal"] == 30
    assert m["pack_marginal"] == 15
    assert m["interaction"] == 10


def test_pack_scoped_inject_flag():
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
    content = (
        "---\nname: 财务报销审计助手\ndomain_template: finance-expense-audit\n"
        "bench_categories:\n  - workflow\n---\n\n"
        "## S_body\n差旅报销审计 超标 酒店400 发票 税号\n"
    )
    inject_anchor, _ = resolve_skill_injection(
        "workflow", content, ["workflow"], skill_name="财务报销审计助手",
        task=by_id["workflow-082"], domain_template="finance-expense-audit",
        pack_scoped_inject=True,
    )
    inject_cross, _ = resolve_skill_injection(
        "workflow", content, ["workflow"], skill_name="财务报销审计助手",
        task=by_id["workflow-064"], domain_template="finance-expense-audit",
        pack_scoped_inject=True,
    )
    assert inject_anchor is True
    assert inject_cross is False


def test_ablation_has_four_conditions():
    assert len(ABLATION_CONDITIONS) == 4
    ids = {c["id"] for c in ABLATION_CONDITIONS}
    assert ids == {"full", "no_heritage", "no_pack_scope", "baseline"}
