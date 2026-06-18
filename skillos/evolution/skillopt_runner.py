"""SkillOpt export validation and external runner helpers."""


import os
import shlex
import subprocess
from pathlib import Path
from typing import Any


def validate_bundle(export_dir: Path | str) -> dict[str, Any]:
    export_dir = Path(export_dir).resolve()
    if not export_dir.is_dir():
        raise FileNotFoundError(f"Export directory not found: {export_dir}")

    best = export_dir / "best_skill.md"
    manifest = export_dir / "manifest.json"
    traces = export_dir / "traces.jsonl"
    missing = [p.name for p in (best, manifest) if not p.exists()]
    trace_count = 0
    if traces.exists():
        trace_count = sum(1 for _ in traces.open(encoding="utf-8"))
    return {
        "ok": not missing,
        "export_dir": str(export_dir),
        "best_skill": str(best) if best.exists() else None,
        "manifest": str(manifest) if manifest.exists() else None,
        "traces": str(traces) if traces.exists() else None,
        "trace_count": trace_count,
        "missing": missing,
    }


def external_cmd_template() -> str:
    return os.getenv(
        "SKILLOPT_EXTERNAL_CMD",
        "python -m skillopt.run --skill {best_skill} --traces {traces}",
    )


def cli_help() -> dict[str, Any]:
    return {
        "script": "python scripts/skillopt_cli.py",
        "commands": {
            "export": "python scripts/skillopt_cli.py export <skill_name> [--output DIR]",
            "validate": "python scripts/skillopt_cli.py validate <export_dir>",
            "run": "python scripts/skillopt_cli.py run <skill_name> [--dry-run]",
        },
        "env": {
            "SKILLOPT_EXTERNAL_CMD": external_cmd_template(),
            "SKILLOPT_DRY_RUN": "Set to 1 to skip external runner",
        },
    }


def run_skillopt_external(
    skill_name: str,
    *,
    tenant=None,
    output_dir: Path | str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Export bundle and optionally invoke SKILLOPT_EXTERNAL_CMD."""
    from skillos.evolution.skillopt_export import export_for_skillopt

    result = export_for_skillopt(skill_name, output_dir=output_dir, tenant=tenant)
    validation = validate_bundle(result.export_dir)
    cmd_tpl = os.getenv("SKILLOPT_EXTERNAL_CMD", "").strip()
    skip_external = dry_run or os.getenv("SKILLOPT_DRY_RUN", "").lower() in ("1", "true", "yes")

    filled = ""
    if cmd_tpl:
        filled = cmd_tpl.format(
            export_dir=str(result.export_dir),
            best_skill=str(result.best_skill_path),
            traces=str(result.traces_path or ""),
            skill_name=skill_name,
        )

    external_rc: int | None = None
    if not skip_external and cmd_tpl:
        try:
            parts = shlex.split(filled, posix=os.name != "nt")
        except ValueError:
            parts = filled.split()
        proc = subprocess.run(parts, cwd=str(result.export_dir), capture_output=True, text=True)
        external_rc = proc.returncode
        validation["external_stdout"] = proc.stdout[-4000:] if proc.stdout else ""
        validation["external_stderr"] = proc.stderr[-4000:] if proc.stderr else ""

    return {
        "ok": validation["ok"],
        "dry_run": skip_external,
        "export": result.to_dict(),
        "validation": validation,
        "external_command": filled or None,
        "external_returncode": external_rc,
        "cli_hint": f"python scripts/skillopt_cli.py run {skill_name}" + (" --dry-run" if skip_external else ""),
    }
