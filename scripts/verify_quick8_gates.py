#!/usr/bin/env python3
"""Offline verify latest Quick8 CI artifact (no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "data" / "benchmarks"


def _parse_pct(value: str) -> float:
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    files = sorted(BENCH.glob("quick8_ci_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("No quick8_ci_*.json — skip offline verify")
        return 0

    data = json.loads(files[0].read_text(encoding="utf-8"))
    min_pct = float(__import__("os").environ.get("QUICK8_MIN_IMPROVEMENT_PCT", "-25"))
    ok = True
    print(f"Verify {files[0].name} (min_pct={min_pct})")
    for row in data.get("results") or []:
        if row.get("error"):
            print(f"  [FAIL] {row.get('skill')}: {row['error']}")
            ok = False
            continue
        pct = row.get("domain_improvement_pct_num", row.get("improvement_pct_num"))
        if pct is None:
            pct = _parse_pct(row.get("domain_improvement_pct") or row.get("improvement_pct", "0"))
        harm = row.get("harm_tasks") or []
        row_ok = pct >= min_pct and not harm
        flag = "OK" if row_ok else "FAIL"
        print(
            f"  [{flag}] {row.get('skill')}: domain {row.get('domain_improvement_pct', row.get('improvement_pct'))} "
            f"harm={harm}",
        )
        if not row_ok:
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
