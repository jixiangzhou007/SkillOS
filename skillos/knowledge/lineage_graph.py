"""Knowledge Lineage — LineageGraph class for provenance graph management."""

import re
from dataclasses import dataclass, field

from .lineage_types import KnowledgeItem


def _json_safe(text: str) -> str:
    """Sanitize text for safe JSON embedding — strip control chars and escape quotes."""
    if not text:
        return ""
    # Remove control characters (except newline/tab) and strip quotes/backslashes
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.replace('\\', '/').replace('"', "'").replace('\n', ' ').replace('\r', '')


def _confidence_color(confidence: float) -> str:
    if confidence >= 0.7:
        return "#10b981"
    if confidence >= 0.4:
        return "#f59e0b"
    return "#ef4444"


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
        cats: dict[str, int] = {}
        for item in self.items:
            cats[item.category] = cats.get(item.category, 0) + 1
        return cats

    @property
    def by_epistemic_level(self) -> dict[str, int]:
        levels: dict[str, int] = {}
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
            if item.confidence >= 0.7:
                dist["high"] += 1
            elif item.confidence >= 0.4:
                dist["medium"] += 1
            else:
                dist["low"] += 1
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
