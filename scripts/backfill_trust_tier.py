#!/usr/bin/env python3
"""Backfill trust_tier + gates into existing SKILL.md frontmatter (no version bump)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def backfill(*, dry_run: bool = False, names: list[str] | None = None) -> list[dict]:
    from skillos.evaluation.trust_tier import compute_trust_tier
    from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload
    from skillos.skills.skill_store import _compose, _skill_path, list_skills, load_skill_raw

    targets = names or list_skills()
    rows: list[dict] = []
    for name in targets:
        try:
            raw = load_skill_raw(name)
        except FileNotFoundError:
            rows.append({"skill": name, "ok": False, "error": "missing"})
            continue
        meta = dict(raw.get("meta") or {})
        ep = format_epistemic_api_payload(meta)
        gate = (meta.get("bench_quality") or {}).get("save_gate") or meta.get("save_gate")
        snap = compute_trust_tier(
            epistemic=ep,
            gate_meta=gate,
            draft=bool(meta.get("draft")),
        )
        changed = meta.get("trust_tier") != snap["trust_tier"] or meta.get("gates") != snap["gates"]
        if changed and not dry_run:
            meta["trust_tier"] = snap["trust_tier"]
            meta["gates"] = snap["gates"]
            _skill_path(name).write_text(
                _compose(meta, raw.get("body") or ""),
                encoding="utf-8",
            )
        rows.append(
            {
                "skill": name,
                "ok": True,
                "trust_tier": snap["trust_tier"],
                "changed": changed,
                "dry_run": dry_run,
            }
        )
    return rows


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Backfill trust_tier on skills")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skill", action="append", dest="skills", help="Limit to skill name(s)")
    args = p.parse_args()

    rows = backfill(dry_run=args.dry_run, names=args.skills)
    changed = sum(1 for r in rows if r.get("changed"))
    for r in rows:
        if not r.get("ok"):
            print(f"[FAIL] {r.get('skill')}: {r.get('error')}")
            continue
        flag = "CHG" if r.get("changed") else "OK"
        print(f"[{flag}] {r['skill']}: {r.get('trust_tier')}")
    print(f"\n{changed}/{len(rows)} changed")
    return 0 if all(r.get("ok") for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
