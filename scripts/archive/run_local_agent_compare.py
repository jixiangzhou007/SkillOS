#!/usr/bin/env python3
"""Local LLM agent compare — mirrors official presets using SkillOS Quick8 (Windows-safe)."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env (DEEPSEEK_*)
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

from skillos.benchmark_local import run_quick8_for_skill
from skillos.official_skillsbench.metrics import compare_pass_rates
from skillos.official_skillsbench.presets import AGENT_COMPARE_PRESETS

# Official task → local compare mode
PRESET_LOCAL: dict[str, dict] = {
    "csv-sales-pivot": {"domain_only": False},
    "pr-dependency-audit": {"domain_only": False},
    "refund-invoice-fraud": {"domain_only": True},
}


def run_preset(preset_id: str) -> dict:
    preset = next(x for x in AGENT_COMPARE_PRESETS if x["id"] == preset_id)
    skill = preset.get("skill") or ""
    if not skill:
        raise SystemExit(f"Preset {preset_id} has no SkillOS skill — use official bench on Linux")

    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        raise SystemExit("DEEPSEEK_API_KEY required (set in .env)")

    opts = PRESET_LOCAL.get(preset_id, {"domain_only": False})
    row = run_quick8_for_skill(skill, domain_only=opts["domain_only"])

    baseline = {
        "pass_rate_pct": round(row["without_skill_score"] / max(1, row["max_score"]) * 100, 1),
        "score": row["without_skill_score"],
        "max_score": row["max_score"],
    }
    with_skill = {
        "pass_rate_pct": round(row["with_skill_score"] / max(1, row["max_score"]) * 100, 1),
        "score": row["with_skill_score"],
        "max_score": row["max_score"],
    }
    comparison = compare_pass_rates(
        {"pass_rate_pct": baseline["pass_rate_pct"]},
        {"pass_rate_pct": with_skill["pass_rate_pct"]},
    )

    return {
        "phase": "local-compare",
        "mode": "skillos_quick8",
        "preset": preset_id,
        "official_task": preset["task"],
        "skill": skill,
        "domain_only": opts["domain_only"],
        "agent": "llm+regex-grader",
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek"),
        "baseline": baseline,
        "with_skill": with_skill,
        "comparison": comparison,
        "skills_injected": row.get("skills_injected"),
        "tasks": row.get("tasks"),
        "task_ids": row.get("task_ids"),
        "per_task": row.get("per_task"),
        "domain_improvement_pct": row.get("domain_improvement_pct"),
        "harm_tasks": row.get("harm_tasks") or [],
        "source_file": row.get("file"),
        "status": "pass",
        "note": "Local Quick8 proxy — not official BenchFlow pass rate. Use Linux CI for authoritative eval.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Local agent compare (Quick8 proxy for official presets)")
    p.add_argument("--preset", choices=[x["id"] for x in AGENT_COMPARE_PRESETS if x.get("skill")], help="Single preset")
    p.add_argument("--all", action="store_true", help="Run all SkillOS skill presets")
    p.add_argument("--list-presets", action="store_true")
    args = p.parse_args()

    if args.list_presets:
        for preset in AGENT_COMPARE_PRESETS:
            if not preset.get("skill"):
                continue
            loc = PRESET_LOCAL.get(preset["id"], {})
            print(f"{preset['id']}: {preset['skill']} → official {preset['task']} domain_only={loc.get('domain_only', False)}")
        return 0

    ids = [args.preset] if args.preset else []
    if args.all:
        ids = [x["id"] for x in AGENT_COMPARE_PRESETS if x.get("skill")]
    if not ids:
        ids = ["refund-invoice-fraud"]

    results = []
    for pid in ids:
        print(f"\n=== Local compare: {pid} ===")
        r = run_preset(pid)
        results.append(r)
        c = r["comparison"]
        print(f"no-skill:   {c['no_skill_pass_rate_pct']}% ({r['baseline']['score']}/{r['baseline']['max_score']})")
        print(f"with-skill: {c['with_skill_pass_rate_pct']}% ({r['with_skill']['score']}/{r['with_skill']['max_score']})")
        print(f"delta:      {c['improvement']} · inject {r.get('skills_injected')}/{r.get('tasks')}")

    out = ROOT / "data" / "benchmarks" / f"local_compare_{int(time.time())}.json"
    payload = {"timestamp": int(time.time()), "presets": results}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
