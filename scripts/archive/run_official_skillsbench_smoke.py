"""Phase 0: smoke test official SkillsBench (BenchFlow + Docker).

Steps:
  1. Preflight: Docker, bench CLI (UTF-8), optional task download
  2. bench tasks check
  3. bench eval create --agent oracle (must reward 1.0)
  4. Optional: no-skill vs with-skill agent compare (needs API keys)

Usage:
  python scripts/run_official_skillsbench_smoke.py
  python scripts/run_official_skillsbench_smoke.py --task citation-check --skip-download
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "skillsbench"
DEFAULT_TASK = os.environ.get("SKILLSBENCH_SMOKE_TASK", "citation-check")
BENCH_DIRS = [
    Path.home() / ".local" / "bin",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
]


def _utf8_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    for d in BENCH_DIRS:
        if d.exists():
            env["PATH"] = f"{d}{os.pathsep}{env.get('PATH', '')}"
    return env


def _find_bench(env: dict[str, str]) -> str | None:
    return shutil.which("bench", path=env.get("PATH"))


def run(cmd: list[str], *, env: dict[str, str], cwd: Path | None = None, timeout: int = 3600) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def preflight(env: dict[str, str]) -> dict:
    report: dict = {"timestamp": int(time.time()), "checks": {}}

    # Docker
    docker = shutil.which("docker", path=env.get("PATH"))
    if not docker:
        report["checks"]["docker"] = {"ok": False, "error": "docker not found"}
    else:
        r = run([docker, "info"], env=env, timeout=60)
        report["checks"]["docker"] = {
            "ok": r.returncode == 0,
            "version": (r.stdout or r.stderr)[:200],
        }

    # bench CLI
    bench = _find_bench(env)
    if not bench:
        report["checks"]["bench"] = {"ok": False, "error": "bench not in PATH (uv tool install benchflow)"}
    else:
        r = run([bench, "--version"], env=env, timeout=30)
        report["checks"]["bench"] = {
            "ok": r.returncode == 0,
            "path": bench,
            "version": (r.stdout or r.stderr).strip(),
        }

    return report


def ensure_task(task_id: str, skip_download: bool) -> Path:
    task_dir = VENDOR / "tasks" / task_id
    if task_dir.joinpath("task.md").exists():
        print(f"Task already present: {task_dir}")
        return task_dir
    if skip_download:
        raise SystemExit(f"Task missing: {task_dir} (run without --skip-download)")

    sys.path.insert(0, str(ROOT))
    import importlib.util

    dl = ROOT / "scripts" / "download_official_task.py"
    spec = importlib.util.spec_from_file_location("download_official_task", dl)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {dl}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.download_task(task_id, dest_root=VENDOR / "tasks")


def parse_reward(logs_dir: Path) -> float | None:
    reward_file = logs_dir / "verifier" / "reward.txt"
    if reward_file.exists():
        try:
            return float(reward_file.read_text(encoding="utf-8").strip())
        except ValueError:
            return None
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Official SkillsBench Phase 0 smoke test")
    p.add_argument("--task", default=DEFAULT_TASK)
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--skip-oracle", action="store_true")
    p.add_argument("--with-agent-compare", action="store_true", help="Run no-skill/with-skill (needs agent API keys)")
    args = p.parse_args()

    env = _utf8_env()
    out_path = ROOT / "data" / "benchmarks" / f"official_smoke_{int(time.time())}.json"
    result: dict = {"phase": "0", "task_id": args.task, "steps": []}

    print("=== Official SkillsBench Phase 0 Smoke ===")
    result["preflight"] = preflight(env)
    for name, chk in result["preflight"]["checks"].items():
        status = "OK" if chk.get("ok") else "FAIL"
        print(f"  [{status}] {name}: {chk}")

    if not result["preflight"]["checks"].get("docker", {}).get("ok"):
        result["status"] = "blocked"
        result["blocked_reason"] = "docker_unavailable"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nBlocked: Docker required. Saved: {out_path}")
        return 1

    bench = _find_bench(env)
    if not bench:
        result["status"] = "blocked"
        result["blocked_reason"] = "bench_cli_missing"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nBlocked: install benchflow — uv tool install \"benchflow>=0.6.2,<0.7\"")
        print(f"Saved: {out_path}")
        return 1

    try:
        task_dir = ensure_task(args.task, args.skip_download)
    except SystemExit as e:
        result["status"] = "blocked"
        result["blocked_reason"] = "task_download_failed"
        result["error"] = str(e)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nBlocked: {e}")
        return 1

    result["task_dir"] = str(task_dir)

    # bench tasks check
    r = run([bench, "tasks", "check", str(task_dir)], env=env, timeout=120)
    step = {"name": "tasks_check", "returncode": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]}
    result["steps"].append(step)
    print(step["stdout"] or step["stderr"])
    if r.returncode != 0:
        result["status"] = "failed"
        result["failed_at"] = "tasks_check"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Failed at tasks check. Saved: {out_path}")
        return 1

    if args.skip_oracle:
        result["status"] = "preflight_ok"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nPreflight OK (oracle skipped). Saved: {out_path}")
        return 0

    # Oracle eval (no LLM)
    r = run(
        [
            bench, "eval", "create",
            "--tasks-dir", str(task_dir),
            "--agent", "oracle",
            "--sandbox", "docker",
        ],
        env=env,
        timeout=3600,
    )
    step = {
        "name": "oracle_eval",
        "returncode": r.returncode,
        "stdout": r.stdout[-4000:],
        "stderr": r.stderr[-4000:],
    }
    result["steps"].append(step)
    print(step["stdout"] or step["stderr"])

    if r.returncode != 0:
        result["status"] = "failed"
        result["failed_at"] = "oracle_eval"
        # Parse latest job summary for error detail
        jobs_root = ROOT / "jobs"
        summaries = sorted(jobs_root.glob("*/summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if summaries:
            result["oracle_summary"] = json.loads(summaries[0].read_text(encoding="utf-8"))
            trial = summaries[0].parent.glob("*/result.json")
            for tr in trial:
                result["oracle_error"] = json.loads(tr.read_text(encoding="utf-8")).get("error")
                break
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nOracle eval failed. Saved: {out_path}")
        if result.get("oracle_error"):
            print(f"Error: {result['oracle_error']}")
        return 1

    result["status"] = "oracle_pass"
    result["note"] = "Oracle passed; official BenchFlow + Docker pipeline is working."

    if args.with_agent_compare:
        skills_dir = task_dir / "environment" / "skills"
        for mode in ("no-skill", "with-skill"):
            cmd = [
                bench, "eval", "create",
                "--tasks-dir", str(task_dir),
                "--agent", "claude-agent-acp",
                "--skill-mode", mode,
            ]
            if mode == "with-skill" and skills_dir.exists():
                cmd.extend(["--skills-dir", str(skills_dir)])
            r = run(cmd, env=env, timeout=3600)
            result["steps"].append({
                "name": f"agent_{mode}",
                "returncode": r.returncode,
                "stdout": r.stdout[-2000:],
                "stderr": r.stderr[-2000:],
            })

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== Phase 0 PASS (oracle) ===\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
