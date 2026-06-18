"""Quick 8-task SkillsBench compare for the 3 user-sim extracted skills."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SKILLS = [
    ("电商退款", "电商客服退款处理"),
    ("PR审查", "GitHub Pull"),
    ("CSV清洗", "CSV数据清洗助手"),
]


def main() -> None:
    from skillos.benchmark_local import run_quick8_for_skill
    from skillos.skills_bench import SKILLS_DIR

    out = {"timestamp": int(time.time()), "mode": "quick8", "structural": [], "task_compare": []}

    for label, name in SKILLS:
        md = SKILLS_DIR / name / "SKILL.md"
        if not md.exists():
            print(f"MISSING: {name}")
            continue
        print(f"\n=== {label} ({name}) ===")
        cmp = run_quick8_for_skill(name, skills_dir=SKILLS_DIR)
        cmp["label"] = label
        out["structural"].append(cmp["structural"])
        out["task_compare"].append({k: v for k, v in cmp.items() if k != "structural"})
        print(f"  结构分: {cmp['structural']['total']}/100 [{cmp['structural']['grade']}]")
        print(f"  路由类别: {', '.join(cmp['bench_categories'])}")
        print(f"  题目: {', '.join(cmp['task_ids'])}")
        print(f"  注入: {cmp['skills_injected']}/{cmp['tasks']} 题")
        print(f"  有技能: {cmp['with_skill_score']}/{cmp['max_score']} [{cmp['with_skill_grade']}]")
        print(f"  无技能: {cmp['without_skill_score']} [{cmp['without_skill_grade']}]")
        print(f"  提升: {cmp['delta']} ({cmp['improvement_pct']})")

    path = ROOT / "data" / "benchmarks" / f"new3skills_quick8_{out['timestamp']}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
