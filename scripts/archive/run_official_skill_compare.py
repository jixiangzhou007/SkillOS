"""Run official SkillsBench no-skill vs with-skill agent compare."""

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
from skillos.official_skillsbench.metrics import compare_pass_rates, find_latest_job, parse_job_summary
from skillos.official_skillsbench.presets import AGENT_COMPARE_PRESETS, DEFAULT_AGENT, DEFAULT_MODEL
from skillos.official_skillsbench.runner import ensure_task, find_bench, run_cmd, utf8_env


def _resolve_skills_dir(task_dir: Path, skill_name: str, source: str, tmp: Path) -> Path | None:
    if source == "bundled":
        bundled = task_dir / "environment" / "skills"
        return bundled if bundled.exists() else None
    if source == "export" and skill_name:
        dest = tmp / "skills"
        export_skill_for_official(skill_name, dest)
        return dest
    return None


def _run_mode(
    bench: str,
    task_dir: Path,
    env: dict,
    *,
    mode: str,
    agent: str,
    model: str,
    skills_dir: Path | None,
) -> dict:
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
    r = run_cmd(cmd, env=env, timeout=7200)
    job_dir = find_latest_job(ROOT / "jobs")
    metrics = parse_job_summary(job_dir) if job_dir else {}
    return {
        "mode": mode,
        "returncode": r.returncode,
        "metrics": metrics,
        "job_dir": str(job_dir) if job_dir else None,
        "stdout_tail": r.stdout[-2500:],
        "stderr_tail": r.stderr[-1500:] if r.stderr else "",
    }


def run_compare(
    task_id: str,
    *,
    skill_name: str = "",
    skills_source: str = "export",
    agent: str = DEFAULT_AGENT,
    model: str = DEFAULT_MODEL,
) -> dict:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY required for agent compare")

    env = utf8_env()
    env["DEEPSEEK_API_KEY"] = api_key
    if os.environ.get("DEEPSEEK_BASE_URL"):
        env["DEEPSEEK_BASE_URL"] = os.environ["DEEPSEEK_BASE_URL"]
    env.setdefault("OPENAI_API_KEY", api_key)
    env.setdefault("OPENAI_BASE_URL", env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))

    bench = find_bench(env)
    task_dir = ensure_task(task_id)

    result: dict = {
        "phase": "1-compare",
        "task_id": task_id,
        "skill": skill_name or None,
        "skills_source": skills_source,
        "agent": agent,
        "model": model,
        "runs": [],
    }

    with tempfile.TemporaryDirectory(prefix="skillos-compare-") as tmpdir:
        tmp = Path(tmpdir)
        skills_dir = _resolve_skills_dir(task_dir, skill_name, skills_source, tmp)
        if skills_source in ("bundled", "export") and skills_dir is None:
            raise SystemExit(f"No skills dir for source={skills_source} task={task_id}")

        no_skill = _run_mode(bench, task_dir, env, mode="no-skill", agent=agent, model=model, skills_dir=None)
        result["runs"].append(no_skill)

        with_skill = _run_mode(
            bench, task_dir, env, mode="with-skill", agent=agent, model=model, skills_dir=skills_dir,
        )
        result["runs"].append(with_skill)

    if no_skill.get("metrics") and with_skill.get("metrics"):
        result["comparison"] = compare_pass_rates(no_skill["metrics"], with_skill["metrics"])

    ok = all(r.get("returncode") == 0 for r in result["runs"])
    result["status"] = "pass" if ok else "failed"
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Official SkillsBench agent compare")
    p.add_argument("--preset", choices=[x["id"] for x in AGENT_COMPARE_PRESETS], help="Use a built-in preset")
    p.add_argument("--task", default="")
    p.add_argument("--skill", default="")
    p.add_argument("--skills-source", choices=["bundled", "export", "none"], default="export")
    p.add_argument("--agent", default=os.environ.get("SKILLSBENCH_AGENT", DEFAULT_AGENT))
    p.add_argument("--model", default=os.environ.get("SKILLSBENCH_MODEL", DEFAULT_MODEL))
    p.add_argument("--list-presets", action="store_true")
    args = p.parse_args()

    if args.list_presets:
        for preset in AGENT_COMPARE_PRESETS:
            print(f"{preset['id']}: {preset['description']}")
            print(f"  task={preset['task']} skill={preset['skill'] or '-'} source={preset['skills_source']}")
        return 0

    if args.preset:
        preset = next(x for x in AGENT_COMPARE_PRESETS if x["id"] == args.preset)
        task_id = preset["task"]
        skill = preset["skill"]
        source = preset["skills_source"]
    else:
        if not args.task:
            raise SystemExit("Provide --task or --preset")
        task_id = args.task
        skill = args.skill
        source = args.skills_source

    print(f"=== Agent compare: {task_id} ({source}) agent={args.agent} ===")
    result = run_compare(
        task_id,
        skill_name=skill,
        skills_source=source,
        agent=args.agent,
        model=args.model,
    )

    out = ROOT / "data" / "benchmarks" / f"official_compare_{int(time.time())}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if result.get("comparison"):
        c = result["comparison"]
        print(f"\nno-skill:  {c['no_skill_pass_rate_pct']}%")
        print(f"with-skill: {c['with_skill_pass_rate_pct']}%")
        print(f"delta:     {c['improvement']}")

    print(f"\nStatus: {result['status']}\nSaved: {out}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
