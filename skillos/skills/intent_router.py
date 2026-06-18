"""Unified precipitation intent routing — Phase 3 protocol.

Single source of truth for IM / API / MCP trigger phrases.
Conservative matching: when unsure, route to ``chat`` (not forced extract).

See also: ``docs/USER_GUIDE.md``, ``skillos/skills/dispatcher.py`` (skill execution layer).
"""


import re
from enum import Enum


class DispatchIntent(str, Enum):
    """High-level user intent for ``/api/skills/dispatch``."""

    LEARN_URL = "learn_url"       # detected via URL regex in API layer
    INGEST = "ingest"             # handled by ``/api/skills/ingest`` upload
    EXTRACT = "extract"           # start/continue skill extraction
    CONFIRM_CLAIMS = "confirm_claims"  # promote Experience → Knowledge
    PLAYBOOK = "playbook"         # team cold-start interview
    CHAT = "chat"                 # default conversational fallback


# ── Trigger tables (conservative — prefer false negatives over false positives) ──

EXTRACT_TRIGGERS: tuple[str, ...] = (
    "沉淀",
    "做成 skill",
    "做成skill",
    "整理成标准",
    "技能",
    "skill",
    "流程",
    "创建skill",
    "新建技能",
    "萃取",
    "提炼",
    "写下来",
    "帮我创建",
    "帮我写",
)

CONFIRM_PHRASES: tuple[str, ...] = (
    "确认待审",
    "采纳待审",
    "确认全部",
    "采纳全部",
    "晋升待审",
    "confirm pending",
    "confirm all",
)

PLAYBOOK_TRIGGERS: tuple[str, ...] = (
    "playbook",
    "冷启动",
    "团队手册",
    "团队规范",
    "风格指南",
    "术语表",
)

_CLAIM_ID_RE = re.compile(r"(?:claim_|ec_)[a-z0-9_\-]+", re.I)
_CONFIRM_INDEX_RE = re.compile(
    r"^(?:确认|采纳|promote|confirm)\s+([\d,\s和、\-]+)",
    re.I,
)
_SKILL_HINT_RE = re.compile(
    r"(?:技能|skill)[:：\s]+([^\s，,。.!！?？]+)",
    re.I,
)


def is_meta_extraction_question(message: str) -> bool:
    """User is asking about the extraction process, not naming a new skill."""
    msg = message.strip()
    if not msg:
        return False
    lower = msg.lower()
    cues = (
        "你不是", "是不是", "有没有在", "怎么还", "为什么还", "什么时候",
        "怎么不", "还没", "在干嘛", "在做什么", "搞什么", "生成了吗",
        "aren't you", "still extracting",
    )
    if any(c in lower for c in cues):
        if "沉淀" in msg or "技能" in msg or "skill" in lower or "?" in msg or "？" in msg:
            return True
    if msg.endswith(("吗", "?", "？")) and len(msg) <= 48:
        if ("沉淀" in msg or "技能" in msg) and any(
            c in msg for c in ("不是", "怎么", "为什么", "啥", "吗", "成功", "好了", "完成")
        ):
            return True
    return False


def classify_message_intent(message: str, *, extraction_active: bool = False) -> DispatchIntent:
    """Classify a user message into a dispatch intent (no URL/file context)."""
    msg = message.strip()
    if not msg:
        return DispatchIntent.CHAT

    lower = msg.lower()

    if _is_confirm_intent(msg, lower):
        return DispatchIntent.CONFIRM_CLAIMS

    if any(kw in lower for kw in PLAYBOOK_TRIGGERS):
        return DispatchIntent.PLAYBOOK

    if extraction_active and is_meta_extraction_question(msg):
        return DispatchIntent.EXTRACT

    if any(kw in lower for kw in EXTRACT_TRIGGERS):
        return DispatchIntent.EXTRACT

    return DispatchIntent.CHAT


def _is_confirm_intent(msg: str, lower: str) -> bool:
    if any(p in lower for p in CONFIRM_PHRASES):
        return True
    if _CONFIRM_INDEX_RE.match(msg.strip()):
        return True
    if _CLAIM_ID_RE.search(msg):
        return True
    return False


def extract_skill_hint(message: str) -> str:
    """Optional skill name hint from message, e.g. ``技能: refund-flow``."""
    m = _SKILL_HINT_RE.search(message)
    return m.group(1).strip() if m else ""


def list_pending_for_confirm(skill_name: str = "") -> list[str]:
    """Return pending claim IDs (Experience or Evidence), optionally scoped to one skill."""
    from skillos.knowledge.epistemology import EpistemicLevel, get_store

    store = get_store()
    pending_levels = {EpistemicLevel.EXPERIENCE, EpistemicLevel.EVIDENCE}
    result = [
        c for c in store.claims.values()
        if c.level in pending_levels and c.is_current
    ]
    if skill_name:
        result = [c for c in result if c.skill_name == skill_name]
    return [c.claim_id for c in result]


def parse_confirm_claim_selection(message: str, pending_ids: list[str]) -> list[str]:
    """Resolve user message to concrete claim IDs.

    Supports:
    - ``确认待审`` / ``确认全部`` → all *pending_ids*
    - ``确认 1,2`` / ``采纳 1和3`` → 1-based indices into *pending_ids*
    - explicit ``claim_…`` IDs in message
    """
    msg = message.strip()
    lower = msg.lower()

    explicit = _CLAIM_ID_RE.findall(msg)
    if explicit:
        return list(dict.fromkeys(explicit))

    if any(p in lower for p in CONFIRM_PHRASES):
        return list(pending_ids)

    m = _CONFIRM_INDEX_RE.match(msg)
    if m and pending_ids:
        indices: list[int] = []
        for part in re.split(r"[,，和、\s]+", m.group(1)):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                bounds = part.split("-", 1)
                if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                    start, end = int(bounds[0]), int(bounds[1])
                    indices.extend(range(start, end + 1))
                continue
            if part.isdigit():
                indices.append(int(part))
        selected: list[str] = []
        for idx in indices:
            if 1 <= idx <= len(pending_ids):
                cid = pending_ids[idx - 1]
                if cid not in selected:
                    selected.append(cid)
        return selected

    return []
