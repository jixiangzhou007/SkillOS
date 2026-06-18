#!/usr/bin/env python3
"""Backfill dna_lineage into existing SKILL.md frontmatter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.knowledge.dna_store import backfill_skill_lineage  # noqa: E402
from skillos.skills_bench import SKILLS_DIR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill dna_lineage YAML metadata")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--names", nargs="*", help="Skill folder names (default: all)")
    args = parser.parse_args()

    if args.names:
        paths = [SKILLS_DIR / n / "SKILL.md" for n in args.names]
    else:
        paths = sorted(SKILLS_DIR.glob("*/SKILL.md"))

    results = []
    changed = 0
    for path in paths:
        if not path.exists():
            print(f"SKIP: {path}")
            continue
        row = backfill_skill_lineage(path, dry_run=args.dry_run)
        results.append({"path": row["path"], "name": row["name"], "changed": row["changed"]})
        flag = "DRY" if args.dry_run else ("OK" if row["changed"] else "--")
        philo = [p["id"] for p in row["lineage"].get("philosophical", [])]
        domain = [d["id"] for d in row["lineage"].get("domain", [])]
        print(f"[{flag}] {row['name']}: philo={philo} domain={domain}")
        if row["changed"]:
            changed += 1

    out = ROOT / "data" / "dna" / "backfill_lineage_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{changed}/{len(results)} updated — report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
