"""Agent Factory — create lightweight agents from skill documents.

Each skill can have a private knowledge base. When executing, relevant
KB chunks are retrieved and injected into the prompt.
"""

import logging
from typing import Any

from skillos.config import get_config
from skillos.llm_client import get_client

_log = logging.getLogger(__name__)


def create_agent(skill_doc: str, task: str = "") -> dict[str, Any]:
    """Build an agent from a skill document.

    Returns a dict with system_prompt, model, and metadata ready for execution.
    """
    from skillos.skills.skill_store import get_skill_body
    import re

    body = get_skill_body(skill_doc)
    m = re.search(r"^#\s*(.+?)\s*$", skill_doc, re.MULTILINE)
    name = m.group(1).strip() if m else "unnamed"

    # Search skill's private knowledge base
    kb_context = ""
    try:
        from skillos.knowledge.store import search
        if task:
            chunks = search(name, task, top_k=3)
            if chunks:
                kb_context = "\n\n## Knowledge Base\n" + "\n\n---\n".join(chunks)
    except ImportError:
        pass  # KB module not yet ported

    system_prompt = (
        f"You are the '{name}' skill executor. Follow the S_body workflow strictly. "
        f"Use S_params when available. S_appendix is for reference only. "
        f"If information is insufficient, ask the user.\n\n{body}{kb_context}"
    )

    cfg = get_config()
    return {
        "name": name,
        "system_prompt": system_prompt,
        "skill_doc": skill_doc,
        "model": cfg.model,
    }


def run_agent(agent: dict[str, Any], task: str) -> str:
    """Execute an agent with a task. Returns the agent's response."""
    import time

    client = get_client()
    t0 = time.time()

    try:
        response = client.chat.completions.create(
            model=agent.get("model", get_config().model),
            messages=[
                {"role": "system", "content": agent["system_prompt"]},
                {"role": "user", "content": task},
            ],
            temperature=0.2,
        )
        result = (response.choices[0].message.content or "").strip()
    except Exception as e:
        _log.error("Agent execution failed: %s", e)
        result = f"[Error: {e}]"

    duration = time.time() - t0
    _log.info("Agent '%s' executed in %.2fs", agent.get("name", "?"), duration)
    return result
