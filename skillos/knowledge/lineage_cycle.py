"""Knowledge Lineage — full knowledge cycle and graph synchronization."""

import logging
import re
import time

from .lineage_core import detect_surprise, load_lineage, save_lineage
from .lineage_graph import LineageGraph
from .lineage_types import KnowledgeItem
from .lineage_wisdom import extract_wisdom, run_consolidation_cycle, trigger_pattern_mining

_log = logging.getLogger(__name__)


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
        from skillos.knowledge.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
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
        from skillos.knowledge.extractor import extract_knowledge, load_all_knowledge, save_knowledge, verify_knowledge
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
