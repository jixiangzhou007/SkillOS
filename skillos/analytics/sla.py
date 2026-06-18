"""SLA monitoring (Sprint 9)."""


import time

from skillos.billing.usage import _conn, record_event

SLA_UPTIME_TARGET = 0.999  # 99.9%


def record_health_ping() -> None:
    record_event(tenant_id="platform", user_id="", event_type="health_ok", detail="")


def get_sla_metrics(*, days: int = 7) -> dict:
    since = time.time() - days * 86400
    conn = _conn()
    health = conn.execute(
        "SELECT COUNT(*) FROM usage_events WHERE event_type = 'health_ok' AND created_at >= ?",
        (since,),
    ).fetchone()
    errors = conn.execute(
        "SELECT COUNT(*) FROM usage_events WHERE event_type = 'api_error' AND created_at >= ?",
        (since,),
    ).fetchone()
    ok = int(health[0]) if health else 0
    err = int(errors[0]) if errors else 0
    total = ok + err
    uptime = (ok / total) if total else 1.0
    return {
        "period_days": days,
        "health_checks": ok,
        "api_errors": err,
        "uptime_ratio": round(uptime, 6),
        "uptime_percent": round(uptime * 100, 3),
        "slo_target_percent": SLA_UPTIME_TARGET * 100,
        "slo_met": uptime >= SLA_UPTIME_TARGET,
    }
