#!/usr/bin/env python3
"""Copy a SkillOS skill into a local harness skills directory.

Targets (DeepSeek Harness–style discovery roots):
  cursor   → ~/.cursor/skills/<slug>/
  agents   → .agents/skills/<slug>/  (cwd project) or ~/.agents/skills/
  dsh      → ~/.dsh/skills/<slug>/   (or --project → .dsh/skills/)

Usage:
  python scripts/install_skill_to_harness.py "GitHub Pull" --target cursor
  python scripts/install_skill_to_harness.py "GitHub Pull" --target dsh
  python scripts/install_skill_to_harness.py "GitHub Pull" --target agents --project
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Install SkillOS skill into a harness folder")
    parser.add_argument("name", help="Skill display name as stored in SkillOS")
    parser.add_argument(
        "--target",
        choices=("cursor", "agents", "dsh"),
        default="cursor",
        help="Harness install root",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Use project .agents/.dsh instead of user home (agents/dsh only)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    from skillos.skills.harness_install import install_skill_to_harness

    result = install_skill_to_harness(args.name, target=args.target, project=args.project)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Installed → {result['path']}")
        print(f"  Trust Tier: {result['trust_tier']} · model_invocable={result['model_invocable']}")
        if result.get("hint"):
            print(f"  Try: {result['hint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
