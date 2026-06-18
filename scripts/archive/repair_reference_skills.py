#!/usr/bin/env python3
"""Repair reference skills: sanitize body, structure pipeline, bench_quality meta."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.skills.post_extraction_bench import REFERENCE_SKILLS, repair_skill


def main() -> int:
    results = [repair_skill(n) for n in sorted(REFERENCE_SKILLS)]
    out = ROOT / "data" / "benchmarks" / "skill_repair_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Skill repair ===")
    for r in results:
        bq = r["bench_quality"]
        gate = bq.get("save_gate", {})
        dna = bq.get("dna_compliance", {})
        moe = bq.get("moe") or {}
        print(
            f"  {r['skill']}: DNA {dna.get('score')} "
            f"smoke={'OK' if gate.get('smoke_pass') else 'FAIL'} "
            f"moe={moe.get('overall_score', '—')}"
        )
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
