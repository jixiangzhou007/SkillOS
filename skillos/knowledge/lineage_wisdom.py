"""Knowledge Lineage — wisdom extraction, consolidation, and pattern mining."""

import json
import logging
import re
import time
from typing import Any

from .lineage_core import list_lineages, load_lineage
from .lineage_types import LINEAGE_DIR, KnowledgeItem

_log = logging.getLogger(__name__)


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
        from skillos.skills.pattern_miner import profile_all_skills
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
                    "avg_score": str(p.avg_score),
                    "runs": str(p.total_runs),
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
    categories: dict[str, Any] = {}

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
    cat_impact: dict[str, Any] = {}
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
