"""Unified post-ingest hook — digest / extract / skill → lineage 4-signal graph."""


import logging
import re
import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from skillos.knowledge.deep_digest import DigestResult

_log = logging.getLogger(__name__)


def _source_chunk(source_url: str, content: str = "", source_type: str = "url"):
    from skillos.knowledge.lineage import SourceChunk

    if source_url.startswith("file://"):
        source_type = "file"
    elif source_url.startswith("skill://"):
        source_type = "conversation"
    return SourceChunk(
        chunk_id=f"src_{uuid.uuid4().hex[:8]}",
        source_url=source_url,
        source_type=source_type,
        raw_text=content[:500] if content else "",
    )


def _new_item_id() -> str:
    return f"ki_{uuid.uuid4().hex[:8]}"


def items_from_digest(
    digest_result: DigestResult,
    source_url: str,
    content: str = "",
) -> list:
    """Convert deep digest artifacts to lineage KnowledgeItem objects."""
    from skillos.knowledge.lineage import KnowledgeItem

    chunk = _source_chunk(source_url, content)
    now = time.time()
    items: list = []

    for term in digest_result.glossary:
        items.append(KnowledgeItem(
            item_id=_new_item_id(),
            content=f"{term.get('term', '')}: {term.get('definition', '')}",
            category="concept",
            confidence=0.8,
            epistemic_level="knowledge",
            source_chunk=chunk,
            created_at=now,
            last_accessed=now,
        ))

    for pattern in digest_result.patterns:
        items.append(KnowledgeItem(
            item_id=_new_item_id(),
            content=f"{pattern.get('name', '')}: {pattern.get('description', '')}",
            category="heuristic",
            confidence=0.7,
            epistemic_level="experience",
            source_chunk=chunk,
            created_at=now,
            last_accessed=now,
        ))

    for section in digest_result.sections:
        heading = section.get("heading", "")
        summary = section.get("summary", "")
        if summary:
            items.append(KnowledgeItem(
                item_id=_new_item_id(),
                content=f"{heading}: {summary}" if heading else summary,
                category="fact",
                confidence=0.6,
                epistemic_level="knowledge",
                source_chunk=chunk,
                created_at=now,
                last_accessed=now,
            ))

    skill_refs = [
        {
            "skill_name": xref["skill_name"],
            "score_delta": 0.5,
            "timestamp": now,
        }
        for xref in (digest_result.cross_references or [])
        if xref.get("skill_name")
    ]
    if skill_refs:
        for item in items:
            item.affected_skills.extend(skill_refs)

    return items


def items_from_extractor(extractor_items: list, source_url: str, content: str = "") -> list:
    """Convert flat extractor KnowledgeItem objects to lineage items."""
    from skillos.knowledge.lineage import KnowledgeItem

    chunk = _source_chunk(source_url, content)
    now = time.time()
    items: list = []

    for raw in extractor_items:
        category = raw.category if raw.category in ("fact", "concept", "heuristic", "pattern") else "fact"
        items.append(KnowledgeItem(
            item_id=raw.item_id or _new_item_id(),
            content=raw.content,
            category=category,
            confidence=raw.confidence,
            epistemic_level="knowledge" if raw.confidence >= 0.7 else "experience",
            source_chunk=chunk,
            created_at=raw.created_at or now,
            last_accessed=now,
        ))

    return items


def items_from_skill(skill_name: str, body: str, source_url: str = "") -> list:
    """Create a lineage item representing a precipitated skill."""
    from skillos.knowledge.lineage import KnowledgeItem

    core = ""
    m = re.search(r"##\s*核心问题\s*\n(.+?)(?:\n##|\Z)", body, re.DOTALL | re.IGNORECASE)
    if m:
        core = m.group(1).strip().split("\n")[0][:200]
    if not core:
        core = body.strip().replace("\n", " ")[:200]

    now = time.time()
    url = source_url or f"skill://{skill_name}"
    return [KnowledgeItem(
        item_id=_new_item_id(),
        content=f"技能「{skill_name}」: {core}",
        category="heuristic",
        confidence=0.75,
        epistemic_level="knowledge",
        source_chunk=_source_chunk(url, body),
        affected_skills=[{
            "skill_name": skill_name,
            "score_delta": 1.0,
            "timestamp": now,
        }],
        created_at=now,
        last_accessed=now,
    )]


def post_ingest(
    content: str,
    source_url: str,
    *,
    source_title: str = "",
    digest_result: DigestResult | None = None,
    extractor_items: list | None = None,
    skill_name: str = "",
    skill_body: str = "",
    sync_graph: bool = True,
    channel: str = "",
) -> dict[str, Any]:
    """Run lineage 4-signal cross-ref after knowledge ingestion."""
    from skillos.knowledge.lineage import append_items_to_lineage

    lineage_items: list = []
    if digest_result is not None:
        lineage_items.extend(items_from_digest(digest_result, source_url, content))
    if extractor_items:
        lineage_items.extend(items_from_extractor(extractor_items, source_url, content))
    if skill_name and skill_body:
        lineage_items.extend(items_from_skill(skill_name, skill_body, source_url))

    if not lineage_items:
        result = {
            "lineage_applied": False,
            "reason": "no_items",
            "channel": channel,
        }
        try:
            from skillos.knowledge.ingest_metrics import record_ingest_event
            record_ingest_event(channel=channel, source_url=source_url, lineage=result)
        except Exception:
            pass
        return result

    try:
        result = append_items_to_lineage(
            lineage_items,
            source_url=source_url,
            source_title=source_title or source_url,
            sync_graph=sync_graph,
        )
        result["lineage_applied"] = True
        result["channel"] = channel
        try:
            from skillos.knowledge.ingest_metrics import record_ingest_event
            record_ingest_event(channel=channel, source_url=source_url, lineage=result)
        except Exception:
            pass
        return result
    except Exception as exc:
        _log.warning("post_ingest lineage failed for %s: %s", source_url[:80], exc)
        result = {
            "lineage_applied": False,
            "reason": str(exc),
            "channel": channel,
        }
        try:
            from skillos.knowledge.ingest_metrics import record_ingest_event
            record_ingest_event(channel=channel, source_url=source_url, lineage=result)
        except Exception:
            pass
        return result


def format_lineage_notice(lineage: dict | None) -> str:
    """Human-readable lineage outcome for API replies and UI toasts."""
    if not lineage:
        return "⚠ 血缘未记录"
    if lineage.get("lineage_applied"):
        parts = [f"✓ 血缘已关联 {lineage.get('items_added', 0)} 条知识"]
        edges = lineage.get("edges_created", 0)
        if edges:
            parts.append(f"{edges} 条交叉引用")
        session_id = lineage.get("session_id", "")
        if session_id:
            parts.append(f"会话 {session_id[:16]}")
        return " · ".join(parts)
    reason = lineage.get("reason", "unknown")
    if reason == "no_items":
        return "ℹ 未提取到可写入血缘的条目（内容可能过短）"
    return f"⚠ 血缘写入失败：{reason}"


def enrich_with_lineage(payload: dict, lineage: dict | None) -> dict:
    """Attach lineage block and user-visible warnings to an ingest API payload."""
    if lineage is None:
        payload.setdefault("warnings", []).append(format_lineage_notice(None))
        return payload
    payload["lineage"] = lineage
    notice = format_lineage_notice(lineage)
    payload["lineage_notice"] = notice
    if not lineage.get("lineage_applied"):
        warnings = payload.setdefault("warnings", [])
        if notice not in warnings:
            warnings.append(notice)
    return payload


def finalize_ingest(
    content: str,
    source_url: str,
    *,
    source_title: str = "",
    digest_result: DigestResult | None = None,
    extractor_items: list | None = None,
    skill_name: str = "",
    skill_body: str = "",
    sync_graph: bool = True,
    channel: str = "",
    payload: dict | None = None,
) -> dict[str, Any]:
    """Unified ingestion exit — lineage, user notices, and metrics in one call."""
    out = dict(payload or {})
    try:
        lineage = post_ingest(
            content,
            source_url,
            source_title=source_title,
            digest_result=digest_result,
            extractor_items=extractor_items,
            skill_name=skill_name,
            skill_body=skill_body,
            sync_graph=sync_graph,
            channel=channel,
        )
    except Exception as exc:
        _log.warning("finalize_ingest failed for %s: %s", source_url[:80], exc)
        lineage = {"lineage_applied": False, "reason": str(exc), "channel": channel}
        try:
            from skillos.knowledge.ingest_metrics import record_ingest_event
            record_ingest_event(channel=channel, source_url=source_url, lineage=lineage)
        except Exception:
            pass
    out = enrich_with_lineage(out, lineage)
    if (
        source_url
        and content
        and not skill_name
        and source_url.startswith(("http://", "https://", "file://"))
    ):
        try:
            from skillos.knowledge.ingest_dedup import mark_ingest_complete
            mark_ingest_complete(source_url, content)
        except Exception:
            pass
    return out


def run_full_knowledge_cycle(
    content: str,
    source_url: str,
    llm_args: tuple,
    *,
    existing_skills: list[str] | None = None,
) -> dict:
    """Public entry for the complete SD knowledge cycle (digest → lineage → wisdom)."""
    from skillos.knowledge.lineage import full_knowledge_cycle

    return full_knowledge_cycle(
        content,
        source_url,
        llm_args,
        existing_skills=existing_skills,
    )
