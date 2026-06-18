"""Skill Polymorphism — Java-inspired variant system.

Interface  = Skill DNA (principles all variants must satisfy)
Concrete   = Skill Variant (one person's implementation)
@Override  = Step override (same step name, different logic)
Overload   = S_params variation (same skill, different parameter sets)
Epistemic  = Who created this, how verified is it?

When multiple people contribute solutions to the same problem:
  求同 (Commonality) → DNA / Archetype
  存异 (Divergence)  → Variants with epistemic annotations
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

VARIANTS_PATH = Path(__file__).parent / "knowledge" / "skill_variants.json"


@dataclass
class SkillVariant:
    """One person's implementation of a skill archetype."""

    variant_id: str = ""           # unique: <archetype>_<creator>
    archetype: str = ""            # which skill archetype this belongs to
    creator: str = ""              # who created this variant
    creator_role: str = ""         # e.g., "客服主管", "NLP工程师"
    content: str = ""              # the skill document

    # What's different from the base archetype?
    overrides: list[dict] = field(default_factory=list)
    # e.g., [{"step": "S_body.步骤2", "base": "关键词匹配", "override": "语义理解"}]

    # What parameters differ?
    param_overloads: dict[str, str] = field(default_factory=dict)
    # e.g., {"匹配模式": "语义", "回复风格": "正式"}

    # Epistemic annotations
    source: str = ""               # where this came from
    confidence: float = 0.5
    verification_score: float = 0.0
    corroborated_by: list[str] = field(default_factory=list)
    epistemic_level: str = "experience"  # evidence | experience | knowledge

    created_at: float = 0.0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id, "archetype": self.archetype,
            "creator": self.creator, "creator_role": self.creator_role,
            "content": self.content, "overrides": self.overrides,
            "param_overloads": self.param_overloads,
            "source": self.source, "confidence": self.confidence,
            "verification_score": self.verification_score,
            "corroborated_by": self.corroborated_by,
            "epistemic_level": self.epistemic_level,
            "created_at": self.created_at, "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillVariant":
        return cls(
            variant_id=data.get("variant_id", ""),
            archetype=data.get("archetype", ""),
            creator=data.get("creator", ""),
            creator_role=data.get("creator_role", ""),
            content=data.get("content", ""),
            overrides=data.get("overrides", []),
            param_overloads=data.get("param_overloads", {}),
            source=data.get("source", ""),
            confidence=data.get("confidence", 0.5),
            verification_score=data.get("verification_score", 0.0),
            corroborated_by=data.get("corroborated_by", []),
            epistemic_level=data.get("epistemic_level", "experience"),
            created_at=data.get("created_at", 0),
            tags=data.get("tags", []),
        )


class VariantRegistry:
    """Registry of skill variants — same archetype, different implementations."""

    def __init__(self) -> None:
        self.variants: dict[str, SkillVariant] = {}
        self._load()

    def _load(self) -> None:
        if not VARIANTS_PATH.exists():
            return
        try:
            data = json.loads(VARIANTS_PATH.read_text(encoding="utf-8"))
            for vdata in data.get("variants", []):
                v = SkillVariant.from_dict(vdata)
                self.variants[v.variant_id] = v
        except Exception as e:
            _log.warning("Failed to load variants: %s", e)

    def save(self) -> None:
        VARIANTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"variants": [v.to_dict() for v in self.variants.values()]}
        VARIANTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_variant(
        self, archetype: str, creator: str, content: str,
        creator_role: str = "", source: str = "", confidence: float = 0.5,
        epistemic_level: str = "experience",
    ) -> SkillVariant:
        """Register a new variant of an archetype."""
        vid = f"{archetype}_{creator}" if creator else f"{archetype}_{int(time.time())}"

        # If variant already exists for this creator, update it
        if vid in self.variants:
            existing = self.variants[vid]
            existing.content = content
            existing.confidence = confidence
            existing.epistemic_level = epistemic_level
            existing.created_at = time.time()
            self.save()
            return existing

        variant = SkillVariant(
            variant_id=vid, archetype=archetype, creator=creator,
            creator_role=creator_role, content=content,
            source=source, confidence=confidence,
            epistemic_level=epistemic_level, created_at=time.time(),
        )
        self.variants[vid] = variant
        self.save()
        return variant

    def get_variants(self, archetype: str) -> list[SkillVariant]:
        """Get all variants of an archetype."""
        return [v for v in self.variants.values() if v.archetype == archetype]

    def get_knowledge_variants(self, archetype: str) -> list[SkillVariant]:
        """Get only knowledge-level variants (verified, cross-referenced)."""
        return [v for v in self.get_variants(archetype) if v.epistemic_level == "knowledge"]

    def get_creators(self, archetype: str) -> list[str]:
        """List all creators who contributed to this archetype."""
        return list(set(v.creator for v in self.get_variants(archetype) if v.creator))


# ═══════════════════════════════════════════════════════════════
# Variant Comparison — 求同存异
# ═══════════════════════════════════════════════════════════════

def compare_variants(archetype: str) -> dict:
    """Compare all variants of an archetype. Extract commonality and divergence.

    Returns:
        {
            "commonality": ["大家一致同意的部分"],
            "divergence": [{"step": "...", "variants": {"张三": "...", "李四": "..."}}],
            "knowledge_count": N (how many variants are verified knowledge),
            "experience_count": N (how many are still unverified experience),
        }
    """
    reg = VariantRegistry()
    variants = reg.get_variants(archetype)
    if len(variants) < 2:
        return {"commonality": [], "divergence": [], "knowledge_count": 0, "experience_count": 0,
                "message": "只有一个变体，无法比较"}

    # Extract common patterns
    from collections import Counter
    all_steps = []
    for v in variants:
        steps = re.findall(r'^\d+[\.\、)]\s*(.+)', v.content, re.MULTILINE)
        if not steps:
            steps = [l.strip() for l in v.content.split("\n") if len(l.strip()) > 15]
        all_steps.extend(steps[:10])

    # Common phrases appearing across multiple variants
    words = re.findall(r'[\w一-鿿]{2,6}', " ".join(all_steps))
    common_words = [w for w, c in Counter(words).most_common(20) if c >= len(variants) * 0.5]

    # Find divergences: steps where variants differ
    divergences = []
    for v in variants:
        if v.overrides:
            for ov in v.overrides:
                divergences.append({
                    "step": ov.get("step", ""),
                    "creator": v.creator,
                    "base": ov.get("base", ""),
                    "override": ov.get("override", ""),
                })

    knowledge = [v for v in variants if v.epistemic_level == "knowledge"]
    experience = [v for v in variants if v.epistemic_level == "experience"]

    return {
        "archetype": archetype,
        "total_variants": len(variants),
        "creators": reg.get_creators(archetype),
        "commonality": common_words[:10],
        "divergence": divergences[:10],
        "knowledge_count": len(knowledge),
        "experience_count": len(experience),
        "knowledge_creators": [v.creator for v in knowledge],
        "experience_creators": [v.creator for v in experience],
    }


def format_variant_comparison(archetype: str) -> str:
    """Human-readable variant comparison report."""
    result = compare_variants(archetype)
    if result.get("message"):
        return result["message"]

    lines = [f"## 🔀 技能变体比较: {archetype}"]
    lines.append(f"\n{result['total_variants']} 个变体，{len(result['creators'])} 位贡献者")

    if result["commonality"]:
        lines.append(f"\n### 🤝 共识（求同）")
        lines.append(f"所有变体共同认可的要素: {', '.join(result['commonality'][:8])}")

    if result["divergence"]:
        lines.append(f"\n### 🔀 分歧（存异）")
        for d in result["divergence"][:5]:
            lines.append(f"- **{d['creator']}**: {d['step']} → {d['override'][:60]} (基础: {d['base'][:40]})")

    if result["knowledge_count"]:
        lines.append(f"\n### ✅ 已验证知识 ({result['knowledge_count']} 个变体)")
        lines.append(f"贡献者: {', '.join(result['knowledge_creators'])}")

    if result["experience_count"]:
        lines.append(f"\n### 📝 待验证经验 ({result['experience_count']} 个变体)")
        lines.append(f"贡献者: {', '.join(result['experience_creators'])}")
        lines.append("这些变体来自个人经验，尚未经过证伪测试和交叉验证。")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Polymorphic Dispatch — select the right variant
# ═══════════════════════════════════════════════════════════════

def dispatch_variant(archetype: str, context: dict | None = None) -> Optional[SkillVariant]:
    """Polymorphic dispatch: select the best variant based on context.

    Rules:
    1. If context specifies a creator → use that variant
    2. If context specifies parameter preferences → match against overloads
    3. Default → use the highest-confidence knowledge variant
    4. Fallback → use any variant
    """
    reg = VariantRegistry()
    variants = reg.get_variants(archetype)
    if not variants:
        return None

    context = context or {}

    # Rule 1: explicit creator preference
    if context.get("creator"):
        for v in variants:
            if v.creator == context["creator"]:
                return v

    # Rule 2: parameter matching
    if context.get("params"):
        best_match, best_score = None, 0
        for v in variants:
            score = sum(1 for k, val in context["params"].items()
                        if v.param_overloads.get(k) == val)
            if score > best_score:
                best_match, best_score = v, score
        if best_match and best_score > 0:
            return best_match

    # Rule 3: highest-confidence knowledge variant
    knowledge = reg.get_knowledge_variants(archetype)
    if knowledge:
        return max(knowledge, key=lambda v: v.confidence)

    # Rule 4: any variant
    return max(variants, key=lambda v: v.confidence)


def _name_similarity(a: str, b: str) -> float:
    wa = set(re.findall(r"[\w一-鿿]{2,}", a.lower()))
    wb = set(re.findall(r"[\w一-鿿]{2,}", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def find_archetype_for_skill(skill_name: str) -> str:
    """Find an existing archetype name similar to *skill_name*."""
    from skillos.skills import skill_store

    best_name, best_score = "", 0.0
    for name in skill_store.list_skills():
        if name == skill_name:
            continue
        score = _name_similarity(skill_name, name)
        if score > best_score:
            best_name, best_score = name, score
    return best_name if best_score >= 0.45 else ""


def register_precipitation_variant(
    skill_name: str,
    content: str,
    *,
    creator: str = "",
    source: str = "",
) -> str:
    """Register variant after precipitation; return user-facing hint if applicable."""
    archetype = find_archetype_for_skill(skill_name)
    if not archetype:
        return ""

    reg = VariantRegistry()
    creator_id = creator or "anonymous"
    reg.register_variant(
        archetype=archetype,
        creator=creator_id,
        content=content,
        source=source or skill_name,
        confidence=0.5,
        epistemic_level="experience",
    )
    total = len(reg.get_variants(archetype))
    if total >= 2:
        return (
            f"🔀 检测到与「{archetype}」相关的第 {total} 个变体（贡献者 {creator_id}）。"
            f"可说「比较变体 {archetype}」查看求同存异。"
        )
    return ""


def suggest_variant_in_dispatch(skill_name: str, creator: str = "") -> str:
    """Lightweight variant hint for dispatch before save completes."""
    archetype = find_archetype_for_skill(skill_name)
    if not archetype:
        return ""
    reg = VariantRegistry()
    n = len(reg.get_variants(archetype))
    if n >= 1:
        return f"🔀 已有相似技能「{archetype}」，本次沉淀将登记为变体。"
    return f"🔀 发现相似技能「{archetype}」，可考虑登记为变体。"


def auto_detect_variants() -> list[dict]:
    """Scan all skills for potential variants of the same archetype.

    Uses pattern_miner archetypes + content overlap to group skills.
    Returns list of groups that could be variant families.
    """
    from skillos.skills import skill_store
    from skillos.skills.pattern_miner import profile_all_skills

    profiles = profile_all_skills()
    if len(profiles) < 2:
        return []

    # Group by structural similarity
    groups = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            pi, pj = profiles[i], profiles[j]
            # Same archetype indicators: similar step count, similar branch count,
            # same section coverage pattern
            coverage_match = (
                pi.has_trigger == pj.has_trigger and
                pi.has_params == pj.has_params and
                abs(pi.step_count - pj.step_count) <= 2 and
                abs(pi.branch_count - pj.branch_count) <= 2
            )
            if coverage_match:
                groups.append({
                    "skill_a": pi.name, "skill_b": pj.name,
                    "similarity": "same_structure",
                    "suggestion": f"「{pi.name}」和「{pj.name}」可能是同一技能的不同变体",
                })

    return groups
