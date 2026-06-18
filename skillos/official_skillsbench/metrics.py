"""Parse BenchFlow job artifacts into pass-rate metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_job_summary(job_dir: Path) -> dict[str, Any]:
    summary_path = job_dir / "summary.json"
    if not summary_path.exists():
        return {}
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    total = int(s.get("total") or 0)
    passed = int(s.get("passed") or 0)
    errored = int(s.get("errored") or 0)
    return {
        "job_name": s.get("job_name"),
        "total": total,
        "passed": passed,
        "failed": int(s.get("failed") or 0),
        "errored": errored,
        "pass_rate_pct": round(passed / total * 100, 1) if total else 0.0,
        "score": s.get("score"),
        "elapsed_sec": s.get("elapsed_sec"),
    }


def find_latest_job(jobs_root: Path) -> Path | None:
    summaries = sorted(jobs_root.glob("*/summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return summaries[0].parent if summaries else None


def compare_pass_rates(baseline: dict, with_skill: dict) -> dict[str, Any]:
    b = float(baseline.get("pass_rate_pct") or 0)
    w = float(with_skill.get("pass_rate_pct") or 0)
    delta = round(w - b, 1)
    return {
        "no_skill_pass_rate_pct": b,
        "with_skill_pass_rate_pct": w,
        "delta_pp": delta,
        "improvement": f"{delta:+.1f}pp",
    }
