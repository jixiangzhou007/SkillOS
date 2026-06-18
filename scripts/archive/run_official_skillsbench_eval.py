"""Phase 1: official SkillsBench eval — oracle smoke + optional SkillOS skill export/compare."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.official_skillsbench.export import export_skill_for_official
from skillos.official_skillsbench.tasks import SMOKE_TASK, suggest_tasks_for_skill
from skillos.official_skillsbench.runner import (
    ensure_task as _ensure_task,
    find_bench as _bench,
    parse_latest_job_error as _parse_latest_job,
    run_cmd as _run,
    utf8_env as _utf8_env,
)


def run_oracle(bench: str, task_dir: Path, env: dict[str, str]) -> dict:
    r = _run(
        [bench, "eval", "create", "--tasks-dir", str(task_dir), "--agent", "oracle", "--sandbox", "docker"],
        env=env,
    )
    step = {"mode": "oracle", "returncode": r.returncode, "stdout": r.stdout[-3000:], "stderr": r.stderr[-2000:]}
    if r.returncode != 0:
        step.update(_parse_latest_job())
    return step


def run_agent_compare(
    bench: str,
    task_dir: Path,
    skills_dir: Path | None,
    env: dict[str, str],
    *,
    agent: str = "oracle",
    model: str = "",
) -> list[dict]:
    """Run no-skill and with-skill. Default agent=oracle for CI without API keys."""
    steps = []
    for mode in ("no-skill", "with-skill"):
        cmd = [
            bench, "eval", "create",
            "--tasks-dir", str(task_dir),
            "--agent", agent,
            "--skill-mode", mode,
            "--sandbox", "docker",
        ]
        if model:
            cmd.extend(["--model", model])
        if mode == "with-skill" and skills_dir:
            cmd.extend(["--skills-dir", str(skills_dir)])
        r = _run(cmd, env=env)
        step = {"mode": mode, "returncode": r.returncode, "stdout": r.stdout[-2000:]}
        if r.returncode != 0:
            step.update(_parse_latest_job())
        steps.append(step)
    return steps


def main() -> int:
    p = argparse.ArgumentParser(description="Official SkillsBench Phase 1 eval")
    p.add_argument("--task", default=os.environ.get("SKILLSBENCH_TASK", SMOKE_TASK))
    p.add_argument("--skill", default="", help="SkillOS skill folder name to export for with-skill")
    p.add_argument("--oracle-only", action="store_true", help="Only run oracle (CI default)")
    p.add_argument("--agent", default=os.environ.get("SKILLSBENCH_AGENT", "oracle"))
    p.add_argument("--model", default=os.environ.get("SKILLSBENCH_MODEL", ""))
    args = p.parse_args()

    env = _utf8_env()
    bench = _bench(env)
    ts = int(time.time())
    out_path = ROOT / "data" / "benchmarks" / f"official_eval_{ts}.json"
    result: dict = {"phase": "1", "task_id": args.task, "skill": args.skill or None, "steps": []}

    print("=== Official SkillsBench Phase 1 ===")
    task_dir = _ensure_task(args.task)
    result["task_dir"] = str(task_dir)

    r = _run([bench, "tasks", "check", str(task_dir)], env=env, timeout=120)
    result["steps"].append({"name": "tasks_check", "returncode": r.returncode})
    if r.returncode != 0:
        result["status"] = "failed"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(r.stderr or r.stdout)
        return 1
    print(r.stdout.strip())

    if args.oracle_only or not args.skill:
        step = run_oracle(bench, task_dir, env)
        result["steps"].append(step)
        result["status"] = "oracle_pass" if step["returncode"] == 0 else "failed"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nStatus: {result['status']}\nSaved: {out_path}")
        return 0 if step["returncode"] == 0 else 1

    with tempfile.TemporaryDirectory(prefix="skillos-bench-") as tmp:
        skills_dir = Path(tmp) / "skills"
        exported = export_skill_for_official(args.skill, skills_dir)
        result["exported_skill_dir"] = str(exported)
        print(f"Exported skill -> {exported}")

        if args.agent == "oracle":
            # Oracle with exported skill vs bundled — still validates export layout
            for label, sdir in [("no_skill", None), ("with_exported", skills_dir)]:
                cmd = [bench, "eval", "create", "--tasks-dir", str(task_dir), "--agent", "oracle", "--sandbox", "docker"]
                if sdir:
                    cmd.extend(["--skill-mode", "with-skill", "--skills-dir", str(sdir)])
                else:
                    cmd.extend(["--skill-mode", "no-skill"])
                r = _run(cmd, env=env)
                result["steps"].append({"name": label, "returncode": r.returncode, "stdout": r.stdout[-1500:]})
        else:
            result["steps"].extend(run_agent_compare(bench, task_dir, skills_dir, env, agent=args.agent, model=args.model))

    ok = all(s.get("returncode") == 0 for s in result["steps"] if "returncode" in s)
    result["status"] = "pass" if ok else "failed"
    if args.skill:
        result["suggested_tasks"] = suggest_tasks_for_skill(args.skill)

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nStatus: {result['status']}\nSaved: {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
