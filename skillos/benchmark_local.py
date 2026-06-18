"""Local SkillsBench quick8 / workflow benchmark lookups and runner."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

BENCHMARKS_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmarks"
MAX_QUICK8_TASKS = 8

_QUICK8_PATTERNS = (
    "new3skills_quick8_*.json",
    "refund_workflow_quick8_*.json",
    "skill_quick8_*.json",
    "skill_domain_quick8_*.json",
    "local_compare_*.json",
)

_REGRESSION_PATTERN = "bench_regression_*.json"
_POST_EXTRACT_PATTERN = "post_extract_regression_*.json"

REFERENCE_QUICK8_SKILLS = (
    "CSV数据清洗助手",
    "GitHub Pull",
    "电商客服退款处理",
)


def _skill_file_slug(name: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", name.strip())
    return slug[:48] or "skill"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _task_compare_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    tc = data.get("task_compare")
    if isinstance(tc, list):
        return tc
    if isinstance(tc, dict):
        return [tc]
    return []


def latest_quick8_for_skill(skill_name: str) -> dict[str, Any] | None:
    """Most recent quick8 task_compare row for this skill."""
    best: dict[str, Any] | None = None
    best_ts = -1
    for pat in _QUICK8_PATTERNS:
        for f in sorted(BENCHMARKS_DIR.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True):
            data = _load_json(f)
            if not data:
                continue
            ts = int(data.get("timestamp") or 0)
            for row in _task_compare_rows(data):
                if row.get("skill") != skill_name:
                    continue
                if ts >= best_ts:
                    best_ts = ts
                    best = {
                        **row,
                        "file": f.name,
                        "timestamp": ts,
                        "mode": data.get("mode", "quick8"),
                    }
    return best


def latest_structural_for_skill(skill_name: str) -> dict[str, Any] | None:
    """Structural score from the latest quick8 bundle containing this skill."""
    for pat in _QUICK8_PATTERNS:
        for f in sorted(BENCHMARKS_DIR.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True):
            data = _load_json(f)
            if not data:
                continue
            structural = data.get("structural")
            if isinstance(structural, dict) and structural.get("skill") == skill_name:
                return {**structural, "file": f.name, "timestamp": data.get("timestamp")}
            if isinstance(structural, list):
                for row in structural:
                    if row.get("skill") == skill_name:
                        return {**row, "file": f.name, "timestamp": data.get("timestamp")}
    return None


def quick8_history_for_skill(skill_name: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Recent quick8 runs for a skill, newest first."""
    rows: list[dict[str, Any]] = []
    for pat in _QUICK8_PATTERNS:
        for f in sorted(BENCHMARKS_DIR.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True):
            data = _load_json(f)
            if not data:
                continue
            ts = int(data.get("timestamp") or 0)
            for row in _task_compare_rows(data):
                if row.get("skill") != skill_name:
                    continue
                rows.append({
                    "timestamp": ts,
                    "file": f.name,
                    "improvement_pct": row.get("improvement_pct"),
                    "domain_improvement_pct": row.get("domain_improvement_pct"),
                    "with_skill_score": row.get("with_skill_score"),
                    "without_skill_score": row.get("without_skill_score"),
                    "skills_injected": row.get("skills_injected"),
                    "harm_tasks": row.get("harm_tasks") or [],
                    "tasks": row.get("tasks"),
                    "mode": data.get("mode", "quick8"),
                })
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    deduped: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        if row["timestamp"] in seen:
            continue
        seen.add(row["timestamp"])
        deduped.append(row)
        if len(deduped) >= limit:
            break
    return deduped


def local_bench_summary(skill_name: str) -> dict[str, Any]:
    """Local quick8 + structural summary for API/frontend."""
    return {
        "skill": skill_name,
        "latest_quick8": latest_quick8_for_skill(skill_name),
        "quick8_history": quick8_history_for_skill(skill_name),
        "structural": latest_structural_for_skill(skill_name),
    }


def latest_bench_regression() -> dict[str, Any] | None:
    """Most recent bench_regression_*.json from scripts/run_bench_regression.py."""
    files = sorted(
        BENCHMARKS_DIR.glob(_REGRESSION_PATTERN),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None
    data = _load_json(files[0])
    if not data:
        return None
    return {**data, "file": files[0].name}


def latest_post_extract_regression() -> dict[str, Any] | None:
    """Most recent post_extract_regression_*.json after reference-skill save."""
    files = sorted(
        BENCHMARKS_DIR.glob(_POST_EXTRACT_PATTERN),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None
    data = _load_json(files[0])
    if not data:
        return None
    return {**data, "file": files[0].name}


def reference_bench_dashboard() -> dict[str, Any]:
    """Overview of reference + generalize skills for bench dashboard."""
    skills: list[dict[str, Any]] = []
    for name in REFERENCE_QUICK8_SKILLS:
        q8 = latest_quick8_for_skill(name)
        structural = latest_structural_for_skill(name)
        row: dict[str, Any] = {
            "skill": name,
            "cohort": "reference",
            "structural_grade": structural.get("grade") if structural else None,
            "structural_total": structural.get("total") if structural else None,
        }
        if q8:
            row.update({
                "improvement_pct": q8.get("improvement_pct"),
                "domain_improvement_pct": q8.get("domain_improvement_pct"),
                "skills_injected": q8.get("skills_injected"),
                "tasks": q8.get("tasks"),
                "harm_tasks": q8.get("harm_tasks") or [],
                "with_skill_score": q8.get("with_skill_score"),
                "without_skill_score": q8.get("without_skill_score"),
                "file": q8.get("file"),
                "timestamp": q8.get("timestamp"),
            })
        skills.append(row)

    generalize = generalize_bench_dashboard()
    reg = latest_bench_regression()
    generalize_regression = (reg or {}).get("generalize_domain_quick8") or []

    latest_ci = None
    ci_files = sorted(BENCHMARKS_DIR.glob("quick8_ci_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if ci_files:
        latest_ci = _load_json(ci_files[0])

    return {
        "reference_skills": skills,
        "generalize_skills": generalize,
        "latest_quick8_ci": latest_ci,
        "latest_regression": reg,
        "latest_post_extract": latest_post_extract_regression(),
        "generalize_regression": generalize_regression,
        "official": latest_official_results_stub(),
    }


def generalize_bench_dashboard() -> list[dict[str, Any]]:
    """Per-skill latest domain quick8 for generalization cohort."""
    from skillos.skills.bench_cohorts import GENERALIZE_SKILLS

    rows: list[dict[str, Any]] = []
    for spec in GENERALIZE_SKILLS:
        name = spec["name"]
        q8 = latest_domain_quick8_for_skill(name) or latest_quick8_for_skill(name)
        structural = latest_structural_for_skill(name)
        row: dict[str, Any] = {
            "skill": name,
            "cohort": "generalize",
            "domain_template": spec.get("domain_template"),
            "anchor_tasks": list(spec.get("anchor_tasks") or ()),
            "min_domain_delta": spec.get("min_domain_delta"),
            "structural_grade": structural.get("grade") if structural else None,
            "structural_total": structural.get("total") if structural else None,
        }
        if q8:
            row.update({
                "domain_improvement_pct": q8.get("domain_improvement_pct"),
                "domain_delta": q8.get("domain_delta"),
                "improvement_pct": q8.get("improvement_pct"),
                "skills_injected": q8.get("skills_injected"),
                "tasks": q8.get("tasks"),
                "task_ids": q8.get("task_ids"),
                "harm_tasks": q8.get("harm_tasks") or [],
                "with_skill_score": q8.get("with_skill_score"),
                "without_skill_score": q8.get("without_skill_score"),
                "file": q8.get("file"),
                "timestamp": q8.get("timestamp"),
            })
        rows.append(row)
    return rows


def latest_domain_quick8_for_skill(skill_name: str) -> dict[str, Any] | None:
    """Most recent skill_domain_quick8 snapshot for a skill."""
    pattern = f"skill_domain_quick8_{skill_name}_*.json"
    files = sorted(
        BENCHMARKS_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None
    data = _load_json(files[0])
    if not data:
        return None
    return {**data, "file": files[0].name}


def latest_official_results_stub() -> dict[str, Any]:
    try:
        from skillos.official_skillsbench.service import latest_official_results
        return latest_official_results(limit=2)
    except Exception:
        return {"eval": [], "compare": [], "smoke": []}


def _select_quick8_tasks(
    label: str,
    content: str,
    categories: list[str],
    all_tasks: list[Any],
    *,
    domain_only: bool,
    domain_template: str | None = None,
) -> list[Any]:
    from skillos.knowledge.skill_routing import primary_bench_category, rank_bench_tasks_for_skill, resolve_skill_injection
    from skillos.skills.domain_pack import get_pack_task_ids

    pack_ids = get_pack_task_ids(domain_template)
    by_id = {t.task_id: t for t in all_tasks}
    pack_tasks = [by_id[tid] for tid in pack_ids if tid in by_id]

    ranked = rank_bench_tasks_for_skill(
        label, content, all_tasks, bench_categories=categories, limit=MAX_QUICK8_TASKS * 3,
    )
    if pack_tasks:
        if domain_only:
            return pack_tasks[:MAX_QUICK8_TASKS]
        rest = [t for t in ranked if t.task_id not in pack_ids]
        return (pack_tasks + rest)[:MAX_QUICK8_TASKS]

    if not domain_only:
        return ranked[:MAX_QUICK8_TASKS]

    injectable: list[Any] = []
    for task in ranked:
        inject, _ = resolve_skill_injection(
            task.category, content, categories, skill_name=label, task=task,
            domain_template=domain_template,
        )
        if inject:
            injectable.append(task)
        if len(injectable) >= MAX_QUICK8_TASKS:
            break

    if injectable:
        return injectable

    primary = primary_bench_category(label, content)
    for task in all_tasks:
        if primary and task.category != primary:
            continue
        inject, _ = resolve_skill_injection(
            task.category, content, categories, skill_name=label, task=task,
            domain_template=domain_template,
        )
        if inject and task not in injectable:
            injectable.append(task)
        if len(injectable) >= MAX_QUICK8_TASKS:
            break
    return injectable


def _domain_metrics(per_task: list[dict[str, Any]]) -> dict[str, Any]:
    injected = [p for p in per_task if p.get("skill_used")]
    if not injected:
        return {"domain_improvement_pct": "+0.0%", "harm_tasks": [], "domain_delta": 0}
    d_with = sum(int(p.get("with_score") or 0) for p in injected)
    d_without = sum(int(p.get("without_score") or 0) for p in injected)
    d_delta = d_with - d_without
    return {
        "domain_with_score": d_with,
        "domain_without_score": d_without,
        "domain_max_score": len(injected) * 100,
        "domain_delta": d_delta,
        "domain_improvement_pct": f"{d_delta / max(1, d_without) * 100:+.1f}%",
        "harm_tasks": [
            p["task_id"] for p in injected
            if int(p.get("with_score") or 0) < int(p.get("without_score") or 0)
        ],
    }


def run_quick8_for_skill(
    skill_name: str,
    *,
    skills_dir: Path | None = None,
    domain_only: bool = False,
) -> dict[str, Any]:
    """Run routed quick8 for one skill; persist JSON and return summary."""
    from skillos.knowledge.skill_routing import load_skill_routing_info
    from skillos.skills_bench import SkillBenchScore
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, _aggregate_results, run_task_evaluation

    root = skills_dir or Path(__file__).resolve().parents[1] / "skills"
    md = root / skill_name / "SKILL.md"
    if not md.exists():
        raise FileNotFoundError(skill_name)

    info = load_skill_routing_info(str(md))
    content = info["content"]
    categories = info["bench_categories"]
    label = info["name"]
    domain_template = info.get("meta", {}).get("domain_template") or info.get("meta", {}).get("domain_template_id")

    matched_tasks = _select_quick8_tasks(
        label, content, categories, SKILLSBENCH_TASKS,
        domain_only=domain_only,
        domain_template=domain_template,
    )
    if not matched_tasks:
        raise ValueError(f"No injectable domain tasks for skill: {skill_name}")

    matched_with: list[dict] = []
    matched_without: list[dict] = []
    task_ids: list[str] = []
    injected_count = 0

    for task in matched_tasks:
        task_ids.append(task.task_id)
        r_without = run_task_evaluation(task.task_id, skill_content="", model="")
        r_with = run_task_evaluation(
            task.task_id,
            skill_content=content,
            model="",
            route_by_category=True,
            bench_categories=categories,
            skill_name=label,
            domain_template=domain_template,
        )
        if r_with.get("skill_used"):
            injected_count += 1
        matched_without.append(r_without)
        matched_with.append(r_with)

    mw = _aggregate_results(matched_with)
    mwo = _aggregate_results(matched_without)
    delta = mw["total_score"] - mwo["total_score"]
    sb = SkillBenchScore.from_skill(md)

    per_task = [
        {
            "task_id": w.get("task_id"),
            "with_score": w.get("score"),
            "without_score": wo.get("score"),
            "skill_used": w.get("skill_used"),
        }
        for w, wo in zip(matched_with, matched_without)
    ]

    compare = {
        "skill": label,
        "skill_path": str(md),
        "bench_categories": categories,
        "routed": True,
        "quick8": True,
        "domain_only": domain_only,
        "task_ids": task_ids,
        "with_skill_score": mw["total_score"],
        "with_skill_grade": mw["grade"],
        "without_skill_score": mwo["total_score"],
        "without_skill_grade": mwo["grade"],
        "delta": delta,
        "improvement_pct": f"{delta / max(1, mwo['total_score']) * 100:+.1f}%",
        "tasks": mw["tasks_run"],
        "max_score": mw["max_score"],
        "skills_injected": injected_count,
        "per_task": per_task,
    }
    compare.update(_domain_metrics(per_task))

    payload = {
        "timestamp": int(time.time()),
        "mode": "skill_domain_quick8" if domain_only else "skill_quick8",
        "skill": label,
        "structural": {
            "skill": label,
            "total": sb.total,
            "grade": sb.grade,
            "correctness": sb.correctness,
            "security": sb.security,
            "completeness": sb.completeness,
            "robustness": sb.robustness,
        },
        "task_compare": compare,
    }

    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = "skill_domain_quick8" if domain_only else "skill_quick8"
    out_path = BENCHMARKS_DIR / f"{prefix}_{_skill_file_slug(label)}_{payload['timestamp']}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        **compare,
        "file": out_path.name,
        "timestamp": payload["timestamp"],
        "structural": payload["structural"],
        "saved_to": str(out_path),
    }