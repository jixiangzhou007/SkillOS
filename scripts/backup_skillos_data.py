#!/usr/bin/env python3
"""Backup SkillOS data directory — SQLite DBs, tenant skills, epistemic state.

Usage:
  python scripts/backup_skillos_data.py
  python scripts/backup_skillos_data.py --output D:/backups/skillos_20260614.zip

See docs/sprint11/GOVERNANCE.md for restore runbook.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root without install
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def resolve_data_dir() -> Path:
    env = os.getenv("SKILLOS_DATA_DIR", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        return p
    return (_REPO / "data").resolve()


def _add_path(zf: zipfile.ZipFile, base: Path, rel: Path) -> int:
    added = 0
    full = base / rel
    if full.is_file():
        zf.write(full, rel.as_posix())
        return 1
    if full.is_dir():
        for fp in full.rglob("*"):
            if fp.is_file():
                zf.write(fp, fp.relative_to(base).as_posix())
                added += 1
    return added


def create_backup(output: Path | None = None) -> Path:
    data_dir = resolve_data_dir()
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = output or (data_dir.parent / "backups" / f"skillos_backup_{ts}.zip")
    out.parent.mkdir(parents=True, exist_ok=True)

    includes = [
        Path("skillhub.db"),
        Path("tenants"),
        Path("epistemic_state.json"),
    ]

    count = 0
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in includes:
            count += _add_path(zf, data_dir, rel)
        for db in data_dir.glob("*.db"):
            if db.name != "skillhub.db":
                zf.write(db, db.name)
                count += 1

    print(f"Backup written: {out} ({count} files from {data_dir})")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup SkillOS data directory")
    parser.add_argument("--output", "-o", default="", help="Output .zip path")
    args = parser.parse_args()
    out = Path(args.output).expanduser() if args.output else None
    create_backup(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
