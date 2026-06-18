"""Channel session ID helpers — map IM platforms to SkillOS sessions."""

from __future__ import annotations

import re


def feishu_session_id(chat_id: str, user_id: str) -> str:
    """Stable session key for Feishu group/DM threads (Phase 4 M2)."""
    chat = chat_id.strip()
    user = user_id.strip()
    if not chat or not user:
        raise ValueError("chat_id and user_id are required")
    return f"feishu:{chat}:{user}"


def wechat_session_id(chat_id: str, user_id: str) -> str:
    return f"wechat:{chat_id.strip()}:{user_id.strip()}"


def parse_channel_session(session_id: str) -> dict[str, str] | None:
    """Parse ``feishu:oc_xxx:ou_xxx`` style session IDs."""
    m = re.match(r"^(feishu|wechat):([^:]+):([^:]+)$", session_id.strip())
    if not m:
        return None
    return {"channel": m.group(1), "chat_id": m.group(2), "user_id": m.group(3)}


def resolve_session_id(
    session_id: str = "",
    *,
    channel: str = "",
    chat_id: str = "",
    user_id: str = "",
) -> str:
    """Use explicit session_id or build from channel + chat + user."""
    if session_id.strip():
        return session_id.strip()
    ch = channel.strip().lower()
    if ch == "feishu" and chat_id and user_id:
        return feishu_session_id(chat_id, user_id)
    if ch == "wechat" and chat_id and user_id:
        return wechat_session_id(chat_id, user_id)
    return ""
