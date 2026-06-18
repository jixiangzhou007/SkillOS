"""Conversation persistence — SQLite-backed, survives restarts and refreshes.

Zero extra dependencies (sqlite3 is Python stdlib).
Auto-cleans conversations older than 30 days.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "conversations.db"
TTL_DAYS = 30

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _init_tables(_local.conn)
    return _local.conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON conversations(created_at)")
    conn.commit()


def save_message(session_id: str, role: str, content: str) -> None:
    """Persist a single message to the conversation history."""
    if not session_id or not content:
        return
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, time.time()),
        )
        conn.commit()
    except Exception as e:
        _log.warning("Failed to save message: %s", e)


def load_history(session_id: str, limit: int = 50) -> list[dict[str, str]]:
    """Load recent conversation history for a session."""
    if not session_id:
        return []
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
    except Exception as e:
        _log.warning("Failed to load history: %s", e)
        return []


def delete_session_history(session_id: str) -> None:
    """Remove all messages for a session."""
    if not session_id:
        return
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()
    except Exception as e:
        _log.warning("Failed to delete history: %s", e)


def cleanup_old(days: int = TTL_DAYS) -> int:
    """Remove conversations older than N days. Returns count of deleted rows."""
    cutoff = time.time() - (days * 86400)
    try:
        conn = _get_conn()
        cursor = conn.execute("DELETE FROM conversations WHERE created_at < ?", (cutoff,))
        conn.commit()
        count = cursor.rowcount
        if count:
            _log.info("Cleaned up %d old conversation messages", count)
        return count
    except Exception as e:
        _log.warning("Cleanup failed: %s", e)
        return 0
