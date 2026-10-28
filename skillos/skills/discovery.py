"""Skill discovery layers + invocation policy (DeepSeek Harness–inspired).

Harness (dsh) treats skills as discoverable instructions with:
- layered providers / rank order
- modelInvocable vs userInvocable
- progressive disclosure (summary first, body on demand)

SkillOS maps that onto Dual Gate Trust Tier without becoming a coding runtime.
"""

from __future__ import annotations

from typing import Any

from skillos.skills.system_skills import SYSTEM_SKILL_NAMES

# Discovery ranks (lower = higher priority), aligned with dsh local scan spirit
SOURCE_RANKS: dict[str, int] = {
    "system": 100,  # bundled / create-mode references
    "workspace": 200,  # tenant / local 「我的」
    "hub": 300,  # installed from SkillHub
    "unknown": 900,
}

SOURCE_LABELS_ZH: dict[str, str] = {
    "system": "系统",
    "workspace": "工作区",
    "hub": "市场安装",
    "unknown": "其他",
}


def resolve_skill_source(name: str, meta: dict[str, Any] | None = None) -> str:
    """Classify skill origin for list/UI badges."""
    if name in SYSTEM_SKILL_NAMES:
        return "system"
    m = meta or {}
    st = str(m.get("source_type") or m.get("skillos_source_type") or "").strip().lower()
    if st in ("marketplace", "hub", "skillhub"):
        return "hub"
    if str(m.get("origin") or "").strip().lower() in ("hub", "marketplace"):
        return "hub"
    return "workspace"


def source_rank(source: str) -> int:
    return SOURCE_RANKS.get(source, SOURCE_RANKS["unknown"])


def invocation_policy(trust_tier: str, *, source: str = "workspace") -> dict[str, bool]:
    """Map Trust Tier → whether model / human catalogs should include the skill.

    - draft: human can open/edit; model catalog excludes (avoid dirty inheritance)
    - provisional: model may try (学徒试用); user always can
    - verified: both on
    - system skills: always model+user invocable (tooling)
    """
    if source == "system":
        return {"model_invocable": True, "user_invocable": True}
    tier = str(trust_tier or "draft").strip().lower()
    if tier == "verified":
        return {"model_invocable": True, "user_invocable": True}
    if tier == "provisional":
        return {"model_invocable": True, "user_invocable": True}
    # draft / unknown
    return {"model_invocable": False, "user_invocable": True}


def catalog_summary(
    *,
    name: str,
    description: str = "",
    trust_tier: str = "draft",
    meta: dict[str, Any] | None = None,
    portable_slug: str = "",
) -> dict[str, Any]:
    """Progressive-disclosure card: name + description only (no body)."""
    source = resolve_skill_source(name, meta)
    policy = invocation_policy(trust_tier, source=source)
    return {
        "name": name,
        "description": (description or "")[:240],
        "trust_tier": trust_tier or "draft",
        "source": source,
        "source_label": SOURCE_LABELS_ZH.get(source, source),
        "source_rank": source_rank(source),
        "model_invocable": policy["model_invocable"],
        "user_invocable": policy["user_invocable"],
        "portable_slug": portable_slug or "",
    }


def plugin_vs_skill_hint() -> str:
    """Product copy: Plugin ≠ Skill (dsh / Cordis vocabulary)."""
    return (
        "Skill（技能）是可验证、可安装的说明书；"
        "Plugin / Harness 是运行时能力（工具、沙箱、UI）。"
        "SkillOS 负责出师；DeepSeek Harness / Cursor 负责执行。"
    )
