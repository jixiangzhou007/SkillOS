"""Unified playbook + PURPOSE context for knowledge ingest and extraction.

LLM Wiki: every ingest/query should read the team's PURPOSE and playbook.
"""


from skillos.knowledge.playbook import get_playbook_context, get_purpose_context


def get_ingest_context(
    *,
    chat_id: str = "",
    session_id: str = "",
    max_playbook_chars: int = 2000,
) -> str:
    """Playbook + PURPOSE blocks for LLM prompts."""
    parts: list[str] = []
    playbook = get_playbook_context(
        max_chars=max_playbook_chars,
        chat_id=chat_id,
        session_id=session_id,
    )
    if playbook:
        parts.append(playbook.strip())
    purpose = get_purpose_context()
    if purpose:
        parts.append(purpose.strip())
    if not parts:
        return ""
    return "\n".join(parts) + "\n"
