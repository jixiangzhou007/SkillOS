"""Persistent DNA stats — philosophical stability + domain template versions."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

DNA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "dna"
PHILOSOPHICAL_STATS_PATH = DNA_DIR / "philosophical_stats.json"
DOMAIN_TEMPLATES_DIR = DNA_DIR / "domain_templates"

DEFAULT_TEMPLATE_VERSION = "1.0.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dirs() -> None:
    DNA_DIR.mkdir(parents=True, exist_ok=True)
    DOMAIN_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _log.warning("Failed to read %s: %s", path, exc)
        return dict(default)


def _save_json(path: Path, data: dict) -> None:
    _ensure_dirs()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_philosophical_stats() -> dict[str, Any]:
    """Load persisted philosophical DNA contribution stats."""
    return _load_json(PHILOSOPHICAL_STATS_PATH, {"methods": {}, "updated_at": ""})


def get_philosophical_stability(method_id: str, default: float = 0.75) -> float:
    stats = load_philosophical_stats()
    entry = stats.get("methods", {}).get(method_id, {})
    return float(entry.get("stability", default))


def get_template_version(template_id: str) -> str:
    path = DOMAIN_TEMPLATES_DIR / f"{template_id}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return str(data.get("version", DEFAULT_TEMPLATE_VERSION))
        except Exception:
            pass
    return DEFAULT_TEMPLATE_VERSION


def get_template_record(template_id: str) -> dict[str, Any]:
    path = DOMAIN_TEMPLATES_DIR / f"{template_id}.json"
    default = {
        "template_id": template_id,
        "version": DEFAULT_TEMPLATE_VERSION,
        "derived_from_skills": 0,
        "updated_at": "",
    }
    if path.exists():
        try:
            return {**default, **json.loads(path.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return default


def list_domain_template_versions() -> dict[str, str]:
    from skillos.skills.domain_templates import DOMAIN_TEMPLATES

    out: dict[str, str] = {}
    for tmpl in DOMAIN_TEMPLATES:
        out[tmpl.template_id] = get_template_version(tmpl.template_id)
    return out


def record_dna_contribution(
    skill_name: str,
    lineage: dict[str, Any],
    *,
    moe_score: int = 0,
) -> None:
    """Persist philosophical + domain DNA stats from a saved skill."""
    if moe_score < 70:
        return

    _ensure_dirs()
    now = _now_iso()

    # Philosophical stats
    stats = load_philosophical_stats()
    methods = stats.setdefault("methods", {})
    for entry in lineage.get("philosophical", []):
        mid = entry.get("id")
        if not mid:
            continue
        row = methods.setdefault(mid, {
            "derived_from_skills": 0,
            "stability": 0.75,
            "contributing_skills": [],
        })
        row["derived_from_skills"] = int(row.get("derived_from_skills", 0)) + 1
        row["stability"] = min(0.99, float(row.get("stability", 0.75)) + 0.01)
        skills = row.setdefault("contributing_skills", [])
        if skill_name not in skills:
            skills.append(skill_name)
            row["contributing_skills"] = skills[-50:]
    stats["updated_at"] = now
    _save_json(PHILOSOPHICAL_STATS_PATH, stats)

    # Domain template stats
    for entry in lineage.get("domain", []):
        tid = entry.get("id")
        if not tid:
            continue
        path = DOMAIN_TEMPLATES_DIR / f"{tid}.json"
        rec = get_template_record(tid)
        rec["derived_from_skills"] = int(rec.get("derived_from_skills", 0)) + 1
        rec["updated_at"] = now
        rec["version"] = entry.get("version") or rec.get("version", DEFAULT_TEMPLATE_VERSION)
        if skill_name not in rec.setdefault("contributing_skills", []):
            rec.setdefault("contributing_skills", []).append(skill_name)
            rec["contributing_skills"] = rec["contributing_skills"][-50:]
        _save_json(path, rec)

    # Sync in-memory philosophical DNA stability for runtime detect (best-effort)
    try:
        from skillos.knowledge.philosophical_dna import PHILOSOPHICAL_DNA
        for mid, row in methods.items():
            if mid in PHILOSOPHICAL_DNA:
                PHILOSOPHICAL_DNA[mid].derived_from_skills = int(row.get("derived_from_skills", 0))
                PHILOSOPHICAL_DNA[mid].stability = float(row.get("stability", PHILOSOPHICAL_DNA[mid].stability))
    except Exception:
        pass


def parse_lineage_from_meta(meta: dict[str, Any]) -> dict[str, Any] | None:
    raw = meta.get("dna_lineage")
    if isinstance(raw, dict) and raw:
        return raw
    return None


def backfill_skill_lineage(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Write dna_lineage into an existing SKILL.md if missing or stale."""
    from skillos.knowledge.dna_context import build_dna_lineage
    from skillos.skills.skill_store import _split_front_matter, _compose

    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    name = meta.get("name") or path.parent.name
    domain_tpl = meta.get("domain_template") or meta.get("domain_template_id")
    lineage = build_dna_lineage(name, body, domain_template_id=domain_tpl)
    changed = meta.get("dna_lineage") != lineage
    if changed and not dry_run:
        meta["dna_lineage"] = lineage
        if not meta.get("philosophical_dna") and lineage.get("philosophical"):
            meta["philosophical_dna"] = lineage["philosophical"][0]["id"]
        if not meta.get("domain") and lineage.get("domain_key"):
            meta["domain"] = lineage["domain_key"]
        path.write_text(_compose(meta, body), encoding="utf-8")
    return {"path": str(path), "name": name, "changed": changed, "lineage": lineage}
