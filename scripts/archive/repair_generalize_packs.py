#!/usr/bin/env python3
"""Prune cross-domain quick8 tasks from generalize domain packs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.skills.bench_cohorts import GENERALIZE_SKILLS
from skillos.skills.cold_start import repair_domain_pack


def main() -> int:
    results = []
    for spec in GENERALIZE_SKILLS:
        dt = spec.get("domain_template")
        if not dt:
            continue
        row = repair_domain_pack(dt)
        results.append(row)
        flag = "CHANGED" if row.get("changed") else "OK"
        removed = row.get("removed") or []
        print(f"[{flag}] {dt}: removed={removed} quick8={row.get('quick8_tasks', [])}")

    out = ROOT / "data" / "benchmarks" / "repair_packs_latest.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
