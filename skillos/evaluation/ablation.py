"""Ablation study — HERITAGE × pack-scoped inject (2×2 factorial)."""


import time
from dataclasses import dataclass
from typing import Any

from skillos.skills.bench_cohorts import GENERALIZE_SKILLS, REFERENCE_SKILL_NAMES

ABLATION_CONDITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "full",
        "label": "HERITAGE+pack",
        "heritage": True,
        "pack_scoped_inject": True,
    },
    {
        "id": "no_heritage",
        "label": "−HERITAGE",
        "heritage": False,
        "pack_scoped_inject": True,
    },
    {
        "id": "no_pack_scope",
        "label": "−pack",
        "heritage": True,
        "pack_scoped_inject": False,
    },
    {
        "id": "baseline",
        "label": "−HERITAGE−pack",
        "heritage": False,
        "pack_scoped_inject": False,
    },
)

DEFAULT_COHORT = GENERALIZE_SKILLS


@dataclass(frozen=True)
class AblationSpec:
    skill_name: str
    domain_template: str | None
    bench_categories: tuple[str, ...]
    anchor_tasks: tuple[str, ...]


def _cohort_specs(extra_reference: bool = True) -> list[AblationSpec]:
    specs: list[AblationSpec] = [
        AblationSpec(
            skill_name=s["name"],
            domain_template=s.get("domain_template"),
            bench_categories=tuple(s.get("bench_categories") or ()),
            anchor_tasks=tuple(s.get("anchor_tasks") or ()),
        )
        for s in DEFAULT_COHORT
    ]
    if extra_reference:
        specs.append(
            AblationSpec(
                skill_name="电商客服退款处理",
                domain_template="workflow-refund",
                bench_categories=("workflow", "documentation"),
                anchor_tasks=("workflow-064",),
            )
        )
    return specs


def prepare_skill_content(
    raw: dict[str, Any],
    *,
    heritage: bool,
) -> str:
    from skillos.skills.skill_structure import compose_skill_markdown, strip_heritage_sections

    body = raw.get("body") or ""
    meta = dict(raw.get("meta") or {})
    if not heritage:
        body = strip_heritage_sections(body)
    return compose_skill_markdown(meta, body)


def select_ablation_tasks(
    skill_name: str,
    content: str,
    categories: list[str],
    *,
    domain_template: str | None,
    domain_only: bool = True,
) -> list[Any]:
    from skillos.benchmark_local import _select_quick8_tasks
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    return _select_quick8_tasks(
        skill_name,
        content,
        categories,
        SKILLSBENCH_TASKS,
        domain_only=domain_only,
        domain_template=domain_template,
    )


def eval_ablation_condition(
    spec: AblationSpec,
    condition: dict[str, Any],
    *,
    domain_only: bool = True,
) -> dict[str, Any]:
    from skillos.skills.skill_store import load_skill_raw
    from skillos.skillsbench_tasks import run_task_evaluation

    raw = load_skill_raw(spec.skill_name)
    content = prepare_skill_content(raw, heritage=bool(condition["heritage"]))
    categories = list(spec.bench_categories or raw.get("meta", {}).get("bench_categories") or [])
    tasks = select_ablation_tasks(
        spec.skill_name,
        content,
        categories,
        domain_template=spec.domain_template,
        domain_only=domain_only,
    )
    if not tasks:
        return {
            "skill": spec.skill_name,
            "condition": condition["id"],
            "error": "no_tasks",
        }

    per_task: list[dict[str, Any]] = []
    injected = 0
    total_delta = 0

    for task in tasks:
        wo = run_task_evaluation(task.task_id, skill_content="", model="")
        w = run_task_evaluation(
            task.task_id,
            skill_content=content,
            model="",
            route_by_category=True,
            bench_categories=categories,
            skill_name=spec.skill_name,
            domain_template=spec.domain_template,
            pack_scoped_inject=bool(condition["pack_scoped_inject"]),
        )
        delta = int(w.get("score") or 0) - int(wo.get("score") or 0)
        if w.get("skill_used"):
            injected += 1
        total_delta += delta
        per_task.append({
            "task_id": task.task_id,
            "description": task.description,
            "with_score": w.get("score"),
            "without_score": wo.get("score"),
            "delta": delta,
            "skill_used": w.get("skill_used"),
        })

    anchor_ids = set(spec.anchor_tasks)
    anchor_rows = [r for r in per_task if r["task_id"] in anchor_ids]
    anchor_delta = sum(int(r["delta"]) for r in anchor_rows)
    anchor_inject = sum(1 for r in anchor_rows if r.get("skill_used"))

    return {
        "skill": spec.skill_name,
        "domain_template": spec.domain_template,
        "condition": condition["id"],
        "condition_label": condition["label"],
        "heritage": condition["heritage"],
        "pack_scoped_inject": condition["pack_scoped_inject"],
        "tasks": len(tasks),
        "task_ids": [t.task_id for t in tasks],
        "skills_injected": injected,
        "inject_rate": round(injected / len(tasks), 3),
        "domain_delta": total_delta,
        "domain_improvement_pct": f"{total_delta / max(1, sum(int(r['without_score'] or 0) for r in per_task)) * 100:+.1f}%",
        "anchor_delta": anchor_delta,
        "anchor_inject_rate": round(anchor_inject / max(1, len(anchor_rows)), 3),
        "per_task": per_task,
    }


def _marginal_effects(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """2×2 factorial marginals for one skill."""
    by_id = {r["condition"]: r for r in rows if not r.get("error")}
    if len(by_id) < 4:
        return {}
    full = by_id["full"]["domain_delta"]
    nh = by_id["no_heritage"]["domain_delta"]
    np_ = by_id["no_pack_scope"]["domain_delta"]
    base = by_id["baseline"]["domain_delta"]
    return {
        "heritage_marginal": full - nh,
        "pack_marginal": full - np_,
        "interaction": full - nh - np_ + base,
        "full": full,
        "no_heritage": nh,
        "no_pack_scope": np_,
        "baseline": base,
    }


def run_ablation_study(
    *,
    include_reference: bool = True,
    domain_only: bool = True,
) -> dict[str, Any]:
    ts = int(time.time())
    specs = _cohort_specs(extra_reference=include_reference)
    results: list[dict[str, Any]] = []
    by_skill: dict[str, list[dict[str, Any]]] = {}

    for spec in specs:
        skill_rows: list[dict[str, Any]] = []
        for cond in ABLATION_CONDITIONS:
            row = eval_ablation_condition(spec, cond, domain_only=domain_only)
            results.append(row)
            skill_rows.append(row)
        by_skill[spec.skill_name] = skill_rows

    skill_summaries: list[dict[str, Any]] = []
    for name, rows in by_skill.items():
        marginals = _marginal_effects(rows)
        valid = [r for r in rows if not r.get("error")]
        skill_summaries.append({
            "skill": name,
            "domain_template": valid[0].get("domain_template") if valid else None,
            "marginals": marginals,
            "conditions": {
                r["condition"]: {
                    "domain_delta": r.get("domain_delta"),
                    "inject_rate": r.get("inject_rate"),
                    "anchor_delta": r.get("anchor_delta"),
                }
                for r in valid
            },
        })

    gen_rows = [r for r in results if r.get("skill") not in REFERENCE_SKILL_NAMES and not r.get("error")]
    ref_rows = [r for r in results if r.get("skill") in REFERENCE_SKILL_NAMES and not r.get("error")]

    def _median_delta(rows: list[dict], cond: str) -> float | None:
        vals = [float(r["domain_delta"]) for r in rows if r.get("condition") == cond]
        if not vals:
            return None
        vals.sort()
        return vals[len(vals) // 2]

    cohort_summary = {
        "generalize_median_by_condition": {
            c["id"]: _median_delta(gen_rows, c["id"]) for c in ABLATION_CONDITIONS
        },
        "reference_by_condition": {
            c["id"]: next(
                (r.get("domain_delta") for r in ref_rows if r.get("condition") == c["id"]),
                None,
            )
            for c in ABLATION_CONDITIONS
        },
    }

    gen_marginals = [_marginal_effects(by_skill[s.skill_name]) for s in specs if s.skill_name not in REFERENCE_SKILL_NAMES]
    gen_marginals = [m for m in gen_marginals if m]
    if gen_marginals:
        cohort_summary["generalize_mean_marginals"] = {
            "heritage_marginal": round(sum(m["heritage_marginal"] for m in gen_marginals) / len(gen_marginals), 1),
            "pack_marginal": round(sum(m["pack_marginal"] for m in gen_marginals) / len(gen_marginals), 1),
            "interaction": round(sum(m["interaction"] for m in gen_marginals) / len(gen_marginals), 1),
        }

    return {
        "timestamp": ts,
        "experiment": "ablation_heritage_x_pack_scope",
        "design": "2x2 factorial: HERITAGE on/off × pack-scoped inject on/off",
        "conditions": list(ABLATION_CONDITIONS),
        "domain_only": domain_only,
        "results": results,
        "skill_summaries": skill_summaries,
        "cohort_summary": cohort_summary,
    }
