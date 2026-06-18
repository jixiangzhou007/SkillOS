#!/usr/bin/env python3
"""Migrate legacy ``skills/`` tree into tenant layout (Sprint 0 · F7).

Usage:
  python scripts/migrate_legacy_skills.py --dry-run
  python scripts/migrate_legacy_skills.py --target org:default
  python scripts/migrate_legacy_skills.py --target personal:migration

After migration, set ``SKILLOS_LEGACY_MODE=false`` and point new writes at tenants.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _legacy_root() -> Path:
    from skillos.skills.skill_store import _legacy_skills_dir
    return _legacy_skills_dir()


def _dest_root(target: str) -> Path:
    from skillos.identity.context import TenantContext

    if target.startswith("personal:"):
        uid = target.split(":", 1)[1]
        if not uid.startswith("usr_"):
            uid = f"usr_{uid}"
        return TenantContext.personal(uid).skills_root()
    if target.startswith("org:"):
        oid = target.split(":", 1)[1]
        if not oid.startswith("org_"):
            oid = f"org_{oid}"
        return TenantContext.organization(oid).skills_root()
    raise SystemExit(f"Invalid --target {target!r}; use personal:ID or org:ID")


def migrate(*, target: str, dry_run: bool) -> dict:
    src = _legacy_root()
    dst = _dest_root(target)
    copied = 0
    skipped = 0

    if not src.exists():
        return {"copied": 0, "skipped": 0, "src": str(src), "dst": str(dst)}

    for skill_md in sorted(src.glob("*/SKILL.md")):
        rel = skill_md.parent.name
        out_dir = dst / rel
        if out_dir.exists() and any(out_dir.iterdir()):
            skipped += 1
            continue
        if dry_run:
            copied += 1
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in skill_md.parent.iterdir():
            dest = out_dir / f.name
            if f.is_dir():
                shutil.copytree(f, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(f, dest)
        copied += 1

    return {"copied": copied, "skipped": skipped, "src": str(src), "dst": str(dst)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy skills/ to tenant paths")
    parser.add_argument(
        "--target",
        default="org:default",
        help="Tenant target, e.g. org:default or personal:migration",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = migrate(target=args.target, dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "DONE"
    print(f"[{mode}] copied={result['copied']} skipped={result['skipped']}")
    print(f"  from: {result['src']}")
    print(f"  to:   {result['dst']}")
    if not args.dry_run and result["copied"]:
        print("\nNext: export SKILLOS_LEGACY_MODE=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
