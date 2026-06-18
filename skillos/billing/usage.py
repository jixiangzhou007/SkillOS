"""Personal Free quotas and usage tracking (Sprint 5)."""


import calendar
import sqlite3
import time
from dataclasses import dataclass

PERSONAL_FREE_MAX_SKILLS = 10
PERSONAL_FREE_MAX_LLM_MONTHLY = 50


def _personal_limits(user_id: str) -> tuple[str, int, int]:
    from skillos.billing.plans import get_user_plan, plan_limits
    plan = get_user_plan(user_id)
    skills, llm = plan_limits(plan)
    return plan, skills, llm


class QuotaExceededError(Exception):
    """User-facing quota violation."""

    def __init__(self, message: str, *, code: str = "quota_exceeded"):
        super().__init__(message)
        self.code = code


@dataclass
class UsageSummary:
    tenant_id: str
    plan: str
    skills_used: int
    skills_limit: int
    llm_used: int
    llm_limit: int
    period: str
    byok: bool = False

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan,
            "skills": {"used": self.skills_used, "limit": self.skills_limit},
            "llm_calls": {"used": self.llm_used, "limit": self.llm_limit, "period": self.period},
            "byok": self.byok,
        }


def _conn() -> sqlite3.Connection:
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def _month_key(ts: float | None = None) -> str:
    t = time.gmtime(ts or time.time())
    return f"{t.tm_year:04d}-{t.tm_mon:02d}"


def _is_personal_free(tenant_id: str) -> bool:
    if not tenant_id.startswith("personal:"):
        return False
    import os
    if os.getenv("SKILLOS_SKIP_USAGE", "").lower() in ("1", "true", "yes"):
        return False
    return True


def user_has_byok(user_id: str) -> bool:
    """True when user configured own LLM key (exempt from platform LLM quota)."""
    uid = user_id[4:] if user_id.startswith("usr_") else user_id
    conn = _conn()
    row = conn.execute(
        "SELECT use_own_key FROM user_llm_keys WHERE user_id = ?",
        (uid,),
    ).fetchone()
    return bool(row and row[0])


def record_event(
    *,
    tenant_id: str,
    user_id: str = "",
    event_type: str,
    detail: str = "",
) -> None:
    conn = _conn()
    conn.execute(
        """INSERT INTO usage_events (tenant_id, user_id, event_type, detail, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (tenant_id, user_id, event_type, detail, time.time()),
    )
    conn.commit()


def count_llm_calls_this_month(tenant_id: str) -> int:
    mk = _month_key()
    start = time.mktime(time.strptime(mk + "-01", "%Y-%m-%d"))
    _, last_day = calendar.monthrange(int(mk[:4]), int(mk[5:7]))
    end = time.mktime(time.strptime(f"{mk}-{last_day:02d}", "%Y-%m-%d")) + 86400
    conn = _conn()
    row = conn.execute(
        """SELECT COUNT(*) FROM usage_events
           WHERE tenant_id = ? AND event_type = 'llm_call'
           AND created_at >= ? AND created_at < ?""",
        (tenant_id, start, end),
    ).fetchone()
    return int(row[0]) if row else 0


def count_skills(tenant) -> int:
    from skillos.skills.skill_store import list_skills
    return len(list_skills(tenant=tenant))


def check_skill_quota(tenant, *, is_new: bool) -> None:
    if tenant is None or not is_new:
        return
    if _is_personal_free(tenant.tenant_id):
        uid = tenant.user_id or tenant.tenant_id.split(":", 1)[1]
        plan, max_skills, _ = _personal_limits(uid)
        used = count_skills(tenant)
        if used >= max_skills:
            hint = "升级到 Pro" if plan == "personal_free" else "请删除旧技能"
            raise QuotaExceededError(
                f"技能上限 {max_skills} 已达。{hint}。",
                code="skill_limit",
            )
        return
    if tenant.tenant_id.startswith("org:"):
        from skillos.billing.dept_quota import check_dept_skill_quota
        check_dept_skill_quota(tenant)


def check_llm_quota(tenant_id: str, user_id: str = "", dept_id: str = "") -> None:
    if _is_personal_free(tenant_id):
        if user_id and user_has_byok(user_id):
            return
        uid = user_id or ""
        _, _, max_llm = _personal_limits(uid)
        used = count_llm_calls_this_month(tenant_id)
        if used >= max_llm:
            raise QuotaExceededError(
                f"本月平台 LLM 额度（{max_llm} 次）已用完。"
                "请在设置中配置自带 API Key（BYOK）或下月再试。",
                code="llm_limit",
            )
        return
    if tenant_id.startswith("org:") and dept_id:
        from skillos.billing.dept_quota import check_dept_llm_quota
        check_dept_llm_quota(tenant_id, dept_id)


def record_llm_usage(tenant_id: str = "", user_id: str = "", dept_id: str = "") -> None:
    from skillos.identity.context import get_tenant_context

    ctx = get_tenant_context()
    tid = tenant_id or (ctx.tenant_id if ctx else "")
    if not tid:
        return
    did = dept_id or (ctx.dept_id if ctx else "")
    if _is_personal_free(tid):
        record_event(tenant_id=tid, user_id=user_id, event_type="llm_call", detail=did)
        return
    if tid.startswith("org:"):
        record_event(tenant_id=tid, user_id=user_id, event_type="llm_call", detail=did)


def get_usage_summary(tenant_id: str, user_id: str = "") -> UsageSummary:
    from skillos.identity.context import TenantContext

    plan = "organization" if tenant_id.startswith("org:") else "personal_free"
    if tenant_id.startswith("personal:"):
        tenant = TenantContext.from_tenant_id(tenant_id)
        skills_used = count_skills(tenant)
        llm_used = count_llm_calls_this_month(tenant_id)
        byok = user_has_byok(user_id) if user_id else False
        plan, skills_limit, llm_limit = _personal_limits(user_id)
        return UsageSummary(
            tenant_id=tenant_id,
            plan=plan,
            skills_used=skills_used,
            skills_limit=skills_limit,
            llm_used=llm_used,
            llm_limit=llm_limit,
            period=_month_key(),
            byok=byok,
        )
    return UsageSummary(
        tenant_id=tenant_id,
        plan=plan,
        skills_used=0,
        skills_limit=9999,
        llm_used=0,
        llm_limit=9999,
        period=_month_key(),
    )


def set_user_byok(user_id: str, *, enabled: bool, api_key: str = "") -> None:
    """Register BYOK preference (key stored locally; production should encrypt)."""
    uid = user_id[4:] if user_id.startswith("usr_") else user_id
    conn = _conn()
    conn.execute(
        """INSERT INTO user_llm_keys (user_id, provider, api_key, use_own_key, updated_at)
           VALUES (?, 'deepseek', ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             api_key=excluded.api_key,
             use_own_key=excluded.use_own_key,
             updated_at=excluded.updated_at""",
        (uid, api_key, 1 if enabled else 0, time.time()),
    )
    conn.commit()
