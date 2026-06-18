"""Helpers for skill extraction dispatch — option buttons, response enrichment."""

from __future__ import annotations

import re

_OPTION_RE = re.compile(r"\[选项\]\s*(.+?)\s*\|\s*(\S+)")


def parse_option_actions(reply: str) -> list[dict[str, str]]:
    """Parse ``[选项] 描述 | action_key`` lines into frontend action buttons."""
    if not reply or "[选项]" not in reply:
        return []
    actions: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in _OPTION_RE.finditer(reply):
        label = m.group(1).strip()
        action = m.group(2).strip()
        if not label or not action or action in seen:
            continue
        seen.add(action)
        actions.append({"label": label, "action": action})
    return actions


def attach_extraction_actions(result: dict, reply: str) -> dict:
    """Add ``actions`` array when reply contains clickable options."""
    actions = parse_option_actions(reply)
    if actions:
        result["actions"] = actions
    return result
