"""Task-level skill injection gating."""

from skillos.knowledge.skill_routing import (
    _skill_signal_terms,
    _task_domain_overlap,
    resolve_skill_injection,
    task_skill_overlap_threshold,
)
from skillos.skillsbench_tasks import SKILLSBENCH_TASKS


def test_refund_skill_not_injected_for_contract_task():
    task = next(t for t in SKILLSBENCH_TASKS if t.task_id == "workflow-080")
    md_path = __import__("pathlib").Path("skills/电商客服退款处理/SKILL.md")
    if not md_path.exists():
        return
    content = md_path.read_text(encoding="utf-8")
    inject, _ = resolve_skill_injection(
        task.category, content, ["workflow", "documentation"],
        skill_name="电商客服退款处理", task=task,
    )
    assert inject is False


def test_refund_skill_injected_for_refund_task():
    task = next(t for t in SKILLSBENCH_TASKS if t.task_id == "workflow-064")
    md_path = __import__("pathlib").Path("skills/电商客服退款处理/SKILL.md")
    if not md_path.exists():
        return
    content = md_path.read_text(encoding="utf-8")
    terms = _skill_signal_terms("电商客服退款处理", content)
    assert _task_domain_overlap(terms, task) >= task_skill_overlap_threshold()
    inject, body = resolve_skill_injection(
        task.category, content, ["workflow", "documentation"],
        skill_name="电商客服退款处理", task=task,
    )
    assert inject is True
    assert body


def test_pr_skill_injected_for_pickle_task():
    task = next(t for t in SKILLSBENCH_TASKS if t.task_id == "code-review-011")
    md_path = __import__("pathlib").Path("skills/GitHub Pull/SKILL.md")
    if not md_path.exists():
        return
    content = md_path.read_text(encoding="utf-8")
    terms = _skill_signal_terms("GitHub Pull", content)
    assert _task_domain_overlap(terms, task) >= task_skill_overlap_threshold()
    inject, body = resolve_skill_injection(
        task.category, content, ["code-review"], skill_name="GitHub Pull", task=task,
    )
    assert inject is True
    assert body


def test_pr_skill_injected_for_infinite_loop_task():
    task = next(t for t in SKILLSBENCH_TASKS if t.task_id == "code-review-009")
    md_path = __import__("pathlib").Path("skills/GitHub Pull/SKILL.md")
    if not md_path.exists():
        return
    content = md_path.read_text(encoding="utf-8")
    inject, _ = resolve_skill_injection(
        task.category, content, ["code-review"], skill_name="GitHub Pull", task=task,
    )
    assert inject is True
