"""Knowledge Lineage — full data provenance from source to wisdom.

Philosophical foundations:
  Plato:   Knowledge = justified true belief. Lineage IS the justification.
  Kant:    Phenomena (raw data) → Categories (structuring) → Noumena (understanding)
  Piaget:  Assimilation (fits schema) vs Accommodation (changes schema)
  Popper:  Falsification attempts → surviving knowledge is stronger
  Luhmann: Structure emerges from linking — lineage shows the links

Every piece of knowledge carries its full history:
  Source → Extraction → Structuring → Integration → Verification → Impact
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

LINEAGE_DIR = Path(__file__).parent / "data" / "lineage"
LINEAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SourceChunk:
    """A specific chunk of source material."""
    chunk_id: str = ""              # src_<hash>
    source_url: str = ""
    source_type: str = ""           # url | file | conversation | paper
    paragraph_index: int = 0
    raw_text: str = ""
    char_offset_start: int = 0
    char_offset_end: int = 0


@dataclass
class ExtractStep:
    """One step in the knowledge extraction pipeline."""
    step_name: str = ""             # 初识 | 理解 | 拆解 | 重构 | 验证 | 内化 | 沉淀 | 扩散
    input_text: str = ""
    output_text: str = ""
    method: str = ""                # LLM call | regex | heuristic
    model_used: str = ""
    confidence_delta: float = 0.0   # how much confidence changed in this step
    elapsed_s: float = 0.0
    timestamp: float = 0.0


@dataclass
class KnowledgeItem:
    """A single knowledge item with full lineage."""
    item_id: str = ""               # ki_<hash>
    content: str = ""               # the knowledge itself
    category: str = "fact"          # fact | concept | heuristic | pattern | contradiction

    # Lineage
    source_chunk: SourceChunk | None = None
    extraction_pipeline: list[ExtractStep] = field(default_factory=list)

    # Current state
    confidence: float = 0.5
    epistemic_level: str = "experience"  # evidence | experience | knowledge | wisdom | superseded
    verified_by: list[str] = field(default_factory=list)     # other item IDs
    contradicted_by: list[str] = field(default_factory=list)  # other item IDs
    superseded_by: str = ""         # item ID of the newer fact that replaced this one

    # Graph connections
    graph_node_id: str = ""         # linked knowledge graph node
    related_items: list[dict] = field(default_factory=list)
    # [{item_id, relation_type, weight}]

    # Impact tracking
    affected_skills: list[dict] = field(default_factory=list)
    # [{skill_name, optimization_round, score_delta, timestamp}]

    # Temporal (Graphiti-inspired: bi-temporal validity)
    created_at: float = 0.0
    valid_at: float = 0.0           # when this fact became true
    invalid_at: float = 0.0         # when this fact stopped being true (0 = still valid)
    last_accessed: float = 0.0
    access_count: int = 0
    decay_rate: float = 0.05        # Ebbinghaus decay per day

    @property
    def is_valid(self) -> bool:
        """Is this fact currently valid? (Graphiti: auto-filter expired facts)"""
        return self.invalid_at == 0 or time.time() < self.invalid_at

    @property
    def current_strength(self) -> float:
        """Ebbinghaus: strength decays without reinforcement."""
        if self.last_accessed <= 0:
            self.last_accessed = self.created_at if self.created_at > 0 else time.time()
        days_since_access = (time.time() - self.last_accessed) / 86400
        decay = self.decay_rate * max(0, days_since_access)
        reinforcement = min(1.0, self.access_count * 0.1)
        return max(0.1, self.confidence - decay + reinforcement)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "content": self.content,
            "category": self.category,
            "confidence": self.confidence,
            "epistemic_level": self.epistemic_level,
            "is_valid": self.is_valid,
            "strength": round(self.current_strength, 2),
            "source": {
                "url": self.source_chunk.source_url if self.source_chunk else "",
                "paragraph": self.source_chunk.paragraph_index if self.source_chunk else 0,
            } if self.source_chunk else None,
            "pipeline_steps": len(self.extraction_pipeline),
            "graph_node": self.graph_node_id,
            "related_items": self.related_items,
            "related_count": len(self.related_items),
            "affected_skills": self.affected_skills,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "superseded_by": self.superseded_by,
        }


@dataclass
class LineageGraph:
    """The full provenance graph for a learning session."""
    session_id: str = ""
    source_url: str = ""
    source_title: str = ""
    items: list[KnowledgeItem] = field(default_factory=list)
    created_at: float = 0.0

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def by_category(self) -> dict[str, int]:
        cats = {}
        for item in self.items:
            cats[item.category] = cats.get(item.category, 0) + 1
        return cats

    @property
    def by_epistemic_level(self) -> dict[str, int]:
        levels = {}
        for item in self.items:
            levels[item.epistemic_level] = levels.get(item.epistemic_level, 0) + 1
        return levels

    @property
    def valid_items(self) -> list[KnowledgeItem]:
        """Only currently valid items (Graphiti: auto-filter expired facts)."""
        return [i for i in self.items if i.is_valid]

    @property
    def superseded_items(self) -> list[KnowledgeItem]:
        """Items that have been superseded by newer facts."""
        return [i for i in self.items if not i.is_valid]

    @property
    def confidence_distribution(self) -> dict[str, int]:
        dist = {"high": 0, "medium": 0, "low": 0}
        for item in self.items:
            if item.confidence >= 0.7: dist["high"] += 1
            elif item.confidence >= 0.4: dist["medium"] += 1
            else: dist["low"] += 1
        return dist

    def to_cytoscape(self) -> dict:
        """Convert to Cytoscape.js format for frontend visualization."""
        def _safe(s, maxlen=200):
            return _json_safe(str(s)[:maxlen])

        nodes = []
        edges = []

        # Source node
        source_id = "source_root"
        nodes.append({
            "data": {
                "id": source_id,
                "label": _safe(self.source_title, 80) or _safe(self.source_url, 80),
                "type": "source",
                "color": "#f59e0b",
            }
        })

        for item in self.items:
            nodes.append({
                "data": {
                    "id": item.item_id,
                    "label": _safe(item.content, 200),
                    "type": item.category,
                    "confidence": item.confidence,
                    "level": item.epistemic_level,
                    "color": _confidence_color(item.confidence),
                    "strength": round(item.current_strength, 2),
                }
            })
            # Source → item edge
            edges.append({
                "data": {
                    "id": f"{source_id}->{item.item_id}",
                    "source": source_id,
                    "target": item.item_id,
                    "label": "extracted_from",
                    "weight": 0.5,
                }
            })
            # Item → related items edges
            for rel in item.related_items:
                edges.append({
                    "data": {
                        "id": f"{item.item_id}->{rel['item_id']}",
                        "source": item.item_id,
                        "target": rel["item_id"],
                        "label": rel.get("relation_type", "related"),
                        "weight": rel.get("weight", 0.5),
                    }
                })
            # Item → affected skills edges
            for aff in item.affected_skills:
                skill_node_id = f"skill_{aff['skill_name']}"
                if not any(n["data"]["id"] == skill_node_id for n in nodes):
                    nodes.append({
                        "data": {
                            "id": skill_node_id,
                            "label": aff["skill_name"][:40],
                            "type": "skill",
                            "color": "#10b981",
                        }
                    })
                edges.append({
                    "data": {
                        "id": f"{item.item_id}->{skill_node_id}",
                        "source": item.item_id,
                        "target": skill_node_id,
                        "label": f"improved +{aff.get('score_delta', 0):.1f}",
                        "weight": 0.8,
                    }
                })

        return {"nodes": nodes, "edges": edges}

    def to_mermaid(self) -> str:
        """Convert to Mermaid flowchart for markdown rendering."""
        def _s(text, maxlen=50):
            return _json_safe(str(text)[:maxlen])

        lines = ["```mermaid", "graph TD"]
        lines.append(f'    SOURCE["{_s(self.source_title, 50)}"]')
        lines.append(f'    SOURCE -->|"ingested"| SESSION["Session {self.session_id[:8]}"]')

        for item in self.items[:20]:
            safe_id = re.sub(r'[^a-zA-Z0-9]', '_', item.item_id)
            label = _s(item.content, 40)
            lines.append(f'    {safe_id}["{label}"]')
            lines.append(f'    SESSION -->|"{item.category}"| {safe_id}')

            for aff in item.affected_skills[:3]:
                skill_id = re.sub(r'[^a-zA-Z0-9]', '_', aff['skill_name'])
                skill_label = _s(aff['skill_name'], 30)
                delta = aff.get('score_delta', 0)
                lines.append(f'    {skill_id}["Skill: {skill_label}"]')
                lines.append(f'    {safe_id} -->|"improved +{delta:.1f}"| {skill_id}')

        lines.append("```")
        return "\n".join(lines)


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
    import hashlib
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


def _json_safe(text: str) -> str:
    """Sanitize text for safe JSON embedding — strip control chars and escape quotes."""
    if not text:
        return ""
    # Remove control characters (except newline/tab) and strip quotes/backslashes
    import re as _re
    text = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.replace('\\', '/').replace('"', "'").replace('\n', ' ').replace('\r', '')


def _confidence_color(confidence: float) -> str:
    if confidence >= 0.7: return "#10b981"
    if confidence >= 0.4: return "#f59e0b"
    return "#ef4444"


# ═══════════════════════════════════════════════════════════════
# Gap 1: Ebbinghaus Consolidation
# ═══════════════════════════════════════════════════════════════

def run_consolidation_cycle() -> dict:
    """Run an Ebbinghaus consolidation cycle across all lineage items.

    For each knowledge item:
    - Items accessed recently → strengthen (reinforcement)
    - Items not accessed in 7+ days → decay
    - Items below strength threshold → flag for review
    - Items below critical threshold → mark as stale (needs re-verification)
    """
    all_items = []
    for fp in sorted(LINEAGE_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            for item_data in data.get("items", []):
                item = KnowledgeItem(
                    item_id=item_data["item_id"],
                    content=item_data["content"],
                    category=item_data.get("category", "fact"),
                    confidence=item_data.get("confidence", 0.5),
                    epistemic_level=item_data.get("epistemic_level", "experience"),
                    created_at=item_data.get("created_at", 0),
                    last_accessed=item_data.get("last_accessed", item_data.get("created_at", 0)),
                    access_count=item_data.get("access_count", 0),
                )
                all_items.append(item)
        except Exception:
            pass

    now = time.time()
    strengthened = 0
    decayed = 0
    flagged = 0
    stale = 0

    for item in all_items:
        days_since = (now - item.last_accessed) / 86400

        if days_since < 1:
            # Recent access → reinforce
            item.confidence = min(1.0, item.confidence + 0.05)
            item.access_count += 1
            strengthened += 1
        elif days_since > 7:
            # Decay
            decay_amount = item.decay_rate * (days_since - 7)
            item.confidence = max(0.1, item.confidence - decay_amount)
            decayed += 1

        strength = item.current_strength
        if strength < 0.3:
            stale += 1
        elif strength < 0.5:
            flagged += 1

    # Update stored items
    for fp in sorted(LINEAGE_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            updated = False
            for item_data in data.get("items", []):
                for item in all_items:
                    if item.item_id == item_data["item_id"]:
                        item_data["confidence"] = round(item.confidence, 2)
                        item_data["access_count"] = item.access_count
                        item_data["last_accessed"] = item.last_accessed
                        item_data["strength"] = round(item.current_strength, 2)
                        updated = True
                        break
            if updated:
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {
        "total_items": len(all_items),
        "strengthened": strengthened,
        "decayed": decayed,
        "flagged_for_review": flagged,
        "stale": stale,
    }


def access_knowledge(item_id: str) -> None:
    """Mark a knowledge item as accessed (reinforcement)."""
    for fp in sorted(LINEAGE_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            for item_data in data.get("items", []):
                if item_data.get("item_id") == item_id:
                    item_data["last_accessed"] = time.time()
                    item_data["access_count"] = item_data.get("access_count", 0) + 1
                    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    return
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# Gap 2: Auto-trigger Pattern Miner
# ═══════════════════════════════════════════════════════════════

def trigger_pattern_mining(llm_args: tuple) -> dict:
    """Auto-trigger cross-skill pattern mining after new knowledge ingestion.

    Analyzes all skills collectively to find:
    - Structural archetypes that have emerged
    - Success factors that correlate with new knowledge
    - Anti-patterns that new knowledge helps explain
    """
    try:
        from skillos.skills.pattern_miner import profile_all_skills, SkillProfile
        profiles = profile_all_skills()

        if len(profiles) < 3:
            return {"mined": False, "reason": "Not enough skills for pattern mining"}

        # Find patterns: what do high-scoring skills share?
        high = [p for p in profiles if p.avg_score >= 3.5]
        low = [p for p in profiles if p.avg_score < 2.5]

        patterns = []
        if high:
            patterns.append({
                "type": "success_factor",
                "finding": f"High-scoring skills (n={len(high)}) average {sum(p.step_count for p in high)/len(high):.1f} steps vs {sum(p.step_count for p in low)/len(low):.1f} in low-scoring" if low else "",
                "sample_skills": [p.name for p in high[:3]],
            })

        # Check if newly ingested knowledge correlates with any skill improvements
        for p in profiles:
            if p.avg_score >= 4.0 and p.total_runs >= 3:
                patterns.append({
                    "type": "validated_skill",
                    "skill": p.name,
                    "avg_score": p.avg_score,
                    "runs": p.total_runs,
                    "signal": "This skill consistently performs well",
                })

        return {
            "mined": True,
            "total_skills_analyzed": len(profiles),
            "patterns_found": len(patterns),
            "patterns": patterns,
        }
    except Exception as e:
        _log.warning("Pattern mining failed: %s", e)
        return {"mined": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# Gap 3: Wisdom Layer — Cross-Lineage Meta-Patterns
# ═══════════════════════════════════════════════════════════════

def extract_wisdom() -> dict:
    """Extract meta-patterns across ALL lineage sessions.

    Wisdom = knowing what patterns recur across domains, what types of
    knowledge most frequently improve skills, and when our methods fail.
    """
    all_sessions = list_lineages()
    if len(all_sessions) < 2:
        return {"wisdom": False, "reason": "Need at least 2 lineage sessions for cross-session patterns"}

    all_items = []
    total_affected = 0
    total_surprises = 0
    domains = set()
    categories = {}

    for session in all_sessions:
        graph = load_lineage(session["session_id"])
        if not graph:
            continue

        for item in graph.items:
            all_items.append(item)
            categories[item.category] = categories.get(item.category, 0) + 1
            if item.affected_skills:
                total_affected += len(item.affected_skills)
            if item.contradicted_by:
                total_surprises += 1

        # Extract domain from title
        title = session.get("source_title", "")
        if title:
            for word in re.findall(r'[\w]{3,}', title):
                if len(word) > 4:
                    domains.add(word.lower())

    # Wisdom insights
    insights = []

    # Which category of knowledge most often improves skills?
    cat_impact = {}
    for item in all_items:
        if item.affected_skills:
            cat_impact[item.category] = cat_impact.get(item.category, 0) + len(item.affected_skills)

    if cat_impact:
        best_cat = max(cat_impact, key=cat_impact.get)
        insights.append(f"最有影响力的知识类型是 '{best_cat}'，平均触发 {cat_impact[best_cat]/max(1, categories.get(best_cat, 1)):.1f} 次 skill 优化")

    # Surprise rate
    if all_items:
        surprise_rate = total_surprises / len(all_items)
        if surprise_rate > 0.1:
            insights.append(f"矛盾率偏高 ({surprise_rate:.1%})，建议审查知识验证流程")
        else:
            insights.append(f"矛盾率健康 ({surprise_rate:.1%})，知识体系内部一致")

    # Domain coverage
    if domains:
        insights.append(f"已覆盖 {len(domains)} 个知识领域")

    # Consolidation health
    strengths = [item.current_strength for item in all_items if hasattr(item, 'current_strength')]
    if strengths:
        avg_strength = sum(strengths) / len(strengths)
        if avg_strength < 0.5:
            insights.append(f"知识衰减警告：平均强度 {avg_strength:.1%}，建议增加复习频率")

    return {
        "wisdom": True,
        "sessions_analyzed": len(all_sessions),
        "total_knowledge_items": len(all_items),
        "total_skill_improvements": total_affected,
        "domains_covered": len(domains),
        "insights": insights,
        "category_distribution": categories,
        "avg_item_confidence": round(sum(i.confidence for i in all_items) / max(1, len(all_items)), 2),
    }


# ═══════════════════════════════════════════════════════════════
# Gap 4: Auto-create Knowledge Graph Nodes
# ═══════════════════════════════════════════════════════════════

def sync_lineage_to_graph(session_id: str) -> dict:
    """Sync lineage items into the knowledge graph.

    For each knowledge item in the lineage session:
    - Create a graph node (concept/fact/skill)
    - Create typed edges based on related_items
    - Detect clusters after insertion
    """
    graph = load_lineage(session_id)
    if not graph:
        return {"synced": False, "reason": "Lineage session not found"}

    try:
        from skillos.knowledge.graph import KnowledgeGraph, KnowledgeNode, KnowledgeEdge
        kg = KnowledgeGraph()
    except ImportError:
        # Fallback: use the get_graph singleton
        from skillos.knowledge.graph import get_graph
        kg = get_graph()

    nodes_created = 0
    edges_created = 0

    for item in graph.items:
        # Create or find node
        node_id = kg.add_node(
            name=item.content[:100],
            node_type="concept" if item.category == "concept" else "fact",
            description=item.content,
            source=graph.source_url,
            confidence=item.confidence,
        )
        item.graph_node_id = node_id
        nodes_created += 1

        # Create edges for related items
        for rel in item.related_items:
            kg.add_edge(
                source_id=item.graph_node_id,
                target_id=rel.get("item_id", ""),
                relation_type=rel.get("relation_type", "related_to"),
                weight=rel.get("weight", 0.5),
                evidence=f"Extracted from {graph.source_url}",
            )
            edges_created += 1

        # Create edges for affected skills
        for aff in item.affected_skills:
            skill_node_id = kg.add_node(
                name=aff["skill_name"],
                node_type="skill",
                description=f"Skill improved by knowledge from {graph.source_title}",
            )
            kg.add_edge(
                source_id=item.graph_node_id,
                target_id=skill_node_id,
                relation_type="improves",
                weight=0.8,
                evidence=f"Score delta: +{aff.get('score_delta', 0):.1f}",
            )
            nodes_created += 1
            edges_created += 1

    # LightRAG-inspired: incremental update — skip full cluster rebuild on every sync.
    # Only re-detect clusters if significant new nodes were added (>=5 new nodes).
    # Query-time graph traversal handles the rest.
    if nodes_created >= 5:
        clusters = kg.detect_clusters(min_cluster_size=2)
    else:
        clusters = kg.clusters  # keep existing clusters
    kg.save()

    # Save updated lineage with graph node IDs
    save_lineage(graph)

    return {
        "synced": True,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "clusters_detected": len(clusters),
        "cluster_labels": [c.label for c in clusters],
    }


# ═══════════════════════════════════════════════════════════════
# Full Pipeline: Ingest → Digest → Lineage → Graph → Mine → Wisdom
# ═══════════════════════════════════════════════════════════════

def full_knowledge_cycle(
    content: str,
    source_url: str,
    llm_args: tuple,
    *,
    existing_skills: list[str] | None = None,
) -> dict:
    """Run the complete knowledge internalization cycle.

    Every step from source to wisdom, with full data lineage.
    """
    t_start = time.time()

    if existing_skills is None:
        from skillos.skills import skill_store
        existing_skills = [s for s in skill_store.list_skills()
                          if s not in ('brainstorming', 'skill-creator', 'deep-digest', 'cold-start-interview')]

    # Phase 1: Deep Digest
    from skillos.knowledge.deep_digest import deep_digest, save_digest
    dd_result = deep_digest(content, source_url, existing_skills=existing_skills, llm_args=llm_args)
    if dd_result.glossary or dd_result.patterns or dd_result.sections:
        save_digest(dd_result)

    # Phase 2–3 + 6: Lineage via unified post_ingest (4-signal + optional graph sync)
    extracted_items = []
    try:
        from skillos.knowledge.extractor import extract_knowledge, save_knowledge, verify_knowledge, load_all_knowledge
        extracted_items = extract_knowledge(content, source_url, llm_args)
        if extracted_items:
            extracted_items = verify_knowledge(extracted_items, load_all_knowledge())
            save_knowledge(extracted_items)
    except Exception:
        _log.debug("Flat knowledge extraction skipped in full_knowledge_cycle", exc_info=True)

    from skillos.knowledge.ingest_pipeline import post_ingest
    lineage_result = post_ingest(
        content,
        source_url,
        source_title=dd_result.title,
        digest_result=dd_result if (dd_result.glossary or dd_result.patterns or dd_result.sections) else None,
        extractor_items=extracted_items,
        sync_graph=True,
        channel="full_knowledge_cycle",
    )
    session_id = lineage_result.get("session_id", f"cycle_{int(t_start)}")
    edges_created = lineage_result.get("edges_created", 0)
    graph = load_lineage(session_id)
    if graph is None:
        graph = LineageGraph(
            session_id=session_id,
            source_url=source_url,
            source_title=dd_result.title,
            created_at=time.time(),
        )

    # Phase 4: Surprise detection
    try:
        from skillos.knowledge import extractor as knowledge_extractor
        existing = [KnowledgeItem(item_id=f"ex_{i}", content=k.content, category=k.category)
                    for i, k in enumerate(knowledge_extractor.load_all_knowledge()[:20])]
        for item in graph.items[:5]:
            detect_surprise(item, existing)
    except Exception:
        pass

    # Phase 5: Auto-optimize related skills
    affected = []
    from skillos.skills import skill_store as ss
    for skill_name in ss.list_skills()[:15]:
        if skill_name in ('brainstorming', 'skill-creator', 'deep-digest', 'cold-start-interview'):
            continue
        try:
            body = ss.get_skill_body(ss.load_skill(skill_name))
            relevance = sum(1 for item in graph.items[:10]
                          if set(re.findall(r'[\w一-鿿]{3,}', item.content.lower())) &
                             set(re.findall(r'[\w一-鿿]{3,}', body.lower())))
            if relevance >= 2:
                affected.append(skill_name)
                for item in graph.items[:10]:
                    if set(re.findall(r'[\w一-鿿]{3,}', item.content.lower())) & set(re.findall(r'[\w一-鿿]{3,}', body.lower())):
                        item.affected_skills.append({"skill_name": skill_name, "score_delta": relevance * 0.5,
                                                     "timestamp": time.time()})
        except Exception:
            pass

    graph_sync = lineage_result.get("graph_sync", {"synced": False})
    if affected:
        save_lineage(graph)
        try:
            graph_sync = sync_lineage_to_graph(session_id)
        except Exception:
            _log.debug("Lineage re-sync skipped after skill impact", exc_info=True)

    # Phase 7: Pattern mining
    pattern_result = trigger_pattern_mining(llm_args)

    # Phase 8: Consolidation
    consolidation = run_consolidation_cycle()

    # Phase 9: Wisdom extraction
    wisdom = extract_wisdom()

    elapsed = round(time.time() - t_start, 1)

    return {
        "session_id": session_id,
        "source_title": dd_result.title,
        "digest": {
            "glossary_terms": len(dd_result.glossary),
            "patterns": len(dd_result.patterns),
            "sections": len(dd_result.sections),
            "cross_references": len(dd_result.cross_references),
        },
        "lineage": {
            "total_items": graph.total_items,
            "by_category": graph.by_category,
            "by_epistemic_level": graph.by_epistemic_level,
            "linked_items": lineage_result.get("linked_items", sum(1 for item in graph.items if item.related_items)),
            "edges_created": edges_created,
            "lineage_applied": lineage_result.get("lineage_applied", False),
        },
        "graph_sync": graph_sync,
        "affected_skills": affected,
        "pattern_mining": pattern_result,
        "consolidation": consolidation,
        "wisdom": wisdom,
        "elapsed_s": elapsed,
    }


# ═══════════════════════════════════════════════════════════════
# Skill precipitation events (Phase 5 — who / which chat / which session)
# ═══════════════════════════════════════════════════════════════

SKILL_EVENTS_PATH = LINEAGE_DIR / "skill_precipitations.jsonl"


def record_skill_precipitation(
    skill_name: str,
    *,
    session_id: str = "",
    channel: str = "",
    chat_id: str = "",
    user_id: str = "",
    source: str = "",
) -> dict:
    """Append a skill creation event with IM contributor context."""
    event = {
        "event_id": f"sp_{uuid.uuid4().hex[:10]}",
        "skill_name": skill_name,
        "session_id": session_id,
        "channel": channel,
        "chat_id": chat_id,
        "user_id": user_id,
        "source": source,
        "created_at": time.time(),
    }
    SKILL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SKILL_EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def query_skill_precipitations(
    skill_name: str = "",
    chat_id: str = "",
    user_id: str = "",
    session_id: str = "",
    limit: int = 50,
) -> list[dict]:
    """Query skill precipitation lineage events."""
    if not SKILL_EVENTS_PATH.exists():
        return []
    results: list[dict] = []
    for line in SKILL_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if skill_name and ev.get("skill_name") != skill_name:
            continue
        if chat_id and ev.get("chat_id") != chat_id:
            continue
        if user_id and ev.get("user_id") != user_id:
            continue
        if session_id and ev.get("session_id") != session_id:
            continue
        results.append(ev)
    return results[-limit:]


def format_skill_lineage(skill_name: str) -> str:
    """Human-readable lineage for a skill."""
    events = query_skill_precipitations(skill_name=skill_name)
    if not events:
        return f"No precipitation lineage for skill '{skill_name}'."
    lines = [f"Skill lineage: {skill_name} ({len(events)} event(s))"]
    for ev in events:
        who = ev.get("user_id") or "unknown"
        chat = ev.get("chat_id") or "-"
        sess = ev.get("session_id") or "-"
        ch = ev.get("channel") or "-"
        lines.append(
            f"- [{ev.get('event_id')}] channel={ch} user={who} chat={chat} session={sess}"
        )
    return "\n".join(lines)
