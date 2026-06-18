"""Knowledge Graph — human-like knowledge organization.

Not a complete ontology. A lightweight, emergent, self-organizing graph
where structure grows from use, not from pre-defined categories.

Inspired by:
- Zettelkasten (Luhmann): structure emerges from linking, not top-down taxonomy
- Conceptual graphs (Sowa): typed relationships between concepts
- Spreading activation (Collins & Loftus): related concepts activate each other

Relationship types (8, like human knowledge):
  is_a        — taxonomic: X is a type of Y
  part_of     — composition: X is part of Y
  depends_on  — prerequisite: X requires Y first
  contradicts — conflict: X and Y disagree
  generalizes — abstraction: X is a more general form of Y
  analogous_to— cross-domain: X in domain A is like Y in domain B
  derived_from— provenance: X came from Y
  evolved_to  — versioning: X was replaced by Y
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

GRAPH_PATH = Path(__file__).parent / "knowledge" / "graph.json"
GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)

RELATION_TYPES = [
    "is_a", "part_of", "depends_on", "contradicts",
    "generalizes", "analogous_to", "derived_from", "evolved_to",
]


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph — a concept, fact, skill, or case."""

    id: str
    name: str
    node_type: str = "concept"  # concept | fact | skill | case | source
    description: str = ""
    source: str = ""            # where this knowledge came from
    confidence: float = 0.5
    created_at: float = 0.0
    activation: float = 0.0     # spreading activation value (transient, not persisted)
    cluster_id: str = ""        # assigned by community detection


@dataclass
class KnowledgeEdge:
    """A typed, directed relationship between two knowledge nodes.

    EvoRAG-inspired: contribution scoring tracks how much this edge
    helps answer real user questions."""
    
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 0.5
    evidence: str = ""
    created_at: float = 0.0
    # EvoRAG: contribution tracking
    contribution_score: float = 0.0  # How much this edge helps (0-1)
    times_used: int = 0              # How many times it was traversed
    times_helped: int = 0            # How many times it led to good answers
    """A typed, directed relationship between two knowledge nodes."""

    source_id: str
    target_id: str
    relation_type: str          # one of RELATION_TYPES
    weight: float = 0.5         # strength of this relationship (grows with use)
    evidence: str = ""          # why this relationship exists
    created_at: float = 0.0


@dataclass
class KnowledgeCluster:
    """An emergent grouping of related nodes (like a Zettelkasten topic cluster)."""

    id: str
    label: str                  # auto-generated or human-assigned
    node_ids: list[str] = field(default_factory=list)
    central_node: str = ""      # the most-connected node in this cluster
    cohesion: float = 0.0       # how tightly connected (0-1)
    created_at: float = 0.0


class KnowledgeGraph:
    """The knowledge graph — lightweight, JSON-backed, self-organizing."""

    def __init__(self) -> None:
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[KnowledgeEdge] = []
        self.clusters: list[KnowledgeCluster] = []
        self._load()

    def record_edge_usage(self, source_id: str, target_id: str, helped: bool):
        """EvoRAG: record whether traversing this edge helped answer a question."""
        for edge in self.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                edge.times_used += 1
                if helped:
                    edge.times_helped += 1
                    edge.contribution_score = min(1.0, edge.contribution_score + 0.1)
                    edge.weight = min(1.0, edge.weight + 0.05)
                else:
                    edge.contribution_score = max(0.0, edge.contribution_score - 0.05)
                    edge.weight = max(0.1, edge.weight - 0.02)
                self.save()
                return

    def prune_low_contribution_edges(self, threshold: float = 0.1, min_uses: int = 5):
        """EvoRAG: remove edges that have been used but never helped."""
        before = len(self.edges)
        self.edges = [e for e in self.edges
                      if not (e.times_used >= min_uses and e.contribution_score < threshold)]
        removed = before - len(self.edges)
        if removed:
            self.save()
        return removed

    def _load(self) -> None:
        if not GRAPH_PATH.exists():
            return
        try:
            data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
            for n in data.get("nodes", []):
                node = KnowledgeNode(
                    id=n["id"], name=n["name"], node_type=n.get("type", "concept"),
                    description=n.get("description", ""), source=n.get("source", ""),
                    confidence=n.get("confidence", 0.5), created_at=n.get("created_at", 0),
                    cluster_id=n.get("cluster_id", ""),
                )
                self.nodes[node.id] = node
            for e in data.get("edges", []):
                self.edges.append(KnowledgeEdge(
                    source_id=e["source"], target_id=e["target"],
                    relation_type=e["type"], weight=e.get("weight", 0.5),
                    evidence=e.get("evidence", ""), created_at=e.get("created_at", 0),
                ))
            for c in data.get("clusters", []):
                self.clusters.append(KnowledgeCluster(
                    id=c["id"], label=c["label"], node_ids=c.get("node_ids", []),
                    central_node=c.get("central_node", ""),
                    cohesion=c.get("cohesion", 0), created_at=c.get("created_at", 0),
                ))
        except Exception as e:
            _log.warning("Failed to load graph: %s", e)

    def save(self) -> None:
        data = {
            "nodes": [
                {"id": n.id, "name": n.name, "type": n.node_type,
                 "description": n.description, "source": n.source,
                 "confidence": n.confidence, "created_at": n.created_at,
                 "cluster_id": n.cluster_id}
                for n in self.nodes.values()
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id, "type": e.relation_type,
                 "weight": e.weight, "evidence": e.evidence, "created_at": e.created_at}
                for e in self.edges
            ],
            "clusters": [
                {"id": c.id, "label": c.label, "node_ids": c.node_ids,
                 "central_node": c.central_node, "cohesion": c.cohesion,
                 "created_at": c.created_at}
                for c in self.clusters
            ],
        }
        GRAPH_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Node operations ──────────────────────────────────────

    def add_node(self, name: str, node_type: str = "concept",
                 description: str = "", source: str = "", confidence: float = 0.5) -> str:
        """Add a node. Returns node ID. Deduplicates by name."""
        # Check for existing
        for node in self.nodes.values():
            if node.name == name:
                return node.id

        nid = f"n_{int(time.time())}_{hash(name) % 10000:04d}"
        self.nodes[nid] = KnowledgeNode(
            id=nid, name=name, node_type=node_type,
            description=description, source=source,
            confidence=confidence, created_at=time.time(),
        )
        self.save()
        return nid

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self.nodes.get(node_id)

    def find_node(self, name: str) -> Optional[KnowledgeNode]:
        for node in self.nodes.values():
            if node.name == name:
                return node
        # Fuzzy match
        for node in self.nodes.values():
            if name in node.name or node.name in name:
                return node
        return None

    # ── Edge operations ──────────────────────────────────────

    def add_edge(self, source_id: str, target_id: str, relation_type: str,
                 weight: float = 0.5, evidence: str = "") -> None:
        """Add or strengthen a typed relationship between two nodes."""
        if relation_type not in RELATION_TYPES:
            return

        # Check for existing edge — strengthen if found
        for edge in self.edges:
            if edge.source_id == source_id and edge.target_id == target_id and edge.relation_type == relation_type:
                edge.weight = min(1.0, edge.weight + 0.1)  # strengthen
                edge.created_at = time.time()
                self.save()
                return

        # Check for reverse edge (for symmetric relations like analogous_to)
        for edge in self.edges:
            if (edge.source_id == target_id and edge.target_id == source_id
                    and edge.relation_type == relation_type
                    and relation_type in ("analogous_to", "contradicts")):
                edge.weight = min(1.0, edge.weight + 0.1)
                self.save()
                return

        self.edges.append(KnowledgeEdge(
            source_id=source_id, target_id=target_id,
            relation_type=relation_type, weight=weight,
            evidence=evidence, created_at=time.time(),
        ))
        self.save()

    def get_neighbors(self, node_id: str, relation_type: str = "") -> list[tuple[KnowledgeNode, KnowledgeEdge]]:
        """Get all neighbors of a node, optionally filtered by relation type."""
        results = []
        for edge in self.edges:
            match = False
            neighbor_id = ""
            if edge.source_id == node_id:
                neighbor_id = edge.target_id
                match = True
            elif edge.target_id == node_id:
                neighbor_id = edge.source_id
                match = True
            if match and (not relation_type or edge.relation_type == relation_type):
                neighbor = self.nodes.get(neighbor_id)
                if neighbor:
                    results.append((neighbor, edge))
        return results

    # ── Clustering (emergent, like Zettelkasten) ────────────

    def detect_clusters(self, min_cluster_size: int = 3) -> list[KnowledgeCluster]:
        """Simple community detection based on edge density.

        Uses label propagation — clusters emerge from connection patterns,
        not from pre-defined categories.
        """
        if len(self.nodes) < min_cluster_size:
            return []

        # Build adjacency
        adj: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            adj[edge.source_id].add(edge.target_id)
            adj[edge.target_id].add(edge.source_id)

        # Label propagation
        labels: dict[str, str] = {}
        for nid in self.nodes:
            labels[nid] = nid  # each node starts with its own label

        for _ in range(10):  # propagate labels
            changed = False
            node_ids = list(self.nodes.keys())
            # Random order not needed for deterministic result
            for nid in node_ids:
                if nid not in adj:
                    continue
                neighbor_labels = [labels.get(n, n) for n in adj[nid]]
                if not neighbor_labels:
                    continue
                # Pick the most common neighbor label
                from collections import Counter
                most_common = Counter(neighbor_labels).most_common(1)[0][0]
                if labels[nid] != most_common:
                    labels[nid] = most_common
                    changed = True
            if not changed:
                break

        # Group by label
        groups: dict[str, list[str]] = defaultdict(list)
        for nid, label in labels.items():
            groups[label].append(nid)

        # Create clusters for groups >= min_cluster_size
        clusters = []
        for label, members in groups.items():
            if len(members) >= min_cluster_size:
                central = self._find_central_node(members)
                cohesion = self._cluster_cohesion(members)
                cid = f"c_{int(time.time())}_{hash(label) % 10000:04d}"
                cluster = KnowledgeCluster(
                    id=cid,
                    label=self._auto_label(members),
                    node_ids=members,
                    central_node=central,
                    cohesion=cohesion,
                    created_at=time.time(),
                )
                clusters.append(cluster)

        self.clusters = clusters
        # Update node cluster assignments
        for cluster in clusters:
            for nid in cluster.node_ids:
                if nid in self.nodes:
                    self.nodes[nid].cluster_id = cluster.id
        self.save()
        return clusters

    def _find_central_node(self, node_ids: list[str]) -> str:
        """Find the most-connected node in a group (highest degree)."""
        best, best_deg = "", -1
        for nid in node_ids:
            deg = sum(1 for e in self.edges if e.source_id == nid or e.target_id == nid)
            if deg > best_deg:
                best, best_deg = nid, deg
        return best

    def _cluster_cohesion(self, node_ids: list[str]) -> float:
        """How tightly connected is this group? (0-1)"""
        nidset = set(node_ids)
        internal = sum(1 for e in self.edges
                       if e.source_id in nidset and e.target_id in nidset)
        max_edges = len(node_ids) * (len(node_ids) - 1) / 2
        return internal / max_edges if max_edges > 0 else 0.0

    def _auto_label(self, node_ids: list[str]) -> str:
        """Generate a label for a cluster based on its central node."""
        central = self._find_central_node(node_ids)
        node = self.nodes.get(central)
        if node:
            return f"关于「{node.name}」的知识群"
        return "未命名知识群"

    # ── Query ────────────────────────────────────────────────

    def spreading_activation(self, seed_ids: list[str], depth: int = 2) -> dict[str, float]:
        """Spreading activation from seed nodes — like how humans recall related ideas.

        Each node activates its neighbors, which activate theirs, with decay.
        """
        activations: dict[str, float] = {}
        # Initialize seeds
        for nid in seed_ids:
            if nid in self.nodes:
                activations[nid] = 1.0
                self.nodes[nid].activation = 1.0

        # Spread
        for _ in range(depth):
            new_acts: dict[str, float] = dict(activations)
            for nid, act in activations.items():
                for edge in self.edges:
                    if edge.source_id == nid:
                        target = edge.target_id
                    elif edge.target_id == nid:
                        target = edge.source_id
                    else:
                        continue
                    boost = act * edge.weight * 0.5  # 50% decay per hop
                    new_acts[target] = max(new_acts.get(target, 0), boost)
            activations = new_acts

        # Reset transient activations
        for node in self.nodes.values():
            node.activation = activations.get(node.id, 0)

        return activations

    def get_cluster_tree(self) -> dict:
        """Return hierarchical view: clusters → their nodes → their connections."""
        tree = {"clusters": []}
        for cluster in self.clusters:
            cdata = {
                "label": cluster.label,
                "cohesion": round(cluster.cohesion, 2),
                "nodes": [],
            }
            for nid in cluster.node_ids:
                node = self.nodes.get(nid)
                if node:
                    neighbors = self.get_neighbors(nid)
                    cdata["nodes"].append({
                        "name": node.name,
                        "type": node.node_type,
                        "connections": len(neighbors),
                        "relation_types": list(set(e.relation_type for _, e in neighbors[:5])),
                    })
            tree["clusters"].append(cdata)
        return tree


# Singleton
_graph: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph


# ═══════════════════════════════════════════════════════════════
# Integration: auto-build graph from skills and knowledge
# ═══════════════════════════════════════════════════════════════

def ingest_skill_to_graph(skill_name: str, skill_content: str) -> None:
    """Add a skill and its knowledge items as nodes in the graph."""
    g = get_graph()

    # Add skill as a node
    skill_id = g.add_node(skill_name, node_type="skill", description=skill_content[:200])

    # Link to knowledge items
    try:
        from skillos.knowledge import skill_kb
        kb = skill_kb.load_kb(skill_name)
        for fact in kb.facts[:5]:
            fid = g.add_node(fact.content[:120], node_type="fact", description=fact.content)
            g.add_edge(skill_id, fid, "part_of", weight=0.6,
                       evidence=f"从技能'{skill_name}'的KB提取")
        for heuristic in kb.heuristics[:3]:
            hid = g.add_node(heuristic.content[:120], node_type="fact", description=heuristic.content)
            g.add_edge(skill_id, hid, "depends_on", weight=0.5,
                       evidence=f"技能'{skill_name}'的启发式规则")
    except Exception as e:
        _log.warning("Non-critical in knowledge_graph.py: %s", e)
        pass

    # Link to source (derived_from)
    source_match = re.search(r'https?://[^\s]+', skill_content)
    if source_match:
        src_url = source_match.group(0)
        src_id = g.add_node(src_url[:100], node_type="source")
        g.add_edge(skill_id, src_id, "derived_from", weight=0.8,
                   evidence=f"技能'{skill_name}'来源")


def ingest_knowledge_to_graph(knowledge_content: str, source_url: str) -> None:
    """Add extracted knowledge items as nodes, linked to their source."""
    g = get_graph()
    src_id = g.add_node(source_url[:100], node_type="source")

    # Extract key concepts from knowledge content
    concepts = re.findall(r'「(.+?)」|"(.+?)"|\*\*(.+?)\*\*', knowledge_content)
    for match_groups in concepts[:10]:
        concept_name = next((g for g in match_groups if g), "")
        if concept_name and len(concept_name) > 2:
            cid = g.add_node(concept_name, node_type="concept", source=source_url)
            g.add_edge(cid, src_id, "derived_from", weight=0.5,
                       evidence=f"从{source_url[:40]}提取")


def rebuild_clusters() -> list[KnowledgeCluster]:
    """Periodic maintenance: re-detect clusters. Call after significant changes."""
    g = get_graph()
    return g.detect_clusters()
