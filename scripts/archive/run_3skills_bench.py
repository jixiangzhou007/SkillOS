"""Run SkillsBench task-suite compare for the 3 user-sim skills."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SKILLS = [
    ("电商退款", "电商客服退款处理"),
    ("CSV清洗", "运营级CSV清洗工坊"),
    ("PR审查", "GitHub PR"),
]

def main():
    from skillos.skills_bench import SKILLS_DIR, SkillBenchScore
    from skillos.skillsbench_tasks import compare_with_without

    out = {"timestamp": int(time.time()), "structural": [], "task_compare": []}
    for label, name in SKILLS:
        md = SKILLS_DIR / name / "SKILL.md"
        if not md.exists():
            print(f"MISSING: {name}")
            continue
        print(f"\n=== {label} ({name}) ===")
        sb = SkillBenchScore.from_skill(md)
        struct = {
            "label": label,
            "skill": name,
            "total": sb.total,
            "grade": sb.grade,
            "correctness": sb.correctness,
            "security": sb.security,
            "completeness": sb.completeness,
            "robustness": sb.robustness,
        }
        out["structural"].append(struct)
        print(f"  结构分: {sb.total}/100 [{sb.grade}] C={sb.correctness} S={sb.security} Cp={sb.completeness} R={sb.robustness}")

        print("  任务集对比中（按 category 路由）…")
        cmp = compare_with_without(str(md), routed=True)
        cmp["label"] = label
        out["task_compare"].append(cmp)
        cats = ", ".join(cmp.get("bench_categories") or [])
        print(f"  路由类别: {cats}")
        print(f"  域内({cmp.get('matched_tasks', '?')}题) 有技能: {cmp['with_skill_score']} [{cmp['with_skill_grade']}]")
        print(f"  域内 无技能: {cmp['without_skill_score']} [{cmp['without_skill_grade']}]")
        print(f"  域内提升: {cmp['delta']} ({cmp['improvement_pct']})")
        if cmp.get("routed"):
            print(f"  跨域 harm_score: {cmp.get('harm_score', 0)}")

    path = ROOT / "data" / "benchmarks" / f"user_sim_3skills_bench_{out['timestamp']}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {path}")

if __name__ == "__main__":
    main()
