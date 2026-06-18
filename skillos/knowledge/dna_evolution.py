"""Domain DNA evolution + stale lineage queue (Phase 4)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillos.knowledge.dna_semver import bump_semver, compare_semver, is_stale_version
from skillos.knowledge.dna_store import (
    DEFAULT_TEMPLATE_VERSION,
    DNA_DIR,
    _ensure_dirs,
    _load_json,
    _now_iso,
    _save_json,
    get_template_record,
    get_template_version,
)

_log = logging.getLogger(__name__)

STALE_QUEUE_PATH = DNA_DIR / "stale_queue.json"
_EVOLUTION_STEP_RE = re.compile(r"^\s*\d+\.\s+(.+)$")


def _extract_skill_steps(skill_content: str) -> list[str]:
    """Pull numbered steps from Instructions / S_body blocks."""
    if not skill_content:
        return []
    lines = skill_content.splitlines()
    steps: list[str] = []
    active = False
    for line in lines:
        if re.match(r"^##\s+(Instructions|S_body|S body)\b", line, re.I):
            active = True
            continue
        if active and re.match(r"^##\s+", line):
            if steps:
                break
            continue
        m = _EVOLUTION_STEP_RE.match(line)
        if m and active:
            text = m.group(1).strip()
            if len(text) >= 8:
                steps.append(text[:240])
    if not steps:
        for line in lines:
            m = _EVOLUTION_STEP_RE.match(line)
            if m:
                text = m.group(1).strip()
                if len(text) >= 8:
                    steps.append(text[:240])
    return steps[:12]


def _is_novel_step(step: str, known: list[str]) -> bool:
    lowered = step.lower()
    for k in known:
        if lowered == k.lower():
            return False
        if len(lowered) > 20 and (lowered in k.lower() or k.lower() in lowered):
            return False
    return True


def evolve_domain_template_record(
    template_id: str,
    skill_name: str,
    skill_content: str,
    skill_score: int,
) -> dict[str, Any]:
    """Merge high-score skill steps into persisted template DNA; bump semver."""
    if skill_score < 70:
        return {"evolved": False, "reason": "score_below_threshold"}

    from skillos.skills.domain_templates import get_template

    if not get_template(template_id):
        return {"evolved": False, "reason": "unknown_template"}

    steps = _extract_skill_steps(skill_content)
    rec = get_template_record(template_id)
    learned: list[str] = list(rec.get("learned_steps") or [])
    novel = [s for s in steps if _is_novel_step(s, learned)]
    if not novel:
        return {
            "evolved": False,
            "reason": "no_novel_steps",
            "version": rec.get("version", DEFAULT_TEMPLATE_VERSION),
        }

    learned.extend(novel)
    rec["learned_steps"] = learned[-30:]
    overlay_lines = list(rec.get("skeleton_overlay_lines") or [])
    for step in novel:
        line = f"- {step}"
        if line not in overlay_lines:
            overlay_lines.append(line)
    rec["skeleton_overlay_lines"] = overlay_lines[-20:]
    rec["skeleton_overlay"] = "\n".join(rec["skeleton_overlay_lines"])

    version = str(rec.get("version", DEFAULT_TEMPLATE_VERSION))
    bump = "patch"
    if len(novel) >= 2 or skill_score >= 85:
        bump = "minor"
    new_version = bump_semver(version, bump)
    rec["version"] = new_version
    rec["updated_at"] = _now_iso()
    rec["template_id"] = template_id

    log = list(rec.get("evolution_log") or [])
    log.append({
        "at": rec["updated_at"],
        "skill": skill_name,
        "score": skill_score,
        "bump": bump,
        "from_version": version,
        "to_version": new_version,
        "novel_steps": len(novel),
    })
    rec["evolution_log"] = log[-30:]

    _ensure_dirs()
    _save_json(DNA_DIR / "domain_templates" / f"{template_id}.json", rec)
    _log.info(
        "Domain DNA evolved: %s %s→%s (%d novel steps, score=%d)",
        template_id, version, new_version, len(novel), skill_score,
    )
    return {
        "evolved": True,
        "template_id": template_id,
        "from_version": version,
        "to_version": new_version,
        "bump": bump,
        "novel_steps": novel,
    }


def get_template_generation_boost(template_id: str, base_skeleton: str) -> str:
    """Base skeleton + persisted evolution overlay."""
    rec = get_template_record(template_id)
    overlay = (rec.get("skeleton_overlay") or "").strip()
    if not overlay:
        return base_skeleton
    version = rec.get("version", DEFAULT_TEMPLATE_VERSION)
    return (
        f"{base_skeleton}\n\n"
        f"## 进化补充（模板 v{version}，来自高分技能聚合）\n"
        f"{overlay}\n"
    )


def load_stale_queue() -> dict[str, Any]:
    return _load_json(STALE_QUEUE_PATH, {"items": [], "updated_at": ""})


def save_stale_queue(items: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {"items": items, "updated_at": _now_iso(), "count": len(items)}
    _ensure_dirs()
    _save_json(STALE_QUEUE_PATH, payload)
    return payload


def scan_stale_lineage_skills(skills_dir: Path | None = None) -> list[dict[str, Any]]:
    """Find skills whose dna_lineage domain version lags current template semver."""
    from skillos.skills.skill_store import _split_front_matter, get_skills_dir

    root = skills_dir or get_skills_dir()
    stale: list[dict[str, Any]] = []
    if not root.exists():
        return stale

    for path in sorted(root.glob("*/SKILL.md")):
        try:
            meta, _ = _split_front_matter(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = meta.get("name") or path.parent.name
        lineage = meta.get("dna_lineage") or {}
        outdated: list[dict[str, str]] = []
        for entry in lineage.get("domain") or []:
            tid = entry.get("id")
            if not tid:
                continue
            recorded = str(entry.get("version") or DEFAULT_TEMPLATE_VERSION)
            current = get_template_version(tid)
            if is_stale_version(recorded, current):
                outdated.append({
                    "template_id": tid,
                    "recorded_version": recorded,
                    "current_version": current,
                })
        if outdated:
            stale.append({
                "skill": name,
                "path": str(path),
                "outdated_templates": outdated,
                "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
    stale.sort(key=lambda x: x["skill"])
    return stale


def refresh_stale_queue(skills_dir: Path | None = None) -> dict[str, Any]:
    items = scan_stale_lineage_skills(skills_dir)
    return save_stale_queue(items)


def relink_skill_lineage(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Refresh dna_lineage domain versions to current template semver."""
    from skillos.knowledge.dna_store import backfill_skill_lineage

    before = scan_stale_lineage_skills(path.parent.parent)
    row = backfill_skill_lineage(path, dry_run=dry_run)
    after_stale = False
    if not dry_run:
        remaining = scan_stale_lineage_skills(path.parent.parent)
        after_stale = any(r["path"] == str(path) for r in remaining)
    return {**row, "was_stale": any(r["path"] == str(path) for r in before), "still_stale": after_stale}


def process_stale_queue(*, dry_run: bool = False, limit: int = 50) -> dict[str, Any]:
    """Re-backfill all queued stale skills."""
    queue = refresh_stale_queue()
    processed: list[dict[str, Any]] = []
    for item in queue.get("items", [])[:limit]:
        path = Path(item["path"])
        if not path.exists():
            continue
        result = relink_skill_lineage(path, dry_run=dry_run)
        processed.append({
            "skill": item["skill"],
            "changed": result.get("changed"),
            "still_stale": result.get("still_stale"),
        })
    if not dry_run:
        refresh_stale_queue()
    return {
        "queued": len(queue.get("items", [])),
        "processed": len(processed),
        "results": processed,
    }
