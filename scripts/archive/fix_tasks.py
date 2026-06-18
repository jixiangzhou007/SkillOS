"""Fix skillsbench_tasks.py: ensure grader code is OUTSIDE the task list."""
from pathlib import Path
import os
os.chdir(Path(__file__).parent.parent)
with open("skillos/skillsbench_tasks.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find grader (first function def after tasks)
grader_line = None
close_line = None
for i, l in enumerate(lines):
    if l.startswith("def _grade(score:") or l.startswith("def _grade("):
        grader_line = i
        break

if grader_line is None:
    print("ERROR: grader not found")
    exit(1)

# Find last ] before grader
for j in range(grader_line - 1, 0, -1):
    if lines[j].strip() == "]":
        close_line = j
        break

print(f"Grader at line {grader_line+1}, list closes at line {close_line+1}")

# Keep lines 0..close_line (task list with closing ]), then grader from grader_line onwards
fixed = lines[:close_line+1] + ["\n"] + lines[grader_line:]

with open("skillos/skillsbench_tasks.py", "w", encoding="utf-8") as f:
    f.writelines(fixed)

# Verify
task_count = sum(1 for l in fixed[:close_line+1] if "SkillBenchTask(" in l)
print(f"Fixed: {task_count} tasks, grader at line {close_line+3}")
