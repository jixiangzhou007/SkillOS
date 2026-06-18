"""Session-scoped extraction drafts — never written to the public skills/ tree."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

_DRAFT_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "session_drafts"


def _safe_id(session_id: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", session_id.strip())[:128] or "anonymous"


def _path(session_id: str) -> Path:
    return _DRAFT_ROOT / f"{_safe_id(session_id)}.json"


def save_session_draft(session_id: str, name: str, content: str, *, goal: str = "") -> None:
    """Persist in-progress draft under data/session_drafts/ (not skills/)."""
    if not session_id:
        return
    _DRAFT_ROOT.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "session_id": session_id,
        "name": name,
        "content": content,
        "goal": goal,
        "updated_at": time.time(),
    }
    try:
        _path(session_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        _log.debug("Session draft write skipped: %s", exc)


def load_session_draft(session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    path = _path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def clear_session_draft(session_id: str) -> None:
    if not session_id:
        return
    try:
        _path(session_id).unlink(missing_ok=True)
    except OSError:
        _log.debug("Session draft clear skipped", exc_info=True)
