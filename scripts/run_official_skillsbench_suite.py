"""Run full official SkillsBench suite: oracle smoke + optional agent compares."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.official_skillsbench.presets import AGENT_COMPARE_PRESETS  # noqa: E402


def _run_py(args: list[str]) -> int:
    cmd = [sys.executable] + args
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="Official SkillsBench full suite")
    p.add_argument("--skip-oracle", action="store_true")
    p.add_argument("--skip-compare", action="store_true")
    p.add_argument(
        "--presets",
        default="citation-curated",
        help="Comma-separated preset ids (default: citation-curated). Use 'all' for every preset.",
    )
    p.add_argument("--smoke-task", default="citation-check")
    args = p.parse_args()

    ts = int(time.time())
    suite: dict = {"timestamp": ts, "steps": [], "status": "running"}

    if not args.skip_oracle:
        rc = _run_py([
            str(ROOT / "scripts" / "run_official_skillsbench_eval.py"),
            "--task", args.smoke_task,
            "--oracle-only",
        ])
        suite["steps"].append({"name": "oracle_smoke", "returncode": rc})
        if rc != 0:
            suite["status"] = "failed"
            _save(suite, ts)
            return rc

    if not args.skip_compare:
        if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
            suite["steps"].append({"name": "agent_compare", "skipped": True, "reason": "no DEEPSEEK_API_KEY"})
        else:
            preset_ids = [x["id"] for x in AGENT_COMPARE_PRESETS] if args.presets == "all" else args.presets.split(",")
            for pid in preset_ids:
                pid = pid.strip()
                if not pid:
                    continue
                rc = _run_py([
                    str(ROOT / "scripts" / "run_official_skill_compare.py"),
                    "--preset", pid,
                ])
                suite["steps"].append({"name": f"compare_{pid}", "returncode": rc})
                if rc != 0:
                    suite["status"] = "failed"
                    _save(suite, ts)
                    return rc

    suite["status"] = "pass"
    _save(suite, ts)
    print(f"\n=== Suite PASS ===\nSaved: data/benchmarks/official_suite_{ts}.json")
    return 0


def _save(suite: dict, ts: int) -> None:
    out = ROOT / "data" / "benchmarks" / f"official_suite_{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(suite, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
