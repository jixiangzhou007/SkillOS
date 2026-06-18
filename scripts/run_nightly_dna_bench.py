#!/usr/bin/env python3
"""Nightly DNA + SkillsBench benchmark (offline golden + optional LLM compare)."""


import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillos.knowledge.dna_golden import (  # noqa: E402
    NIGHTLY_DIR,
    load_baseline,
    run_golden_set,
)


def _run_gates() -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_skill_bench_gates.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = proc.stdout or ""
    return {
        "exit_code": proc.returncode,
        "stdout_tail": stdout.strip().splitlines()[-5:],
        "ok": proc.returncode == 0,
    }


def _run_llm_compare(skills: list[str]) -> list[dict]:
    from skillos.skills_bench import SKILLS_DIR
    from skillos.skillsbench_tasks import compare_with_without

    rows: list[dict] = []
    for name in skills:
        md = SKILLS_DIR / name / "SKILL.md"
        if not md.exists():
            continue
        try:
            cmp = compare_with_without(str(md), routed=True)
            rows.append({
                "skill": name,
                "matched_delta": cmp.get("matched_delta"),
                "harm_score": cmp.get("harm_score"),
                "matched_tasks": cmp.get("matched_tasks"),
                "with_skill_score": cmp.get("with_skill_score"),
                "without_skill_score": cmp.get("without_skill_score"),
                "bench_categories": cmp.get("bench_categories"),
            })
        except Exception as exc:
            rows.append({"skill": name, "error": str(exc)})
    return rows


def main() -> int:
    baseline = load_baseline()
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    golden = run_golden_set()
    gates = _run_gates()

    out: dict = {
        "started_at": started,
        "golden": golden.to_dict(),
        "gates": gates,
        "llm_compare": [],
        "llm_skipped": True,
    }

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    skills = list(baseline.get("reference_skills", {}).keys()) or [
        c["skill"] for c in json.loads(
            (ROOT / "data" / "benchmarks" / "dna" / "golden_set.json").read_text(encoding="utf-8")
        ).get("reference_skills", [])
    ]

    if api_key:
        print("Running LLM routed compare for reference skills (nightly)…")
        out["llm_compare"] = _run_llm_compare(skills)
        out["llm_skipped"] = False
        llm_cfg = baseline.get("llm_compare", {})
        for row in out["llm_compare"]:
            if row.get("error"):
                continue
            if row.get("matched_delta", -999) < llm_cfg.get("min_matched_delta", -50):
                print(f"WARN: {row['skill']} matched_delta below threshold", file=sys.stderr)
            if row.get("harm_score", 0) > llm_cfg.get("max_harm_score", 200):
                print(f"WARN: {row['skill']} harm_score above threshold", file=sys.stderr)
    else:
        print("DEEPSEEK_API_KEY not set — skipping LLM compare (offline golden only)")

    min_rate = baseline.get("golden_min_pass_rate", 1.0)
    ok = golden.ok and gates["ok"] and golden.to_dict()["pass_rate"] >= min_rate

    out["ok"] = ok
    out["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    NIGHTLY_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    path = NIGHTLY_DIR / f"run_{ts}.json"
    latest = NIGHTLY_DIR / "latest.json"
    text = json.dumps(out, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")
    print(json.dumps({"ok": ok, "golden_passed": golden.passed, "gates_ok": gates["ok"]}, ensure_ascii=False))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
