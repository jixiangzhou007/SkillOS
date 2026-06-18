#!/usr/bin/env python3
"""Run Path B cold-start on generalized skills and re-benchmark."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if val and key not in os.environ:
            os.environ[key] = val

from skillos.skills.bench_cohorts import GENERALIZE_SKILLS

GENERALIZE_SPECS = GENERALIZE_SKILLS


def main() -> int:
    from skillos.skills.cold_start import run_cold_start
    from skillos.skills.post_extraction_bench import repair_skill
    from skillos.skills.skill_store import load_skill_raw

    results = []
    for spec in GENERALIZE_SPECS:
        name = spec["name"]
        print(f"\n=== Cold start: {name} ===")
        raw = load_skill_raw(name)
        body = raw.get("body", "")
        meta = raw.get("meta") or {}
        cs = run_cold_start(
            name,
            body,
            domain_template=spec["domain_template"],
            bench_categories=meta.get("bench_categories"),
            anchor_task_ids=spec["anchor_tasks"],
            force=os.environ.get("SKILLOS_FORCE_COLD_START", "").strip().lower() in ("1", "true", "yes"),
        )
        print(f"  rounds={len(cs.rounds)} min={cs.min_with_score} passed={cs.passed}")
        print(f"  pack={cs.pack_path}")
        from skillos.skills.skill_store import _compose, _skill_path, resolve_skills_root
        from skillos.skills.skill_structure import apply_structure_pipeline

        path = _skill_path(name, root=resolve_skills_root())
        body2, pipe_meta = apply_structure_pipeline(
            name, cs.body, skill_md_path=path, domain_template=spec["domain_template"],
        )
        raw["body"] = body2
        meta["domain_template"] = spec["domain_template"]
        meta["domain_template_id"] = spec["domain_template"]
        if cs.bench_categories:
            meta["bench_categories"] = cs.bench_categories
        path.write_text(_compose(meta, body2), encoding="utf-8")
        repair = {"pipeline": pipe_meta, "cold_start_only": True}
        results.append({
            "skill": name,
            "cold_start": cs.to_dict(),
            "repair": repair,
        })

    ts = int(time.time())
    out = ROOT / "data" / "benchmarks" / f"cold_start_{ts}.json"
    out.write_text(json.dumps({"timestamp": ts, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
