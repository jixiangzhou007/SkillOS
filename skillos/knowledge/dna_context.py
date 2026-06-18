"""Unified DNA context builder — single injection entry for extraction prompts.

Layer 0 (philosophical DNA) owns methodology; taxonomy supplies domain only.
Replaces dual injection of taxonomy.methodology + philosophical_dna in agent paths.
"""


from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillos.knowledge.philosophical_dna import (
    PhilosophicalDNA,
    build_philosophical_context,
    cross_domain_conflict_check,
    detect_philosophical_dna,
)
from skillos.knowledge.taxonomy import (
    Domain,
    detect_domain,
    detect_methodology,
    domain_classification_context,
)

# philosophical_dna.method_id → taxonomy.Methodology.key (YAML backward compat)
PHILOSOPHICAL_TO_TAXONOMY: dict[str, str] = {
    "pdca": "business-process",
    "ooda": "diagnostic",
    "scientific-method": "scientific",
    "dialectical": "diagnostic",
    "reductionist": "engineering",
    "pragmatic": "design-thinking",
}

TAXONOMY_TO_PHILOSOPHICAL: dict[str, str] = {
    "business-process": "pdca",
    "diagnostic": "ooda",
    "scientific": "scientific-method",
    "engineering": "reductionist",
    "design-thinking": "pragmatic",
    "creative": "pragmatic",
}


@dataclass
class DnaDetection:
    """Unified detection result for domain + methodology layers."""

    domain: Domain | None
    philosophical: list[PhilosophicalDNA]
    taxonomy_methodology_key: str | None = None
    taxonomy_methodology_label: str | None = None
    conflicts: list[str] | None = None

    def to_meta(self) -> dict[str, Any]:
        """YAML frontmatter fields for skill save."""
        meta: dict[str, Any] = {}
        if self.domain:
            meta["domain"] = self.domain.key
            meta["domain_label"] = self.domain.name
        if self.philosophical:
            primary = self.philosophical[0]
            meta["philosophical_dna"] = primary.method_id
            meta["philosophical_dna_label"] = primary.name
            if len(self.philosophical) > 1:
                meta["philosophical_dna_secondary"] = [
                    p.method_id for p in self.philosophical[1:3]
                ]
        if self.taxonomy_methodology_key:
            meta["methodology"] = self.taxonomy_methodology_key
            if self.taxonomy_methodology_label:
                meta["methodology_label"] = self.taxonomy_methodology_label
        return meta


def detect_dna(topic: str, content: str = "") -> DnaDetection:
    """Detect domain (taxonomy) + methodology (philosophical DNA, single source)."""
    domain = detect_domain(topic, content)
    domain_key = domain.key if domain else ""
    philosophical = detect_philosophical_dna(topic, content, domain_key=domain_key)

    tax_key: str | None = None
    tax_label: str | None = None
    if philosophical:
        tax_key = PHILOSOPHICAL_TO_TAXONOMY.get(philosophical[0].method_id)
        if tax_key:
            tax_label = philosophical[0].name
    if not tax_key:
        legacy = detect_methodology(topic, content)
        if legacy:
            tax_key = legacy.key
            tax_label = legacy.name
            if not philosophical:
                philo_id = TAXONOMY_TO_PHILOSOPHICAL.get(legacy.key)
                if philo_id:
                    from skillos.knowledge.philosophical_dna import get_philosophical_dna
                    p = get_philosophical_dna(philo_id)
                    if p:
                        philosophical = [p]

    conflicts = cross_domain_conflict_check(philosophical) if len(philosophical) > 1 else []
    return DnaDetection(
        domain=domain,
        philosophical=philosophical,
        taxonomy_methodology_key=tax_key,
        taxonomy_methodology_label=tax_label,
        conflicts=conflicts or None,
    )


def build_domain_context(topic: str, content: str = "") -> str:
    """Domain-only context (no methodology — use build_dna_context for full)."""
    return domain_classification_context(topic, content)


def build_dna_context(topic: str, content: str = "", *, compact: bool = False) -> str:
    """Single injection block: domain + philosophical methodology (+ conflicts)."""
    det = detect_dna(topic, content)
    parts: list[str] = []

    if det.domain:
        if compact:
            parts.append(
                f"领域: {det.domain.name} | 证据标准: {det.domain.evidence_standard}"
            )
        else:
            dc = domain_classification_context(topic, content)
            if dc:
                parts.append(dc.strip())

    if det.philosophical:
        if compact:
            primary = det.philosophical[0]
            pattern_preview = " → ".join(primary.pattern[:3])
            if len(primary.pattern) > 3:
                pattern_preview += " → …"
            parts.append(
                f"方法论: {primary.name} ({pattern_preview}) | "
                f"证据标准: {primary.evidence_standard}"
            )
            if len(det.philosophical) > 1:
                others = ", ".join(p.name for p in det.philosophical[1:3])
                parts.append(f"辅助方法论: {others}")
        else:
            parts.append(build_philosophical_context(det.philosophical).strip())

    if det.conflicts:
        parts.append("⚠️ 方法论冲突（需在萃取中确认主导模式）: " + " | ".join(det.conflicts[:2]))

    return "\n".join(parts) if parts else ""


def build_dna_hint(topic: str, content: str = "") -> str:
    """One-line hint for inline explore/refine prompts."""
    return build_dna_context(topic, content, compact=True)


def build_domain_template_context(topic: str, content: str = "") -> str:
    """Multi-domain template competition block for extraction prompts."""
    from skillos.skills.domain_templates import format_competition_notice, resolve_domain_competition

    comp = resolve_domain_competition(f"{topic} {content[:1500]}", top_k=3)
    if not comp.primary:
        return ""
    parts = [f"领域模板（主）: {comp.primary.title} ({comp.primary.template_id})"]
    if comp.secondary:
        alts = ", ".join(f"{s.template.title}({s.score})" for s in comp.secondary[:2])
        parts.append(f"次要继承: {alts}")
    notice = format_competition_notice(comp).strip()
    if notice:
        parts.append(notice)
    return "\n".join(parts)


def primary_philosophical_id(topic: str, content: str = "") -> str | None:
    det = detect_dna(topic, content)
    return det.philosophical[0].method_id if det.philosophical else None


def _normalize_weights(count: int) -> list[float]:
    if count <= 0:
        return []
    raw = [1.0 / (i + 1) for i in range(count)]
    total = sum(raw)
    return [round(w / total, 2) for w in raw]


def build_dna_lineage(
    name: str,
    content: str = "",
    *,
    domain_template_id: str | None = None,
    domain_template_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build nested dna_lineage block for SKILL.md frontmatter."""
    from skillos.knowledge.dna_store import get_template_version

    det = detect_dna(name, content)
    philo_weights = _normalize_weights(len(det.philosophical))
    philosophical = [
        {"id": p.method_id, "weight": philo_weights[i]}
        for i, p in enumerate(det.philosophical[:3])
    ]

    comp = None
    if domain_template_ids:
        template_ids = list(domain_template_ids)
    elif domain_template_id:
        template_ids = [domain_template_id]
    else:
        from skillos.skills.domain_templates import resolve_domain_competition
        comp = resolve_domain_competition(f"{name} {content[:2000]}", top_k=3)
        if comp.primary:
            template_ids = [comp.primary.template_id] + [
                s.template.template_id for s in comp.secondary
            ]
        else:
            template_ids = []

    score_map: dict[str, int] = {}
    if comp:
        for s in comp.all_scored:
            if s.template.template_id in template_ids:
                score_map[s.template.template_id] = s.score

    if score_map:
        total = sum(score_map.get(tid, 1) for tid in template_ids) or 1
        domain_weights = [round(score_map.get(tid, 1) / total, 2) for tid in template_ids]
    else:
        domain_weights = _normalize_weights(len(template_ids))
    domain = [
        {
            "id": tid,
            "version": get_template_version(tid),
            "weight": domain_weights[i] if i < len(domain_weights) else 0.1,
            "primary": i == 0,
        }
        for i, tid in enumerate(template_ids)
    ]

    lineage: dict[str, Any] = {
        "philosophical": philosophical,
        "domain": domain,
        "detected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if det.conflicts:
        lineage["conflicts"] = det.conflicts
    if det.domain:
        lineage["domain_key"] = det.domain.key
    if comp:
        if comp.conflicts:
            existing = lineage.get("conflicts") or []
            lineage["conflicts"] = existing + comp.conflicts
        if comp.ambiguous:
            lineage["domain_ambiguous"] = True
    return lineage


# ── Philosophical DNA stability tracking ────────────────────

_DNA_STATE_PATH = Path(__file__).parent.parent.parent / "data" / "philosophical_dna_state.json"


def _load_dna_state() -> dict[str, dict]:
    if not _DNA_STATE_PATH.exists():
        return {}
    try:
        return __import__('json').loads(_DNA_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_dna_state(state: dict[str, dict]) -> None:
    _DNA_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DNA_STATE_PATH.write_text(
        __import__('json').dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def track_philosophical_dna_contribution(topic: str, content: str = "", moe_score: int = 0) -> dict:
    """Track a successful skill creation against its philosophical DNA lineage.

    Updates stability and derived_from_skills counters. Persists to disk so
    values survive server restarts. Only counts skills with MoE score >= 70.
    """
    if moe_score < 70:
        return {"tracked": False, "reason": f"MoE score {moe_score} < 70"}

    det = detect_dna(topic, content)
    if not det.philosophical:
        return {"tracked": False, "reason": "no philosophical DNA detected"}

    state = _load_dna_state()
    updated = []
    for p in det.philosophical:
        entry = state.get(p.method_id, {"stability": p.stability, "derived_from_skills": 0})
        entry["derived_from_skills"] = entry.get("derived_from_skills", 0) + 1
        # Stability increases with more evidence (diminishing returns, max 0.99)
        entry["stability"] = min(0.99, entry["stability"] + 0.01)
        state[p.method_id] = entry
        updated.append(p.method_id)

    _save_dna_state(state)

    # Also update in-memory for this session
    from skillos.knowledge.philosophical_dna import PHILOSOPHICAL_DNA
    for mid in updated:
        if mid in PHILOSOPHICAL_DNA:
            e = state[mid]
            PHILOSOPHICAL_DNA[mid].stability = e["stability"]
            PHILOSOPHICAL_DNA[mid].derived_from_skills = e["derived_from_skills"]

    return {"tracked": True, "updated": updated, "state": state}


def get_dna_stability_report() -> dict:
    """Load persisted stability state, merged with baseline from code."""
    from skillos.knowledge.philosophical_dna import PHILOSOPHICAL_DNA
    persisted = _load_dna_state()
    report = {}
    for mid, dna in PHILOSOPHICAL_DNA.items():
        p = persisted.get(mid, {})
        report[mid] = {
            "name": dna.name,
            "baseline_stability": dna.stability,
            "effective_stability": p.get("stability", dna.stability),
            "derived_from_skills": p.get("derived_from_skills", 0),
            "last_updated": p.get("last_updated", ""),
        }
    return report
def build_skill_dna_meta(
    name: str,
    content: str = "",
    *,
    domain_template_id: str | None = None,
    domain_template_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Flat meta fields + nested dna_lineage for save_skill frontmatter."""
    det = detect_dna(name, content)
    meta = det.to_meta()
    meta["dna_lineage"] = build_dna_lineage(
        name,
        content,
        domain_template_id=domain_template_id,
        domain_template_ids=domain_template_ids,
    )
    return meta
