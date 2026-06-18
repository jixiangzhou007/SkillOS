"""Workflow-only quick 8-task compare for 电商客服退款处理."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SKILL_NAME = "电商客服退款处理"


def main() -> None:
    from skillos.skills_bench import SKILLS_DIR, SkillBenchScore
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, _aggregate_results, run_task_evaluation

    md = SKILLS_DIR / SKILL_NAME / "SKILL.md"
    content = md.read_text(encoding="utf-8")
    task_ids = [t.task_id for t in SKILLSBENCH_TASKS if t.category == "workflow"][:8]

    print(f"技能: {SKILL_NAME}")
    print(f"workflow 8题: {task_ids}")

    matched_with: list[dict] = []
    matched_without: list[dict] = []
    for tid in task_ids:
        matched_without.append(run_task_evaluation(tid, skill_content=""))
        matched_with.append(run_task_evaluation(tid, skill_content=content))

    agg_w = _aggregate_results(matched_with)
    agg_wo = _aggregate_results(matched_without)
    delta = agg_w["total_score"] - agg_wo["total_score"]
    sb = SkillBenchScore.from_skill(md)

    result = {
        "timestamp": int(time.time()),
        "mode": "workflow_quick8",
        "label": "电商退款",
        "skill": SKILL_NAME,
        "bench_categories": ["workflow"],
        "structural": {
            "total": sb.total,
            "grade": sb.grade,
            "correctness": sb.correctness,
            "security": sb.security,
            "completeness": sb.completeness,
            "robustness": sb.robustness,
        },
        "task_ids": task_ids,
        "with_skill_score": agg_w["total_score"],
        "with_skill_grade": agg_w["grade"],
        "without_skill_score": agg_wo["total_score"],
        "without_skill_grade": agg_wo["grade"],
        "max_score": agg_w["max_score"],
        "delta": delta,
        "improvement_pct": f"{delta / max(1, agg_wo['total_score']) * 100:+.1f}%",
        "tasks": agg_w["tasks_run"],
    }

    out = ROOT / "data" / "benchmarks" / f"refund_workflow_quick8_{result['timestamp']}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"结构分: {sb.total}/100 [{sb.grade}]")
    print(f"有技能: {result['with_skill_score']}/{result['max_score']} [{result['with_skill_grade']}]")
    print(f"无技能: {result['without_skill_score']} [{result['without_skill_grade']}]")
    print(f"提升: {result['delta']} ({result['improvement_pct']})")
    print(f"Saved: {out}")

    # Refund-specific single task
    r_without = run_task_evaluation("workflow-064", skill_content="")
    r_with = run_task_evaluation("workflow-064", skill_content=content)
    d = r_with["score"] - r_without["score"]
    print(f"\n--- 单题 workflow-064 处理客户退款 ---")
    print(f"无技能: {r_without['score']}/{r_without['max_score']} [{r_without['grade']}]")
    print(f"有技能: {r_with['score']}/{r_with['max_score']} [{r_with['grade']}]")
    print(f"提升: {d:+d}")


if __name__ == "__main__":
    main()
