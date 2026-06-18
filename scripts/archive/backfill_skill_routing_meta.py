#!/usr/bin/env python3
"""Backfill domain / bench_categories into existing SKILL.md files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.knowledge.skill_routing import backfill_skill_routing_meta  # noqa: E402
from skillos.skills_bench import SKILLS_DIR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill skill routing YAML metadata")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    parser.add_argument("--names", nargs="*", help="Skill folder names (default: all)")
    args = parser.parse_args()

    if args.names:
        paths = [SKILLS_DIR / name / "SKILL.md" for name in args.names]
    else:
        paths = sorted(SKILLS_DIR.glob("*/SKILL.md"))

    results = []
    changed = 0
    for path in paths:
        if not path.exists():
            print(f"SKIP missing: {path}")
            continue
        row = backfill_skill_routing_meta(path, dry_run=args.dry_run)
        results.append(row)
        if row["changed"]:
            changed += 1
            flag = "DRY" if args.dry_run else "OK"
            print(f"[{flag}] {row['name']}: {row.get('bench_categories', [])}")
        else:
            print(f"[--] {row['name']}: up to date")

    print(f"\nTotal: {len(results)} skills, {changed} would update")
    out = ROOT / "data" / "benchmarks" / "backfill_routing_meta.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
