"""SkillHub Auth — RBAC user management and audit logging.

Roles: admin > reviewer > publisher > member
  - admin:     full access, manage users, force approve/reject, view all
  - reviewer:  approve/reject pending skills, view review queue
  - publisher: publish skills, sync updates, view own skills
  - member:    search, subscribe, install (default)

Private Hub mode: when SKILLHUB_PRIVATE=true, only authenticated users
can access the Hub. Registration is invite-only (admin creates accounts).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "skillhub.db"
PRIVATE_MODE = os.environ.get("SKILLHUB_PRIVATE", "false").lower() in ("true", "1", "yes")

_local = threading.local()


class Role(Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"
    MEMBER = "member"

    @property
    def level(self) -> int:
        return {"admin": 100, "reviewer": 70, "publisher": 50, "member": 10}[self.value]

    def can(self, action: str) -> bool:
        """Check if this role can perform an action."""
        perms = {
            "admin":     ["manage_users", "review", "publish", "subscribe", "install", "view_all", "force_approve", "view_audit_log"],
            "reviewer":  ["review", "publish", "subscribe", "install"],
            "publisher": ["publish", "subscribe", "install"],
            "member":    ["subscribe", "install"],
        }
        return action in perms.get(self.value, [])


@dataclass
class User:
    user_id: str
    username: str
    role: Role = Role.MEMBER
    email: str = ""
    team: str = ""
    active: bool = True
    created_at: float = 0.0
    last_login: float = 0.0


@dataclass
class AuditEntry:
    id: int = 0
    user_id: str = ""
    username: str = ""
    action: str = ""           # publish, review, install, subscribe, sync, user_create, user_delete
    target: str = ""           # skill_id, user_id, etc.
    detail: str = ""           # extra info
    ip_address: str = ""
    created_at: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Database
# ═══════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    """Get thread-local connection via central db.py."""
    if not hasattr(_local, "conn") or _local.conn is None:
        from skillos.db import get_conn
        _local.conn = get_conn("skillhub.db")
        _local.conn.row_factory = sqlite3.Row
        _init_tables(_local.conn)
    return _local.conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """Seed default admin when database is empty (schema via skillos.db migrations)."""
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        _seed_admin(conn)


def _seed_admin(conn: sqlite3.Connection) -> None:
    """Create default admin user."""
    admin_id = uuid.uuid4().hex[:12]
    now = time.time()
    pw = os.environ.get("SKILLHUB_ADMIN_PASSWORD", "admin123")
    conn.execute(
        "INSERT INTO users (user_id, username, password_hash, role, email, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (admin_id, "admin", _hash_pw(pw), "admin", "admin@skillhub.local", now)
    )
    # Create admin token
    token = "skh_" + uuid.uuid4().hex
    conn.execute(
        "INSERT INTO api_tokens (token, user_id, label, created_at) VALUES (?, ?, ?, ?)",
        (token, admin_id, "default-admin", now)
    )
    conn.commit()
    _log.info("Seeded admin user (password: %s, token: %s)", pw, token)


# ═══════════════════════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════════════════════

def _hash_pw(password: str) -> str:
    return hashlib.sha256(f"skillhub:{password}:salt".encode()).hexdigest()


def authenticate_token(token: str) -> User | None:
    """Validate an API token and return the user."""
    if not token:
        return None
    # Strip Bearer prefix
    if token.startswith("Bearer "):
        token = token[7:]
    conn = _get_conn()
    row = conn.execute(
        "SELECT u.* FROM users u JOIN api_tokens t ON u.user_id = t.user_id WHERE t.token = ? AND u.active = 1",
        (token,)
    ).fetchone()
    if not row:
        return None
    # Update last used
    conn.execute("UPDATE api_tokens SET last_used = ? WHERE token = ?", (time.time(), token))
    conn.commit()
    return _row_to_user(row)


def authenticate_password(username: str, password: str) -> User | None:
    """Login with username + password. Returns user or None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND active = 1", (username,)
    ).fetchone()
    if not row:
        return None
    if row["password_hash"] != _hash_pw(password):
        return None
    conn.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (time.time(), row["user_id"]))
    conn.commit()
    return _row_to_user(row)


def login(username: str, password: str) -> dict | None:
    """Login, return {token, user} or None."""
    user = authenticate_password(username, password)
    if not user:
        return None
    token = "skh_" + uuid.uuid4().hex
    conn = _get_conn()
    conn.execute(
        "INSERT INTO api_tokens (token, user_id, label, created_at) VALUES (?, ?, ?, ?)",
        (token, user.user_id, f"login-{int(time.time())}", time.time())
    )
    conn.commit()
    _log_audit(user.user_id, user.username, "login", "", "password login")
    return {"token": token, "user": user_to_dict(user)}


def create_token(user_id: str, label: str = "") -> str | None:
    """Create a new API token for a user (admin only)."""
    token = "skh_" + uuid.uuid4().hex
    conn = _get_conn()
    conn.execute(
        "INSERT INTO api_tokens (token, user_id, label, created_at) VALUES (?, ?, ?, ?)",
        (token, user_id, label, time.time())
    )
    conn.commit()
    return token


# ═══════════════════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════════════════

def create_user(username: str, password: str, role: str = "member", email: str = "", team: str = "", creator_id: str = "") -> User | None:
    """Create a new user. Returns None if username taken."""
    conn = _get_conn()
    existing = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return None
    uid = uuid.uuid4().hex[:12]
    now = time.time()
    conn.execute(
        "INSERT INTO users (user_id, username, password_hash, role, email, team, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, username, _hash_pw(password), role, email, team, now)
    )
    conn.commit()
    user = get_user(uid)
    _log_audit(creator_id, "", "user_create", uid, f"Created user {username} role={role}")
    return user


def get_user(user_id: str) -> User | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def list_users() -> list[User]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [_row_to_user(r) for r in rows]


def update_user(user_id: str, **kwargs) -> User | None:
    """Update user fields: role, email, team, active."""
    conn = _get_conn()
    allowed = {"role", "email", "team", "active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_user(user_id)
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE users SET {sets} WHERE user_id = ?", list(updates.values()) + [user_id])
    conn.commit()
    return get_user(user_id)


def delete_user(user_id: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM api_tokens WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE user_id = ? AND role != 'admin'", (user_id,))
    conn.commit()
    return True


def user_to_dict(u: User) -> dict:
    return {
        "user_id": u.user_id, "username": u.username, "role": u.role.value,
        "email": u.email, "team": u.team, "active": u.active,
        "created_at": u.created_at, "last_login": u.last_login,
    }


# ═══════════════════════════════════════════════════════════════
# RBAC Middleware
# ═══════════════════════════════════════════════════════════════

def require_auth(request_headers: dict, action: str = "subscribe") -> tuple[User | None, str | None]:
    """Check if the request is authorized for the given action.

    Returns (user, error_message).
    If PRIVATE_MODE is off, returns a default anonymous user for non-admin actions.
    If PRIVATE_MODE is on, requires valid auth for everything.
    """
    auth_header = request_headers.get("Authorization", "") or request_headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header

    user = authenticate_token(token) if token else None

    if PRIVATE_MODE:
        if not user:
            return None, "Authentication required in private mode"
        if not user.role.can(action):
            return None, f"Role '{user.role.value}' cannot perform action '{action}'"
        return user, None

    # Public mode: auth optional, default to anonymous
    if not user:
        user = User(user_id="anonymous", username="anonymous", role=Role.MEMBER)
        # Anonymous can only subscribe/install in public mode
        if action in ("publish", "review", "manage_users", "force_approve", "view_audit_log"):
            return None, f"Authentication required for action '{action}'"
    return user, None


def require_role(min_role: str, request_headers: dict) -> tuple[User | None, str | None]:
    """Require a minimum role level."""
    user, err = require_auth(request_headers, "subscribe")
    if err:
        return None, err
    if user.role.level < Role(min_role).level:
        return None, f"Requires {min_role}+ role, you are {user.role.value}"
    return user, None


# ═══════════════════════════════════════════════════════════════
# Audit Log
# ═══════════════════════════════════════════════════════════════

def _log_audit(user_id: str, username: str, action: str, target: str, detail: str = "", ip: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO audit_log (user_id, username, action, target, detail, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, action, target, detail, ip, time.time())
    )
    conn.commit()


def log_action(user: User, action: str, target: str = "", detail: str = "", ip: str = "") -> None:
    _log_audit(user.user_id, user.username, action, target, detail, ip)


def get_audit_log(limit: int = 100, action: str = "", user_id: str = "") -> list[dict]:
    """Query audit log with optional filters."""
    conn = _get_conn()
    where = []
    params = []
    if action:
        where.append("action = ?")
        params.append(action)
    if user_id:
        where.append("user_id = ?")
        params.append(user_id)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"SELECT * FROM audit_log {clause} ORDER BY created_at DESC LIMIT ?",
        params + [limit]
    ).fetchall()
    return [
        {"id": r["id"], "user_id": r["user_id"], "username": r["username"],
         "action": r["action"], "target": r["target"], "detail": r["detail"],
         "ip_address": r["ip_address"], "created_at": r["created_at"]}
        for r in rows
    ]


def get_audit_stats() -> dict:
    """Aggregate audit stats: actions by type, top users."""
    conn = _get_conn()
    actions = {}
    for row in conn.execute("SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action").fetchall():
        actions[row["action"]] = row["cnt"]
    total = sum(actions.values())
    return {"total_events": total, "by_action": actions}


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _row_to_user(row: sqlite3.Row) -> User:
    def _g(key, default=""):
        try: return row[key]
        except (KeyError, IndexError): return default
    return User(
        user_id=row["user_id"], username=row["username"],
        role=Role(row["role"]), email=_g("email", ""),
        team=_g("team", ""), active=bool(_g("active", 1)),
        created_at=_g("created_at", 0.0), last_login=_g("last_login", 0.0),
    )


def is_private_mode() -> bool:
    return PRIVATE_MODE
