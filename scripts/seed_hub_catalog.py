#!/usr/bin/env python3
"""Seed local SkillHub from cohort SKILL.md files.

Usage:
  python scripts/seed_hub_catalog.py
  python scripts/seed_hub_catalog.py --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed SkillHub catalog for local product use")
    parser.add_argument("--force", action="store_true", help="Seed even if catalog already has skills")
    args = parser.parse_args()
    from skillos.marketplace.seed import seed_hub_from_local_skills

    result = seed_hub_from_local_skills(force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
