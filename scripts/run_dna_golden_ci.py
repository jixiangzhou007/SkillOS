#!/usr/bin/env python3
"""Run DNA golden set — CI entry (offline, no LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.knowledge.dna_golden import assert_golden_set, run_golden_set  # noqa: E402


def main() -> int:
    report = run_golden_set()
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if not report.ok:
        print(f"\nFAIL: {report.failed} golden case(s) failed", file=sys.stderr)
        return 1
    print(f"\nOK: {report.passed}/{report.passed} golden cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
