"""Shared BenchFlow subprocess helpers for official SkillsBench scripts."""


import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "skillsbench"


def utf8_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    home_bin = Path.home() / ".local" / "bin"
    if home_bin.exists():
        env["PATH"] = f"{home_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


def find_bench(env: dict[str, str]) -> str:
    b = shutil.which("bench", path=env.get("PATH"))
    if not b:
        raise SystemExit('bench not found — run: uv tool install "benchflow>=0.6.2,<0.7"')
    return b


def run_cmd(cmd: list[str], env: dict[str, str], timeout: int = 3600) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def load_downloader():
    dl = ROOT / "scripts" / "download_official_task.py"
    spec = importlib.util.spec_from_file_location("download_official_task", dl)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {dl}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ensure_task(task_id: str) -> Path:
    task_dir = VENDOR / "tasks" / task_id
    if task_dir.joinpath("task.md").exists():
        return task_dir
    return load_downloader().download_task(task_id, dest_root=VENDOR / "tasks")


def parse_latest_job_error() -> dict:
    from skillos.official_skillsbench.metrics import find_latest_job, parse_job_summary

    job_dir = find_latest_job(ROOT / "jobs")
    if not job_dir:
        return {}
    summary = parse_job_summary(job_dir)
    err = None
    for tr in job_dir.glob("*/result.json"):
        err = json.loads(tr.read_text(encoding="utf-8")).get("error")
        break
    return {"summary": summary, "error": err, "job_dir": str(job_dir)}
