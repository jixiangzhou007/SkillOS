"""Subscription plans (Sprint 9 — Personal Pro beta)."""

from __future__ import annotations

import time

PLAN_PERSONAL_FREE = "personal_free"
PLAN_PERSONAL_PRO = "personal_pro"

PLAN_LIMITS: dict[str, tuple[int, int]] = {
    PLAN_PERSONAL_FREE: (10, 50),
    PLAN_PERSONAL_PRO: (9999, 500),
}


def _conn():
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def _uid(user_id: str) -> str:
    return user_id[4:] if user_id.startswith("usr_") else user_id


def get_user_plan(user_id: str) -> str:
    uid = _uid(user_id)
    conn = _conn()
    row = conn.execute("SELECT plan, expires_at FROM user_plans WHERE user_id = ?", (uid,)).fetchone()
    if not row:
        return PLAN_PERSONAL_FREE
    plan, expires = row[0], float(row[1])
    if expires and expires < time.time() and plan == PLAN_PERSONAL_PRO:
        return PLAN_PERSONAL_FREE
    return plan


def set_user_plan(user_id: str, plan: str, *, expires_at: float = 0.0) -> str:
    if plan not in PLAN_LIMITS:
        raise ValueError(f"Unknown plan: {plan}")
    uid = _uid(user_id)
    now = time.time()
    conn = _conn()
    conn.execute(
        """INSERT INTO user_plans (user_id, plan, expires_at, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             plan=excluded.plan,
             expires_at=excluded.expires_at,
             updated_at=excluded.updated_at""",
        (uid, plan, expires_at, now),
    )
    conn.commit()
    return plan


def plan_limits(plan: str) -> tuple[int, int]:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_PERSONAL_FREE])
