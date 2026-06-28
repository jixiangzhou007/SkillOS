"""Knowledge Lineage — core logic: cross-references, surprise detection, persistence."""

import hashlib
import json
import logging
import re
import time
from pathlib import Path

from .lineage_graph import LineageGraph
from .lineage_types import LINEAGE_DIR, KnowledgeItem, SourceChunk

_log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Surprise Detection
# ═══════════════════════════════════════════════════════════════

def detect_surprise(new_item: KnowledgeItem, existing_items: list[KnowledgeItem]) -> list[dict]:
    """Detect if new knowledge surprises (contradicts or significantly extends) existing knowledge.

    Surprise types:
    - contradiction: new item directly conflicts with existing belief
    - extension: new item adds a dimension not covered by existing knowledge
    - confirmation: new item corroborates existing knowledge (not surprising)
    - anomaly: new item is unrelated to anything in the knowledge base
    """
    surprises = []

    for existing in existing_items:
        overlap = _text_similarity(new_item.content, existing.content)

        if overlap > 0.7:
            # High overlap — check for contradiction
            if _are_contradictory(new_item.content, existing.content):
                # Graphiti-style temporal edge invalidation: OLD fact → mark invalid
                existing.invalid_at = time.time()
                existing.epistemic_level = "superseded"
                existing.superseded_by = new_item.item_id
                new_item.valid_at = time.time()
                new_item.contradicted_by.append(existing.item_id)
                surprises.append({
                    "type": "contradiction",
                    "new_item": new_item.item_id,
                    "existing_item": existing.item_id,
                    "existing_content": existing.content[:100],
                    "overlap": round(overlap, 2),
                    "action": "invalidated_old_fact",
                    "detail": f"旧事实已标记失效 (invalid_at={existing.invalid_at:.0f})，新事实为当前有效版本",
                })
            else:
                surprises.append({
                    "type": "confirmation",
                    "new_item": new_item.item_id,
                    "existing_item": existing.item_id,
                    "overlap": round(overlap, 2),
                    "action": "reinforce_both",
                })
                new_item.confidence = min(1.0, new_item.confidence + 0.1)
                new_item.verified_by.append(existing.item_id)
        elif overlap < 0.05 and existing.category == new_item.category:
            surprises.append({
                "type": "anomaly",
                "new_item": new_item.item_id,
                "note": f"New {new_item.category} unrelated to existing knowledge in same category",
            })

    if not surprises:
        surprises.append({"type": "novel", "note": "No existing knowledge in this domain"})

    return surprises


def _text_similarity(a: str, b: str) -> float:
    """Simple word overlap similarity."""
    words_a = set(re.findall(r'[\w一-鿿]{2,}', a.lower()))
    words_b = set(re.findall(r'[\w一-鿿]{2,}', b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a | words_b), 1)


def _are_contradictory(a: str, b: str) -> bool:
    """Heuristic contradiction detection using negation and opposing numbers."""
    # Check for negation in one but not the other
    neg_words = ['not', 'never', 'cannot', 'should not', "don't", '避免', '不要', '不能', '禁止']
    a_neg = any(w in a.lower() for w in neg_words)
    b_neg = any(w in b.lower() for w in neg_words)
    if a_neg != b_neg:
        return True

    # Check for opposing numerical claims
    nums_a = set(re.findall(r'\d+\.?\d*', a))
    nums_b = set(re.findall(r'\d+\.?\d*', b))
    if nums_a and nums_b and nums_a != nums_b:
        return True

    return False


# ═══════════════════════════════════════════════════════════════
# 4-signal cross-reference (LLM Wiki model)
# ═══════════════════════════════════════════════════════════════

_CROSSREF_THRESHOLD = 0.25
_SIGNAL_CONTENT = 3.0
_SIGNAL_SAME_SOURCE = 4.0
_SIGNAL_SHARED_SKILLS = 2.0
_SIGNAL_SAME_CATEGORY = 1.5
_SIGNAL_TOTAL = _SIGNAL_CONTENT + _SIGNAL_SAME_SOURCE + _SIGNAL_SAME_CATEGORY + _SIGNAL_SHARED_SKILLS


def _association_weight(item1: KnowledgeItem, item2: KnowledgeItem) -> tuple[float, str] | None:
    """Score a pair with 4 weighted signals; return (weight, relation_type) or None."""
    w1 = set(re.findall(r'[\w一-鿿]{3,}', item1.content.lower()))
    w2 = set(re.findall(r'[\w一-鿿]{3,}', item2.content.lower()))
    shared_words = len(w1 & w2)
    if shared_words < 2:
        return None

    score = min(1.0, shared_words / max(len(w1), len(w2), 1))
    same_source = (
        item1.source_chunk is not None
        and item2.source_chunk is not None
        and item1.source_chunk.source_url == item2.source_chunk.source_url
    )
    same_cat = item1.category == item2.category
    shared_skills = bool(
        set(a["skill_name"] for a in item1.affected_skills)
        & set(a["skill_name"] for a in item2.affected_skills)
    )

    weighted = score * _SIGNAL_CONTENT
    if same_source:
        weighted += _SIGNAL_SAME_SOURCE
    if same_cat:
        weighted += _SIGNAL_SAME_CATEGORY
    if shared_skills:
        weighted += _SIGNAL_SHARED_SKILLS

    final_weight = min(1.0, weighted / _SIGNAL_TOTAL)
    if final_weight <= _CROSSREF_THRESHOLD:
        return None

    rel_type = (
        "same_source" if same_source
        else ("linked" if shared_skills else "related")
    )
    return final_weight, rel_type


def build_cross_references(items: list[KnowledgeItem]) -> int:
    """Apply 4-signal weighted association across knowledge items. Returns new edge count."""
    edges = 0
    for i, item1 in enumerate(items):
        existing = {rel["item_id"] for rel in item1.related_items}
        for item2 in items[i + 1:]:
            if item2.item_id in existing:
                continue
            assoc = _association_weight(item1, item2)
            if assoc is None:
                continue
            weight, rel_type = assoc
            item1.related_items.append({
                "item_id": item2.item_id,
                "relation_type": rel_type,
                "weight": round(weight, 2),
            })
            edges += 1
    return edges


def _lineage_session_id(source_url: str) -> str:
    if not source_url.strip():
        return f"lineage_{int(time.time())}"
    return f"src_{hashlib.sha256(source_url.encode()).hexdigest()[:12]}"


def append_items_to_lineage(
    items: list[KnowledgeItem],
    *,
    source_url: str,
    source_title: str = "",
    session_id: str = "",
    sync_graph: bool = True,
) -> dict:
    """Incrementally append knowledge items, run 4-signal cross-ref, persist lineage."""
    if not items:
        return {
            "session_id": session_id or "",
            "items_added": 0,
            "edges_created": 0,
            "total_items": 0,
            "linked_items": 0,
            "graph_sync": {"synced": False},
        }

    sid = session_id or _lineage_session_id(source_url)
    graph = load_lineage(sid)
    if graph is None:
        graph = LineageGraph(
            session_id=sid,
            source_url=source_url,
            source_title=source_title or source_url,
            created_at=time.time(),
        )
    elif source_title and not graph.source_title:
        graph.source_title = source_title

    graph.items.extend(items)
    edges_created = build_cross_references(graph.items)
    save_lineage(graph)

    graph_sync: dict = {"synced": False}
    if sync_graph:
        try:
            from .lineage_cycle import sync_lineage_to_graph
            graph_sync = sync_lineage_to_graph(sid)
        except Exception as e:
            _log.warning("Lineage graph sync failed for %s: %s", sid, e)
            graph_sync = {"synced": False, "error": str(e)}

    return {
        "session_id": sid,
        "items_added": len(items),
        "total_items": graph.total_items,
        "edges_created": edges_created,
        "linked_items": sum(1 for item in graph.items if item.related_items),
        "graph_sync": graph_sync,
    }


# ═══════════════════════════════════════════════════════════════
# Storage
# ═══════════════════════════════════════════════════════════════

def save_lineage(graph: LineageGraph) -> Path:
    """Persist a lineage graph to disk."""
    path = LINEAGE_DIR / f"{graph.session_id}.json"
    data = {
        "session_id": graph.session_id,
        "source_url": graph.source_url,
        "source_title": graph.source_title,
        "created_at": graph.created_at,
        "summary": {
            "total_items": graph.total_items,
            "by_category": graph.by_category,
            "by_epistemic_level": graph.by_epistemic_level,
            "confidence_distribution": graph.confidence_distribution,
        },
        "items": [item.to_dict() for item in graph.items],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _log.info("Lineage saved: %s (%d items)", graph.session_id, graph.total_items)
    return path


def load_lineage(session_id: str) -> LineageGraph | None:
    """Load a previously saved lineage graph."""
    path = LINEAGE_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = LineageGraph(
        session_id=data["session_id"],
        source_url=data["source_url"],
        source_title=data["source_title"],
        created_at=data.get("created_at", 0),
    )
    # Reconstruct items (simplified)
    for item_data in data.get("items", []):
        source_data = item_data.get("source") or {}
        source_url = source_data.get("url", "") if isinstance(source_data, dict) else ""
        source_chunk = None
        if source_url:
            source_chunk = SourceChunk(
                source_url=source_url,
                paragraph_index=source_data.get("paragraph", 0) if isinstance(source_data, dict) else 0,
            )
        item = KnowledgeItem(
            item_id=item_data["item_id"],
            content=item_data["content"],
            category=item_data["category"],
            confidence=item_data["confidence"],
            epistemic_level=item_data.get("epistemic_level", "experience"),
            created_at=item_data.get("created_at", 0),
            source_chunk=source_chunk,
            related_items=list(item_data.get("related_items", [])),
            affected_skills=list(item_data.get("affected_skills", [])),
            graph_node_id=item_data.get("graph_node", ""),
        )
        graph.items.append(item)
    return graph


def list_lineages() -> list[dict]:
    """List all lineage sessions."""
    sessions = []
    for fp in sorted(LINEAGE_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            sessions.append({
                "session_id": data["session_id"],
                "source_title": data.get("source_title", ""),
                "source_url": data.get("source_url", ""),
                "total_items": data.get("summary", {}).get("total_items", 0),
                "created_at": data.get("created_at", 0),
            })
        except Exception:
            pass
    return sessions
