"""Knowledge Lineage — skill precipitation events tracking."""

import json
import time
import uuid

from .lineage_types import LINEAGE_DIR

SKILL_EVENTS_PATH = LINEAGE_DIR / "skill_precipitations.jsonl"


def record_skill_precipitation(
    skill_name: str,
    *,
    session_id: str = "",
    channel: str = "",
    chat_id: str = "",
    user_id: str = "",
    source: str = "",
) -> dict:
    """Append a skill creation event with IM contributor context."""
    event = {
        "event_id": f"sp_{uuid.uuid4().hex[:10]}",
        "skill_name": skill_name,
        "session_id": session_id,
        "channel": channel,
        "chat_id": chat_id,
        "user_id": user_id,
        "source": source,
        "created_at": time.time(),
    }
    SKILL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SKILL_EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def query_skill_precipitations(
    skill_name: str = "",
    chat_id: str = "",
    user_id: str = "",
    session_id: str = "",
    limit: int = 50,
) -> list[dict]:
    """Query skill precipitation lineage events."""
    if not SKILL_EVENTS_PATH.exists():
        return []
    results: list[dict] = []
    for line in SKILL_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if skill_name and ev.get("skill_name") != skill_name:
            continue
        if chat_id and ev.get("chat_id") != chat_id:
            continue
        if user_id and ev.get("user_id") != user_id:
            continue
        if session_id and ev.get("session_id") != session_id:
            continue
        results.append(ev)
    return results[-limit:]


def format_skill_lineage(skill_name: str) -> str:
    """Human-readable lineage for a skill."""
    events = query_skill_precipitations(skill_name=skill_name)
    if not events:
        return f"No precipitation lineage for skill '{skill_name}'."
    lines = [f"Skill lineage: {skill_name} ({len(events)} event(s))"]
    for ev in events:
        who = ev.get("user_id") or "unknown"
        chat = ev.get("chat_id") or "-"
        sess = ev.get("session_id") or "-"
        ch = ev.get("channel") or "-"
        lines.append(
            f"- [{ev.get('event_id')}] channel={ch} user={who} chat={chat} session={sess}"
        )
    return "\n".join(lines)
