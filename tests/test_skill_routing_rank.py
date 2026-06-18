"""Task ranking for category-aware quick8 benchmarks."""

from skillos.knowledge.skill_routing import rank_bench_tasks_for_skill
from skillos.skillsbench_tasks import SKILLSBENCH_TASKS


def test_refund_skill_prefers_workflow_tasks():
    from skillos.skills_bench import SKILLS_DIR

    md = SKILLS_DIR / "电商客服退款处理" / "SKILL.md"
    if not md.exists():
        return
    content = md.read_text(encoding="utf-8")
    picked = rank_bench_tasks_for_skill(
        "电商客服退款处理", content, SKILLSBENCH_TASKS, limit=8,
    )
    ids = [t.task_id for t in picked]
    assert "workflow-064" in ids, ids
    assert ids[0] == "workflow-064"
    assert all(t.category == "workflow" for t in picked)
