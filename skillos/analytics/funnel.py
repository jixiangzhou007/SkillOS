"""Conversion funnel + error analytics (Sprint 7)."""


import time

from skillos.billing.usage import _conn, record_event

FUNNEL_STEPS = (
    "register",
    "first_dispatch",
    "first_skill",
    "create_team",
    "copy_to_org",
)


def track_funnel(
    step: str,
    *,
    tenant_id: str = "",
    user_id: str = "",
    detail: str = "",
) -> None:
    if step not in FUNNEL_STEPS:
        return
    record_event(
        tenant_id=tenant_id or "global",
        user_id=user_id,
        event_type=f"funnel_{step}",
        detail=detail,
    )


def track_api_error(*, path: str, status: int, tenant_id: str = "", user_id: str = "") -> None:
    record_event(
        tenant_id=tenant_id or "global",
        user_id=user_id,
        event_type="api_error",
        detail=f"{status}:{path}",
    )


def _since_ts(days: int) -> float:
    return time.time() - days * 86400


def get_funnel_summary(*, days: int = 30, tenant_id: str = "") -> dict:
    conn = _conn()
    since = _since_ts(days)
    params: list = [since]
    where = "created_at >= ? AND event_type LIKE 'funnel_%'"
    if tenant_id:
        where += " AND tenant_id = ?"
        params.append(tenant_id)
    rows = conn.execute(
        f"""SELECT event_type, COUNT(*) FROM usage_events
            WHERE {where}
            GROUP BY event_type""",
        params,
    ).fetchall()
    counts = {step: 0 for step in FUNNEL_STEPS}
    for event_type, cnt in rows:
        step = event_type.replace("funnel_", "", 1)
        if step in counts:
            counts[step] = int(cnt)
    total_reg = counts.get("register", 0) or 1
    return {
        "period_days": days,
        "tenant_id": tenant_id or "all",
        "steps": counts,
        "conversion": {
            "register_to_first_skill": round(counts.get("first_skill", 0) / total_reg, 3),
            "register_to_create_team": round(counts.get("create_team", 0) / total_reg, 3),
            "create_team_to_copy": round(
                (counts.get("copy_to_org", 0) / max(counts.get("create_team", 0), 1)), 3
            ),
        },
    }


def get_error_rate(*, days: int = 7) -> dict:
    conn = _conn()
    since = _since_ts(days)
    errors = conn.execute(
        """SELECT COUNT(*) FROM usage_events
           WHERE created_at >= ? AND event_type = 'api_error'""",
        (since,),
    ).fetchone()
    llm_calls = conn.execute(
        """SELECT COUNT(*) FROM usage_events
           WHERE created_at >= ? AND event_type = 'llm_call'""",
        (since,),
    ).fetchone()
    err = int(errors[0]) if errors else 0
    calls = int(llm_calls[0]) if llm_calls else 0
    denom = max(calls + err, 1)
    rate = err / denom
    return {
        "period_days": days,
        "api_errors": err,
        "llm_calls": calls,
        "error_rate": round(rate, 4),
        "target_under_1pct": rate < 0.01,
    }
