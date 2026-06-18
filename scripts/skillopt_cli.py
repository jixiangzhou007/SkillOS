#!/usr/bin/env python3
"""SkillOpt CLI — export SkillOS skills for external Microsoft SkillOpt-style runners."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def cmd_export(skill_name: str, output: str | None) -> int:
    from skillos.evolution.skillopt_export import export_for_skillopt
    from skillos.evolution.skillopt_runner import validate_bundle

    out = Path(output).expanduser() if output else None
    result = export_for_skillopt(skill_name, output_dir=out)
    print(f"Exported: {result.export_dir}")
    print(f"  best_skill.md  -> {result.best_skill_path}")
    if result.traces_path:
        print(f"  traces.jsonl   -> {result.traces_path}")
    print(f"  manifest.json  -> {result.manifest_path}")
    validation = validate_bundle(result.export_dir)
    print(f"Validate: {'OK' if validation['ok'] else 'FAIL ' + str(validation['missing'])}")
    return 0 if validation["ok"] else 1


def cmd_validate(export_dir: str) -> int:
    from skillos.evolution.skillopt_runner import validate_bundle

    try:
        info = validate_bundle(export_dir)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"Directory: {info['export_dir']}")
    print(f"best_skill: {info['best_skill']}")
    print(f"manifest:   {info['manifest']}")
    print(f"traces:     {info['traces']} ({info['trace_count']} lines)")
    if info["missing"]:
        print(f"Missing:    {', '.join(info['missing'])}", file=sys.stderr)
        return 1
    print("Validation: OK")
    return 0


def cmd_run(skill_name: str, dry_run: bool) -> int:
    from skillos.evolution.skillopt_runner import cli_help, run_skillopt_external

    result = run_skillopt_external(skill_name, dry_run=dry_run)
    if not result["ok"]:
        print(f"Export validation failed: {result['validation'].get('missing')}", file=sys.stderr)
        return 1
    if dry_run:
        print("[dry-run] Export ready at:", result["export"]["export_dir"])
        print("Suggested command:", result.get("external_command") or cli_help()["env"]["SKILLOPT_EXTERNAL_CMD"])
        return 0
    if result["external_returncode"] is None:
        print("Set SKILLOPT_EXTERNAL_CMD to invoke external SkillOpt runner.", file=sys.stderr)
        print("Example:", cli_help()["env"]["SKILLOPT_EXTERNAL_CMD"], file=sys.stderr)
        return 2
    return int(result["external_returncode"])


def main() -> int:
    parser = argparse.ArgumentParser(description="SkillOpt export & external runner CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="Export skill bundle for SkillOpt")
    p_export.add_argument("skill_name")
    p_export.add_argument("--output", "-o", default="", help="Export root directory")

    p_validate = sub.add_parser("validate", help="Validate an export directory")
    p_validate.add_argument("export_dir")

    p_run = sub.add_parser("run", help="Export then run external SkillOpt (if configured)")
    p_run.add_argument("skill_name")
    p_run.add_argument("--dry-run", action="store_true", help="Export + print command only")

    args = parser.parse_args()
    if args.command == "export":
        return cmd_export(args.skill_name, args.output or None)
    if args.command == "validate":
        return cmd_validate(args.export_dir)
    if args.command == "run":
        return cmd_run(args.skill_name, args.dry_run)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
