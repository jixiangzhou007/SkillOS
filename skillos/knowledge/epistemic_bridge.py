"""Epistemic bridge — connect skill documents to the epistemology engine.

Extracts actionable claims from SKILL.md sections, records them via
record_claim(), optionally runs Popper-style falsification, and writes
epistemic metadata back into skill frontmatter + body annotations.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from skillos.knowledge.epistemology import (
    EpistemicClaim,
    EpistemicLevel,
    get_store,
    record_claim,
)

_log = logging.getLogger(__name__)

_CLAIM_SECTIONS = ("s_body", "s_route", "s_trigger", "s_params", "s_appendix")
_MIN_CLAIM_LEN = 12
_MAX_CLAIMS = 40


@dataclass
class EpistemicSummary:
    """Result of processing a skill through the epistemology pipeline."""

    skill_name: str = ""
    source: str = ""
    source_type: str = ""
    total: int = 0
    verified: int = 0
    pending: int = 0
    preferences: int = 0
    errors: int = 0
    claim_ids: list[str] = field(default_factory=list)
    pending_ids: list[str] = field(default_factory=list)

    def to_meta(self) -> dict:
        return {
            "epistemic": {
                "source": self.source,
                "source_type": self.source_type,
                "total_claims": self.total,
                "verified": self.verified,
                "pending": self.pending,
                "preferences": self.preferences,
                "errors": self.errors,
                "claim_ids": self.claim_ids,
                "pending_ids": self.pending_ids,
                "processed_at": time.time(),
            }
        }

    def user_footer(self) -> str:
        if self.total == 0:
            return ""
        return (
            f"\n\n---\n"
            f"📊 **认识论状态**：已验证 **{self.verified}** 条 · "
            f"待确认 **{self.pending}** 条 · 共提取 **{self.total}** 条声明"
        )


def extract_claims_from_skill(body: str) -> list[tuple[str, str]]:
    """Extract (section, claim_text) pairs from skill markdown body."""
    claims: list[tuple[str, str]] = []
    seen: set[str] = set()
    current_section = "general"

    for line in body.splitlines():
        header = re.match(r"^##\s+(.+)", line.strip())
        if header:
            title = header.group(1).strip().lower().replace(" ", "_").replace("（", "_").replace("）", "")
            current_section = title.split("_")[0] if title else "general"
            if not any(current_section.startswith(s) for s in _CLAIM_SECTIONS):
                if "body" in title or "步骤" in title:
                    current_section = "s_body"
                elif "route" in title or "决策" in title:
                    current_section = "s_route"
                elif "trigger" in title or "触发" in title:
                    current_section = "s_trigger"
                elif "param" in title or "参数" in title:
                    current_section = "s_params"
            continue

        if current_section == "认识论状态" or "认识论" in current_section:
            continue

        candidate = _line_to_claim(line)
        if not candidate:
            continue

        key = candidate[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        claims.append((current_section, candidate))

        if len(claims) >= _MAX_CLAIMS:
            break

    return claims


def _line_to_claim(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("<!--"):
        return ""

    if stripped.startswith("|") and stripped.count("|") >= 3:
        if re.match(r"^\|[-:\s|]+\|$", stripped):
            return ""
        cells = [c.strip() for c in stripped.strip("|").split("|") if c.strip()]
        if len(cells) >= 2:
            return f"{cells[0]} → {cells[1]}"
        return cells[0] if cells else ""

    m = re.match(r"^(?:\d+\.|[-*•]|\*\*步骤\d+[：:])\s*(.+)", stripped)
    if m:
        text = m.group(1).strip()
    elif stripped.startswith("IF ") or stripped.lower().startswith("if "):
        text = stripped
    else:
        return ""

    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    if len(text) < _MIN_CLAIM_LEN:
        return ""
    return text[:500]


def apply_epistemics_to_skill(
    body: str,
    skill_name: str,
    source: str = "",
    source_type: str = "llm_generated",
    llm_args: tuple | None = None,
    *,
    run_falsify: bool = True,
) -> tuple[str, EpistemicSummary]:
    """Record claims, optionally falsify, annotate body, return summary."""
    summary = EpistemicSummary(
        skill_name=skill_name,
        source=source,
        source_type=source_type,
    )
    pairs = extract_claims_from_skill(body)
    if not pairs:
        return body, summary

    store = get_store()
    new_claims: list[EpistemicClaim] = []

    for section, text in pairs:
        claim = record_claim(
            content=text,
            source=source or skill_name,
            source_type=source_type,
            skill_name=skill_name,
            llm_args=llm_args,
        )
        if section not in claim.tags:
            claim.tags.append(section)
        new_claims.append(claim)
        summary.claim_ids.append(claim.claim_id)

    should_falsify = run_falsify and llm_args and len(llm_args) > 0 and llm_args[0]
    if should_falsify:
        for claim in new_claims:
            if claim.level == EpistemicLevel.EXPERIENCE:
                store._falsify_claim(claim, llm_args)
                if claim.promote_to_knowledge():
                    _log.info("Promoted after falsify: %s", claim.content[:60])
        store.save()

    for claim in new_claims:
        refreshed = store.claims.get(claim.claim_id, claim)
        if refreshed.is_knowledge:
            summary.verified += 1
        elif refreshed.level == EpistemicLevel.EXPERIENCE:
            summary.pending += 1
            summary.pending_ids.append(refreshed.claim_id)
        elif refreshed.level == EpistemicLevel.PREFERENCE:
            summary.preferences += 1
        elif refreshed.level == EpistemicLevel.ERROR:
            summary.errors += 1
        elif refreshed.level == EpistemicLevel.EVIDENCE:
            summary.pending += 1
            summary.pending_ids.append(refreshed.claim_id)
        else:
            summary.pending += 1
            summary.pending_ids.append(refreshed.claim_id)

    summary.total = len(new_claims)
    annotated = _inject_epistemic_section(body, new_claims, store)
    return annotated, summary


def _inject_epistemic_section(
    body: str,
    claims: list[EpistemicClaim],
    store,
) -> str:
    """Append or replace ## 认识论状态 section with current claim levels."""
    if "## 认识论状态" in body:
        body = re.sub(r"\n## 认识论状态[\s\S]*$", "", body.rstrip())

    verified_lines: list[str] = []
    pending_lines: list[str] = []

    for claim in claims:
        refreshed = store.claims.get(claim.claim_id, claim)
        snippet = refreshed.content[:120]
        if refreshed.is_knowledge:
            verified_lines.append(f"- ✅ {snippet}")
        elif refreshed.level == EpistemicLevel.EXPERIENCE:
            pending_lines.append(f"- ⏳ [待验证] {snippet} (`{refreshed.claim_id}`)")
        elif refreshed.level in (EpistemicLevel.EVIDENCE, EpistemicLevel.PREFERENCE):
            pending_lines.append(
                f"- 📋 [{refreshed.level.value}] {snippet} (`{refreshed.claim_id}`)"
            )

    if not verified_lines and not pending_lines:
        return body

    parts = ["\n\n## 认识论状态\n", "> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。\n"]
    if verified_lines:
        parts.append("\n### 已验证\n")
        parts.extend(line + "\n" for line in verified_lines[:15])
    if pending_lines:
        parts.append("\n### 待确认\n")
        parts.extend(line + "\n" for line in pending_lines[:15])

    return body.rstrip() + "".join(parts)


def format_epistemic_api_payload(meta: dict) -> dict:
    """Normalize epistemic block from skill YAML for API/MCP responses."""
    ep = meta.get("epistemic") if meta else None
    if not ep:
        return {"verified": 0, "pending": 0, "total_claims": 0, "pending_ids": []}
    return {
        "verified": ep.get("verified", 0),
        "pending": ep.get("pending", 0),
        "total_claims": ep.get("total_claims", 0),
        "pending_ids": ep.get("pending_ids", []),
        "source_type": ep.get("source_type", ""),
    }


def list_pending_claims_detail(skill_name: str = "") -> list[dict]:
    """Pending claims with text for UI confirmation (Sprint 4)."""
    from skillos.knowledge.epistemology import EpistemicLevel, get_store

    store = get_store()
    pending_levels = {EpistemicLevel.EXPERIENCE, EpistemicLevel.EVIDENCE}
    rows: list[dict] = []
    for claim in store.claims.values():
        if claim.level not in pending_levels or not claim.is_current:
            continue
        if skill_name and claim.skill_name != skill_name:
            continue
        rows.append({
            "claim_id": claim.claim_id,
            "content": claim.content,
            "skill_name": claim.skill_name,
            "section": getattr(claim, "section", ""),
            "level": claim.level.value if hasattr(claim.level, "value") else str(claim.level),
            "confidence": claim.confidence,
        })
    return rows


def confirm_claims(claim_ids: list[str], llm_args: tuple | None = None) -> int:
    """User-confirmed promotion: Experience → Knowledge (Phase 3 hook)."""
    return confirm_claims_detailed(claim_ids, llm_args).promoted


@dataclass
class ConfirmResult:
    promoted: int = 0
    claim_ids: list[str] = field(default_factory=list)
    synced_skills: list[str] = field(default_factory=list)


def confirm_claims_detailed(
    claim_ids: list[str],
    llm_args: tuple | None = None,
    *,
    sync_skills: bool = True,
) -> ConfirmResult:
    """Promote claims and optionally refresh affected SKILL.md epistemic sections."""
    store = get_store()
    promoted_ids: list[str] = []
    for cid in claim_ids:
        claim = store.claims.get(cid)
        if not claim or claim.level not in (
            EpistemicLevel.EXPERIENCE,
            EpistemicLevel.EVIDENCE,
        ):
            continue
        claim.level = EpistemicLevel.KNOWLEDGE
        claim.confidence = max(claim.confidence, 0.85)
        claim.expires_at = time.time() + (90 * 86400)
        if "user_confirmed" not in claim.tags:
            claim.tags.append("user_confirmed")
        claim.last_verified = time.time()
        promoted_ids.append(cid)
    if promoted_ids:
        store.save()

    synced: list[str] = []
    if sync_skills and promoted_ids:
        synced = _sync_skills_for_claims(promoted_ids)

    return ConfirmResult(
        promoted=len(promoted_ids),
        claim_ids=promoted_ids,
        synced_skills=synced,
    )


def _sync_skills_for_claims(claim_ids: list[str]) -> list[str]:
    store = get_store()
    skill_names: set[str] = set()
    for cid in claim_ids:
        claim = store.claims.get(cid)
        if claim and claim.skill_name:
            skill_names.add(claim.skill_name)
    synced: list[str] = []
    for name in sorted(skill_names):
        if refresh_skill_epistemic_state(name):
            synced.append(name)
    return synced


def refresh_skill_epistemic_state(skill_name: str) -> bool:
    """Rewrite skill YAML meta + ``## 认识论状态`` from current store levels."""
    from skillos.skills import skill_store

    try:
        raw = skill_store.load_skill_raw(skill_name)
    except FileNotFoundError:
        return False

    meta = dict(raw.get("meta") or {})
    body = raw.get("body") or ""
    ep = meta.get("epistemic") or {}
    claim_ids: list[str] = list(ep.get("claim_ids") or [])

    store = get_store()
    if not claim_ids:
        claim_ids = [
            c.claim_id
            for c in store.claims.values()
            if c.skill_name == skill_name
        ]

    claims = [store.claims[cid] for cid in claim_ids if cid in store.claims]
    if not claims:
        return False

    summary = EpistemicSummary(
        skill_name=skill_name,
        source=ep.get("source", skill_name),
        source_type=ep.get("source_type", "llm_generated"),
    )
    for claim in claims:
        summary.claim_ids.append(claim.claim_id)
        if claim.is_knowledge:
            summary.verified += 1
        elif claim.level == EpistemicLevel.EXPERIENCE:
            summary.pending += 1
            summary.pending_ids.append(claim.claim_id)
        elif claim.level == EpistemicLevel.PREFERENCE:
            summary.preferences += 1
        elif claim.level == EpistemicLevel.ERROR:
            summary.errors += 1
        else:
            summary.pending += 1
            summary.pending_ids.append(claim.claim_id)
    summary.total = len(claims)

    annotated = _inject_epistemic_section(body, claims, store)
    meta.update(summary.to_meta())
    skill_store.save_skill(skill_name, annotated, meta=meta, epistemic=False)
    return True
