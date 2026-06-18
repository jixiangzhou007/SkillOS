#!/usr/bin/env python3
"""CI/nightly Quick8 benchmark for reference skills (LLM + cache)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_SKILLS = (
    "CSV数据清洗助手",
    "GitHub Pull",
    "电商客服退款处理",
)


def _parse_pct(value: str) -> float:
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    from skillos.benchmark_local import run_quick8_for_skill
    from skillos.skills_bench import SKILLS_DIR

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("DEEPSEEK_API_KEY not set — skipping Quick8 CI")
        return 0

    skills_env = os.environ.get("SKILLS_QUICK8", "").strip()
    skills = [s.strip() for s in skills_env.split(",") if s.strip()] if skills_env else list(DEFAULT_SKILLS)

    min_pct = float(os.environ.get("QUICK8_MIN_IMPROVEMENT_PCT", "-20"))
    min_injected = int(os.environ.get("QUICK8_MIN_INJECTED", "1"))

    out: dict = {
        "timestamp": int(time.time()),
        "mode": "quick8_ci",
        "skills": skills,
        "results": [],
        "ok": True,
    }

    for name in skills:
        md = SKILLS_DIR / name / "SKILL.md"
        if not md.exists():
            out["results"].append({"skill": name, "error": "missing SKILL.md", "ok": False})
            out["ok"] = False
            continue
        print(f"\n=== Quick8 CI: {name} ===")
        try:
            row = run_quick8_for_skill(name, skills_dir=SKILLS_DIR)
            pct = _parse_pct(row.get("improvement_pct", "0"))
            domain_pct = _parse_pct(row.get("domain_improvement_pct", row.get("improvement_pct", "0")))
            injected = int(row.get("skills_injected") or 0)
            harm = row.get("harm_tasks") or []
            max_harm = int(os.environ.get("QUICK8_MAX_HARM_TASKS", "0"))
            row_ok = (
                pct >= min_pct
                and domain_pct >= min_pct
                and injected >= min_injected
                and len(harm) <= max_harm
            )
            row["improvement_pct_num"] = pct
            row["domain_improvement_pct_num"] = domain_pct
            row["ok"] = row_ok
            out["results"].append(row)
            print(
                f"  Δ {row.get('improvement_pct')} · 域内 {row.get('domain_improvement_pct', 'n/a')} · "
                f"inject {injected}/{row.get('tasks')} · harm {len(harm)} · ok={row_ok}",
            )
            if harm:
                print(f"  harm_tasks: {harm}", file=sys.stderr)
            if not row_ok:
                out["ok"] = False
                print(
                    f"  FAIL gate: min_pct={min_pct}, min_injected={min_injected}, max_harm={max_harm}",
                    file=sys.stderr,
                )
        except Exception as exc:
            out["results"].append({"skill": name, "error": str(exc), "ok": False})
            out["ok"] = False
            print(f"  ERROR: {exc}", file=sys.stderr)

    bench_dir = ROOT / "data" / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    path = bench_dir / f"quick8_ci_{out['timestamp']}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {path}")
    print(json.dumps({"ok": out["ok"], "skills": len(out["results"])}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
