#!/usr/bin/env python3
"""Trigger Official SkillsBench GitHub Actions workflow."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env for GITHUB_TOKEN / GITHUB_REPOSITORY when present
_env = ROOT / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key.startswith("GITHUB_") and val and key not in os.environ:
            os.environ[key] = val

from skillos.official_skillsbench.service import preset_for_skill, trigger_official_ci


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger official SkillsBench CI")
    parser.add_argument("--skill", default="电商客服退款处理", help="SkillOS skill folder name")
    parser.add_argument("--preset", default="", help="Override preset id (e.g. refund-invoice-fraud)")
    parser.add_argument("--dry-run", action="store_true", help="Print manual steps only")
    args = parser.parse_args()

    preset = args.preset or preset_for_skill(args.skill) or "citation-curated"
    if args.dry_run:
        print(json.dumps({
            "skill": args.skill,
            "preset": preset,
            "workflow": ".github/workflows/official-skillsbench.yml",
            "env_required": ["GITHUB_TOKEN", "GITHUB_REPOSITORY", "DEEPSEEK_API_KEY (secret in repo)"],
        }, ensure_ascii=False, indent=2))
        return 0

    result = trigger_official_ci(args.skill, preset=preset or None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("ok"):
        return 0

    manual = result.get("manual") or {}
    print("\nManual trigger (GitHub CLI):", file=sys.stderr)
    print(
        f"  gh workflow run official-skillsbench.yml "
        f"-f run_agent_compare=true -f compare_preset={manual.get('compare_preset', preset)}",
        file=sys.stderr,
    )
    print("\nRequired repo secrets: DEEPSEEK_API_KEY", file=sys.stderr)
    print("Required env for API dispatch: GITHUB_TOKEN, GITHUB_REPOSITORY", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
