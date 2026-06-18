#!/usr/bin/env python3
"""Refresh stale dna_lineage queue and optionally re-backfill skills."""


import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.knowledge.dna_evolution import (  # noqa: E402
    process_stale_queue,
    refresh_stale_queue,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="DNA stale lineage queue")
    parser.add_argument("--scan-only", action="store_true", help="Only refresh queue JSON")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    if args.scan_only:
        payload = refresh_stale_queue()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"\n{len(payload.get('items', []))} stale skill(s)")
        return 0

    result = process_stale_queue(dry_run=args.dry_run, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
