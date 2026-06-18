"""Export SkillOS skills for Microsoft SkillOpt-compatible training loops.

SkillOS native optimization lives in ``skillos.evolution.skillopt``; this module
produces a portable directory that external SkillOpt tooling (or manual review)
can consume as a ``best_skill.md`` + traces entry point.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_EXPORT_ROOT = Path(__file__).parent.parent.parent / "data" / "exports" / "skillopt"


@dataclass
class SkillOptExportResult:
    skill_name: str
    export_dir: Path
    best_skill_path: Path
    skill_path: Path
    traces_path: Path | None
    manifest_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "export_dir": str(self.export_dir),
            "best_skill_path": str(self.best_skill_path),
            "skill_path": str(self.skill_path),
            "traces_path": str(self.traces_path) if self.traces_path else None,
            "manifest_path": str(self.manifest_path),
        }


def export_for_skillopt(
    skill_name: str,
    output_dir: Path | str | None = None,
    *,
    include_traces: bool = True,
    tenant=None,
) -> SkillOptExportResult:
    """Export a skill bundle for SkillOpt-style optimization.

    Creates::

        {export_dir}/{skill_name}-skillopt/
          best_skill.md   # primary trainable document
          skill.md        # identical copy (SkillOpt alias)
          traces.jsonl    # execution traces (if any)
          manifest.json   # epistemic + export metadata
          README.md       # usage notes

    Returns:
        SkillOptExportResult with paths to generated files.
    """
    from skillos.skills.skill_store import load_skill, load_skill_raw
    from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload

    raw = load_skill_raw(skill_name, tenant=tenant)
    full_doc = load_skill(skill_name, tenant=tenant)
    body = raw.get("body") or full_doc
    meta = raw.get("meta") or {}
    ep = format_epistemic_api_payload(meta)

    safe = re.sub(r'[<>:"/\\|?*]', "_", skill_name)[:64]
    root = Path(output_dir) if output_dir else DEFAULT_EXPORT_ROOT
    export_dir = root / f"{safe}-skillopt"
    export_dir.mkdir(parents=True, exist_ok=True)

    best_path = export_dir / "best_skill.md"
    skill_path = export_dir / "skill.md"
    best_path.write_text(full_doc if full_doc.strip().startswith("---") else body, encoding="utf-8")
    skill_path.write_text(best_path.read_text(encoding="utf-8"), encoding="utf-8")

    traces_path: Path | None = None
    traces: list[dict] = []
    if include_traces:
        from skillos.evolution.skillopt import collect_traces

        traces = collect_traces(skill_name)
        if traces:
            traces_path = export_dir / "traces.jsonl"
            with traces_path.open("w", encoding="utf-8") as f:
                for t in traces:
                    f.write(json.dumps(t, ensure_ascii=False) + "\n")

    manifest = {
        "skill_name": skill_name,
        "exported_at": time.time(),
        "source": "skillos.export_for_skillopt",
        "version": meta.get("version", 1),
        "epistemic_summary": ep,
        "trace_count": len(traces) if include_traces and traces_path else 0,
        "skillos_native_optimize": f"POST /api/evolution/{skill_name}/optimize",
    }
    manifest_path = export_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = export_dir / "README.md"
    readme.write_text(
        f"# SkillOpt Export: {skill_name}\n\n"
        f"- **best_skill.md** — trainable skill document (edit budget optimization target)\n"
        f"- **traces.jsonl** — execution feedback ({manifest['trace_count']} traces)\n"
        f"- **manifest.json** — epistemic summary + provenance\n\n"
        "## SkillOS native optimization\n\n"
        f"```bash\n"
        f"curl -X POST http://127.0.0.1:9876/api/evolution/{skill_name}/optimize\n"
        f"```\n\n"
        "## External SkillOpt (Microsoft)\n\n"
        "Point your SkillOpt runner at `best_skill.md` and `traces.jsonl` in this directory.\n"
        "SkillOS epistemology layer should gate which claims are trusted before cross-skill diffusion.\n",
        encoding="utf-8",
    )

    return SkillOptExportResult(
        skill_name=skill_name,
        export_dir=export_dir,
        best_skill_path=best_path,
        skill_path=skill_path,
        traces_path=traces_path,
        manifest_path=manifest_path,
    )
