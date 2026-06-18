import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from skillos.skillsbench_tasks import run_skillsbench_suite

content = Path("skills/GitHub PR/SKILL.md").read_text(encoding="utf-8")
for label, skill in [("with_skill", content), ("without_skill", "")]:
    r = run_skillsbench_suite(skill_content=skill)
    print(f"=== {label} {r['total_score']}/{r['max_score']} [{r['grade']}] ===")
    for t in r["results"]:
        if "score" in t:
            print(f"  {t['task_id']:28s} {t['score']:3d}/{t['max_score']} [{t['grade']}]")
        else:
            print(f"  {t['task_id']:28s} ERR")
