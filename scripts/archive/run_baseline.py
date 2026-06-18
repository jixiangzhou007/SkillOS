import sys, os
os.chdir(r"D:\SkillOS")
sys.path.insert(0, r"D:\SkillOS")
import skillos.skillsbench_tasks as s
import json
r = s.run_skillsbench_suite()
json.dump(r, open(r"D:\SkillOS\data\benchmarks\baseline_88.json", "w", encoding="utf-8"), ensure_ascii=False)
print("Saved:", r["total_score"], "/", r["max_score"], "[", r["grade"], "]")
