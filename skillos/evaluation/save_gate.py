"""Post-extraction save gate — domain smoke eval before persisting skill."""


import logging
import os
from typing import Any

_log = logging.getLogger(__name__)

DOMAIN_SMOKE_MIN_WITH_SCORE = 80
REGRESSION_DELTA_PP = 5

# Preferred smoke tasks per domain template (official preset alignment).
DOMAIN_SMOKE_TASK_IDS: dict[str, tuple[str, ...]] = {
    "workflow-refund": ("workflow-064",),
    "code-review-pr": ("software-dependency-audit", "code-review-002"),
    "data-csv-clean": ("data-processing-036", "data-processing-037"),
}

# Skill name fallbacks when domain_template missing from meta.
SKILL_SMOKE_TASK_IDS: dict[str, tuple[str, ...]] = {
    "电商客服退款处理": ("workflow-064",),
    "GitHub Pull": ("software-dependency-audit", "code-review-002"),
    "CSV数据清洗助手": ("data-processing-036",),
}


def _gate_enabled() -> bool:
    return os.environ.get("SKILLOS_SKIP_SAVE_GATE", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )


def _resolve_smoke_task_ids(
    skill_name: str,
    *,
    domain_template: str | None = None,
) -> tuple[str, ...]:
    if domain_template and domain_template in DOMAIN_SMOKE_TASK_IDS:
        return DOMAIN_SMOKE_TASK_IDS[domain_template]
    try:
        from skillos.skills.domain_pack import get_smoke_task_ids

        pack_ids = get_smoke_task_ids(domain_template, skill_name)
        if pack_ids:
            return pack_ids
    except Exception:
        pass
    if skill_name in SKILL_SMOKE_TASK_IDS:
        return SKILL_SMOKE_TASK_IDS[skill_name]
    return ()


def _first_domain_task(skill_name: str, body: str, categories: list[str]):
    from skillos.benchmark_local import _select_quick8_tasks
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    tasks = _select_quick8_tasks(
        skill_name, body, categories, SKILLSBENCH_TASKS, domain_only=True,
    )
    return tasks[0] if tasks else None


def _task_by_id(task_id: str):
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    for task in SKILLSBENCH_TASKS:
        if task.task_id == task_id:
            return task
    return None


def _eval_task(
    task_id: str,
    body: str,
    *,
    skill_name: str = "",
    domain_template: str | None = None,
    bench_categories: list[str] | None = None,
) -> dict[str, Any] | None:
    from skillos.skillsbench_tasks import run_task_evaluation

    task = _task_by_id(task_id)
    if task is None:
        return None
    without = run_task_evaluation(task_id, skill_content="", model="")
    with_skill = run_task_evaluation(
        task_id,
        skill_content=body,
        model="",
        route_by_category=True,
        bench_categories=bench_categories,
        skill_name=skill_name,
        domain_template=domain_template,
    )
    return {
        "task_id": task_id,
        "category": task.category,
        "without_score": int(without.get("score") or 0),
        "with_score": int(with_skill.get("score") or 0),
        "max_score": int(with_skill.get("max_score") or 100),
        "passed": int(with_skill.get("score") or 0) >= DOMAIN_SMOKE_MIN_WITH_SCORE,
        "delta": int(with_skill.get("score") or 0) - int(without.get("score") or 0),
    }


def run_domain_smoke(
    skill_name: str,
    body: str,
    *,
    bench_categories: list[str] | None = None,
    domain_template: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any] | None:
    """Run one injectable domain task; return scores or None if no task."""
    from skillos.knowledge.skill_routing import infer_bench_categories

    categories = bench_categories or infer_bench_categories(skill_name, body)

    if task_id:
        row = _eval_task(
            task_id, body,
            skill_name=skill_name,
            domain_template=domain_template,
            bench_categories=bench_categories,
        )
        if row:
            return row

    preferred = _resolve_smoke_task_ids(skill_name, domain_template=domain_template)
    for tid in preferred:
        row = _eval_task(
            tid, body,
            skill_name=skill_name,
            domain_template=domain_template,
            bench_categories=bench_categories,
        )
        if row:
            return row

    task = _first_domain_task(skill_name, body, categories)
    if task is None:
        return None
    return _eval_task(
        task.task_id, body,
        skill_name=skill_name,
        domain_template=domain_template,
        bench_categories=bench_categories,
    )


def run_domain_smoke_suite(
    skill_name: str,
    body: str,
    *,
    bench_categories: list[str] | None = None,
    domain_template: str | None = None,
) -> list[dict[str, Any]]:
    """Run all preferred domain smoke tasks for this template/skill."""
    from skillos.knowledge.skill_routing import infer_bench_categories

    categories = bench_categories or infer_bench_categories(skill_name, body)
    preferred = _resolve_smoke_task_ids(skill_name, domain_template=domain_template)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tid in preferred:
        row = run_domain_smoke(
            skill_name, body,
            bench_categories=categories,
            domain_template=domain_template,
            task_id=tid,
        )
        if row and row["task_id"] not in seen:
            rows.append(row)
            seen.add(row["task_id"])
    if rows:
        return rows
    single = run_domain_smoke(
        skill_name, body,
        bench_categories=categories,
        domain_template=domain_template,
    )
    return [single] if single else []


def apply_save_gate(
    skill_name: str,
    body: str,
    *,
    old_body: str | None = None,
    bench_categories: list[str] | None = None,
    domain_template: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Domain smoke suite + regression guard; may re-merge heritage from old_body."""
    meta: dict[str, Any] = {"gate_enabled": _gate_enabled()}
    if not _gate_enabled():
        return body, meta

    suite = run_domain_smoke_suite(
        skill_name, body,
        bench_categories=bench_categories,
        domain_template=domain_template,
    )
    if not suite:
        meta["skipped"] = "no_domain_task"
        return body, meta

    meta["domain_smoke_suite"] = suite
    smoke = suite[0]
    meta["domain_smoke"] = smoke

    def _smoke(body_text: str) -> list[dict[str, Any]]:
        return run_domain_smoke_suite(
            skill_name, body_text,
            bench_categories=bench_categories,
            domain_template=domain_template,
        )

    primary_score = min(r["with_score"] for r in suite)

    if old_body and primary_score < DOMAIN_SMOKE_MIN_WITH_SCORE:
        old_suite = _smoke(old_body)
        old_primary = min((r["with_score"] for r in old_suite), default=0)
        if old_suite and old_primary >= primary_score + REGRESSION_DELTA_PP:
            try:
                from skillos.skills.skill_structure import merge_protected_sections

                repaired, merged = merge_protected_sections(
                    old_body, body, domain_template=domain_template,
                )
                meta["heritage_repair"] = merged
                suite2 = _smoke(repaired)
                if suite2:
                    meta["domain_smoke_after_repair"] = suite2
                    new_primary = min(r["with_score"] for r in suite2)
                    if new_primary > primary_score:
                        body = repaired
                        meta["domain_smoke_suite"] = suite2
                        meta["domain_smoke"] = suite2[0]
                        primary_score = new_primary
            except Exception as exc:
                _log.debug("Save gate heritage repair skipped: %s", exc)

    if primary_score < DOMAIN_SMOKE_MIN_WITH_SCORE:
        meta["warning"] = (
            f"域内烟测未达 {DOMAIN_SMOKE_MIN_WITH_SCORE} 分"
            f"（tasks={[r['task_id'] for r in meta.get('domain_smoke_suite', suite)]}"
            f" min_score={primary_score}）"
        )

    return body, meta
