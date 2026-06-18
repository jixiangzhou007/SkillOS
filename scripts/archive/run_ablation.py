#!/usr/bin/env python3
"""Run HERITAGE × pack-scoped inject ablation (2×2) on generalize cohort."""
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


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        print("ERROR: DEEPSEEK_API_KEY required")
        return 1

    from skillos.evaluation.ablation import ABLATION_CONDITIONS, run_ablation_study

    include_ref = os.environ.get("SKILLOS_ABLATION_SKIP_REF", "").strip().lower() not in ("1", "true", "yes")
    payload = run_ablation_study(include_reference=include_ref, domain_only=True)

    ts = payload.get("timestamp") or int(time.time())
    out = ROOT / "data" / "benchmarks" / f"ablation_{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Ablation 2×2: HERITAGE × pack-scoped inject ===\n")
    for summary in payload.get("skill_summaries") or []:
        print(f"--- {summary['skill']} ---")
        conds = summary.get("conditions") or {}
        for c in ABLATION_CONDITIONS:
            row = conds.get(c["id"]) or {}
            print(
                f"  [{c['label']:16}] Δ={row.get('domain_delta', '?'):>4} "
                f"inject={row.get('inject_rate', '?')} anchor_Δ={row.get('anchor_delta', '?')}"
            )
        m = summary.get("marginals") or {}
        if m:
            print(
                f"  marginals: heritage={m.get('heritage_marginal')} "
                f"pack={m.get('pack_marginal')} interaction={m.get('interaction')}"
            )
        print()

    cs = payload.get("cohort_summary") or {}
    med = cs.get("generalize_median_by_condition") or {}
    print("=== Generalize cohort median domain Δ ===")
    for c in ABLATION_CONDITIONS:
        print(f"  {c['label']:16}: {med.get(c['id'])}")
    mm = cs.get("generalize_mean_marginals") or {}
    if mm:
        print(
            f"\nMean marginals (generalize): heritage={mm.get('heritage_marginal')} "
            f"pack={mm.get('pack_marginal')} interaction={mm.get('interaction')}"
        )
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
