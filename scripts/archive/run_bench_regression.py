#!/usr/bin/env python3
"""Local benchmark regression — reference Quick8 + generalize domain Quick8 + smoke gates."""
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

from skillos.skills.bench_cohorts import (
    GENERALIZE_SKILLS,
    REFERENCE_MIN_DELTA_PP,
    REFERENCE_PRESETS,
)


def run_quick8_regression() -> list[dict]:
    from scripts.run_local_agent_compare import run_preset

    rows = []
    for preset_id in REFERENCE_MIN_DELTA_PP:
        row = run_preset(preset_id)
        delta = float(row["comparison"]["delta_pp"])
        row["min_delta_pp"] = REFERENCE_MIN_DELTA_PP[preset_id]
        row["regression_pass"] = delta >= REFERENCE_MIN_DELTA_PP[preset_id]
        row["cohort"] = "reference"
        rows.append(row)
    return rows


def run_generalize_domain_quick8() -> list[dict]:
    from skillos.benchmark_local import run_quick8_for_skill

    rows = []
    for spec in GENERALIZE_SKILLS:
        name = spec["name"]
        try:
            q8 = run_quick8_for_skill(name, domain_only=True)
        except Exception as exc:
            rows.append({
                "skill": name,
                "domain_template": spec.get("domain_template"),
                "cohort": "generalize",
                "error": str(exc),
                "regression_pass": False,
            })
            continue
        delta = float(q8.get("domain_delta") or (q8["with_skill_score"] - q8["without_skill_score"]))
        min_delta = float(spec.get("min_domain_delta") or 0)
        rows.append({
            "skill": name,
            "domain_template": spec.get("domain_template"),
            "cohort": "generalize",
            "domain_delta": delta,
            "min_domain_delta": min_delta,
            "skills_injected": q8.get("skills_injected"),
            "tasks": q8.get("tasks"),
            "task_ids": q8.get("task_ids"),
            "per_task": q8.get("per_task"),
            "regression_pass": delta >= min_delta,
        })
    return rows


def run_smoke_gates() -> list[dict]:
    from skillos.evaluation.save_gate import run_domain_smoke_suite
    from skillos.skills.skill_store import load_skill_raw

    out = []
    all_specs = [
        *({"preset": pid, "skill": name, "cohort": "reference"} for pid, name in REFERENCE_PRESETS.items()),
        *({"skill": s["name"], "cohort": "generalize", "domain_template": s.get("domain_template")} for s in GENERALIZE_SKILLS),
    ]
    for spec in all_specs:
        skill_name = spec["skill"]
        raw = load_skill_raw(skill_name)
        meta = raw.get("meta", {})
        body = raw.get("body", "")
        suite = run_domain_smoke_suite(
            skill_name,
            body,
            bench_categories=meta.get("bench_categories"),
            domain_template=meta.get("domain_template") or meta.get("domain_template_id") or spec.get("domain_template"),
        )
        min_score = min((r["with_score"] for r in suite), default=0)
        out.append({
            **spec,
            "domain_template": meta.get("domain_template") or spec.get("domain_template"),
            "suite": suite,
            "min_with_score": min_score,
            "smoke_pass": min_score >= 80,
        })
    return out


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        print("ERROR: DEEPSEEK_API_KEY required")
        return 1

    ts = int(time.time())
    quick8 = run_quick8_regression()
    generalize = run_generalize_domain_quick8()
    smoke = run_smoke_gates()

    failed_q = [r for r in quick8 if not r.get("regression_pass")]
    failed_g = [r for r in generalize if not r.get("regression_pass")]
    failed_s = [r for r in smoke if not r.get("smoke_pass")]

    payload = {
        "timestamp": ts,
        "quick8": quick8,
        "generalize_domain_quick8": generalize,
        "domain_smoke": smoke,
        "summary": {
            "quick8_pass": len(failed_q) == 0,
            "generalize_pass": len(failed_g) == 0,
            "smoke_pass": len(failed_s) == 0,
            "all_pass": len(failed_q) == 0 and len(failed_g) == 0 and len(failed_s) == 0,
        },
    }
    out = ROOT / "data" / "benchmarks" / f"bench_regression_{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Reference Quick8 regression ===")
    for r in quick8:
        c = r["comparison"]
        flag = "OK" if r["regression_pass"] else "FAIL"
        print(
            f"  [{flag}] {r['preset']}: {c['improvement']} "
            f"(min {r['min_delta_pp']}pp) inject {r.get('skills_injected')}/{r.get('tasks')}"
        )

    print("\n=== Generalize domain Quick8 ===")
    for r in generalize:
        flag = "OK" if r.get("regression_pass") else "FAIL"
        if r.get("error"):
            print(f"  [{flag}] {r['skill']}: ERROR {r['error']}")
        else:
            print(
                f"  [{flag}] {r['skill']}: Δ={r.get('domain_delta')} "
                f"(min {r.get('min_domain_delta')}) inject {r.get('skills_injected')}/{r.get('tasks')}"
            )

    print("\n=== Domain smoke gates (reference + generalize) ===")
    for r in smoke:
        flag = "OK" if r["smoke_pass"] else "FAIL"
        tasks = [x["task_id"] for x in r["suite"]]
        print(f"  [{flag}] [{r.get('cohort')}] {r['skill']}: min={r['min_with_score']} tasks={tasks}")

    print(f"\nSaved: {out}")
    if failed_q or failed_g or failed_s:
        print("\nREGRESSION FAILED")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
