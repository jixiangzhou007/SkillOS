#!/usr/bin/env python3
"""Sync reference domain packs from configs/ into data/domain_packs/."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REFERENCE_PACKS_DIR = ROOT / "configs" / "reference_domain_packs"
REFERENCE_TEMPLATES = (
    "workflow-refund",
    "code-review-pr",
    "data-csv-clean",
)


def sync_reference_packs(*, dry_run: bool = False) -> list[dict]:
    """Copy tracked reference pack JSON into runtime data/domain_packs/."""
    from skillos.skills.domain_pack import save_domain_pack

    rows: list[dict] = []
    for template_id in REFERENCE_TEMPLATES:
        src = REFERENCE_PACKS_DIR / f"{template_id}.json"
        if not src.is_file():
            rows.append({"domain_template": template_id, "ok": False, "error": "missing config"})
            continue
        pack = json.loads(src.read_text(encoding="utf-8"))
        pack["updated_at"] = int(time.time())
        if dry_run:
            rows.append({"domain_template": template_id, "ok": True, "dry_run": True})
            continue
        path = save_domain_pack(pack)
        rows.append({"domain_template": template_id, "ok": True, "path": str(path)})
    return rows


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Sync reference domain packs to data/domain_packs/")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    rows = sync_reference_packs(dry_run=args.dry_run)
    for row in rows:
        flag = "OK" if row.get("ok") else "FAIL"
        print(f"[{flag}] {row.get('domain_template')}: {row.get('path') or row.get('error', '')}")
    if any(not r.get("ok") for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
