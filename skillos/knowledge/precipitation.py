"""Unified source precipitation — additive orchestration over existing pipelines.

This module does not replace API endpoints or agent logic. It centralizes the
*same* call sequence used by HTTP ingest so background queue workers cannot
silently skip skill persistence.

Rollback: set ``SKILLOS_PRECIPITATION_LEGACY_QUEUE=1`` to restore the pre-fix
queue URL-skill path (lineage only, no disk persist).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


def legacy_queue_enabled() -> bool:
    """When true, queue actionable-URL tasks skip full skill persist (old behavior)."""
    return os.environ.get("SKILLOS_PRECIPITATION_LEGACY_QUEUE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


@dataclass
class SkillPrecipitationResult:
    """Outcome of actionable source → skill precipitation."""

    skill_name: str | None = None
    reply: str = ""
    doc: dict | None = None
    epistemic_summary: dict | None = None
    lineage_applied: bool = False
    persisted: bool = False
    warnings: list[str] = field(default_factory=list)

    def queue_message(self) -> str:
        if not self.skill_name:
            return "skill:no_doc"
        lineage = "yes" if self.lineage_applied else "no"
        persist = "persisted" if self.persisted else "lineage_only"
        return f"skill:{self.skill_name}:lineage={lineage}:{persist}"


def _default_skill_list() -> list[str]:
    from skillos.skills.skill_store import list_skills

    return list_skills()


def learn_skill_from_source(
    source_uri: str,
    content: str,
    llm_args: tuple,
    *,
    existing_skills: list[str] | None = None,
) -> tuple[str, dict | None]:
    """Run the existing 7-step URL learning pipeline (no behavior change)."""
    from skillos.skills.agent import SkillExtractionAgent

    skills = existing_skills if existing_skills is not None else _default_skill_list()
    agent = SkillExtractionAgent()
    return agent.learn_from_url(source_uri, content, skills, llm_args)


def persist_skill_document(
    doc: dict,
    source_uri: str,
    llm_args: tuple,
    *,
    channel: str = "precipitation",
    team_context: dict | None = None,
    source_type: str = "url_content",
) -> dict:
    """Full skill persist — same path as ``POST /api/skills/ingest`` actionable branch."""
    from skillos.api.skills_extract import _persist_created_skill

    ctx = dict(team_context or {})
    ctx.setdefault("channel", channel)
    return _persist_created_skill(
        doc["name"],
        doc["content"],
        llm_args,
        source=source_uri,
        source_type=source_type,
        team_context=ctx,
    )


def finalize_skill_lineage_only(
    doc: dict,
    source_uri: str,
    *,
    channel: str = "ingestion_queue",
) -> dict:
    """Legacy queue exit: lineage graph update without writing SKILL.md to disk."""
    from skillos.knowledge.ingest_pipeline import finalize_ingest

    return finalize_ingest(
        doc["content"],
        source_uri,
        skill_name=doc["name"],
        skill_body=doc["content"],
        sync_graph=False,
        channel=channel,
    )


def precipitate_actionable_source(
    source_uri: str,
    content: str,
    llm_args: tuple,
    *,
    channel: str = "ingestion_queue",
    team_context: dict | None = None,
    existing_skills: list[str] | None = None,
    persist_skill: bool | None = None,
) -> SkillPrecipitationResult:
    """Actionable material → skill doc → persist (or legacy lineage-only).

    ``persist_skill`` defaults to ``not legacy_queue_enabled()``.
    """
    if persist_skill is None:
        persist_skill = not legacy_queue_enabled()

    reply, doc = learn_skill_from_source(
        source_uri, content, llm_args, existing_skills=existing_skills,
    )
    result = SkillPrecipitationResult(reply=reply, doc=doc)

    if not doc:
        return result

    result.skill_name = doc.get("name")

    if persist_skill:
        try:
            ep = persist_skill_document(
                doc,
                source_uri,
                llm_args,
                channel=channel,
                team_context=team_context,
            )
            result.epistemic_summary = ep
            result.lineage_applied = bool((ep.get("lineage") or {}).get("lineage_applied"))
            result.persisted = True
        except Exception as exc:
            _log.warning(
                "Full skill persist failed for %s (%s); falling back to lineage-only",
                source_uri[:80],
                exc,
            )
            result.warnings.append(f"persist_failed:{exc}")
            try:
                fin = finalize_skill_lineage_only(doc, source_uri, channel=channel)
                result.lineage_applied = bool((fin.get("lineage") or {}).get("lineage_applied"))
            except Exception as exc2:
                _log.warning("Lineage fallback also failed: %s", exc2)
                result.warnings.append(f"lineage_failed:{exc2}")
    else:
        try:
            fin = finalize_skill_lineage_only(doc, source_uri, channel=channel)
            result.lineage_applied = bool((fin.get("lineage") or {}).get("lineage_applied"))
        except Exception as exc:
            _log.warning("Legacy lineage-only path failed: %s", exc)
            result.warnings.append(f"lineage_failed:{exc}")

    return result


def precipitate_conceptual_source(
    content: str,
    source_uri: str,
    llm_args: tuple,
    *,
    channel: str = "ingestion_queue",
) -> dict[str, Any]:
    """Conceptual material → deep digest + knowledge extraction + lineage (unchanged logic)."""
    from skillos.knowledge.deep_digest import deep_digest, save_digest
    from skillos.knowledge.ingest_pipeline import finalize_ingest

    dd = deep_digest(content, source_uri, llm_args=llm_args)
    extracted_items: list = []
    if dd.glossary or dd.patterns or dd.sections:
        save_digest(dd)
        try:
            from skillos.knowledge.extractor import extract_knowledge, save_knowledge

            extracted_items = extract_knowledge(content, source_uri, llm_args)
            if extracted_items:
                save_knowledge(extracted_items)
        except Exception:
            _log.debug("extract_knowledge skipped", exc_info=True)

    fin = finalize_ingest(
        content,
        source_uri,
        source_title=dd.title,
        digest_result=dd if (dd.glossary or dd.patterns or dd.sections) else None,
        extractor_items=extracted_items or None,
        channel=channel,
    )
    lineage_ok = (fin.get("lineage") or {}).get("lineage_applied")
    return {
        "title": dd.title,
        "lineage_applied": bool(lineage_ok),
        "finalize": fin,
    }
