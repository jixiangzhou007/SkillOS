"""Department-level quotas (Sprint 7)."""

from __future__ import annotations

import calendar
import time
from dataclasses import dataclass

from skillos.billing.usage import QuotaExceededError, _conn, _month_key


@dataclass
class DeptQuota:
    dept_id: str
    org_id: str
    max_skills: int = 50
    max_llm_monthly: int = 200


def get_dept_quota(dept_id: str) -> DeptQuota | None:
    conn = _conn()
    row = conn.execute(
        "SELECT dept_id, org_id, max_skills, max_llm_monthly FROM dept_quotas WHERE dept_id = ?",
        (dept_id,),
    ).fetchone()
    if not row:
        return None
    return DeptQuota(dept_id=row[0], org_id=row[1], max_skills=int(row[2]), max_llm_monthly=int(row[3]))


def set_dept_quota(dept_id: str, org_id: str, *, max_skills: int, max_llm_monthly: int) -> DeptQuota:
    now = time.time()
    conn = _conn()
    conn.execute(
        """INSERT INTO dept_quotas (dept_id, org_id, max_skills, max_llm_monthly, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(dept_id) DO UPDATE SET
             max_skills=excluded.max_skills,
             max_llm_monthly=excluded.max_llm_monthly,
             updated_at=excluded.updated_at""",
        (dept_id, org_id, max_skills, max_llm_monthly, now),
    )
    conn.commit()
    return DeptQuota(dept_id=dept_id, org_id=org_id, max_skills=max_skills, max_llm_monthly=max_llm_monthly)


def count_dept_skills(org_id: str, dept_id: str) -> int:
    from skillos.identity.models import list_skill_metadata

    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    meta = list_skill_metadata(f"org:{oid}")
    return sum(1 for row in meta if row.get("dept_id") == dept_id)


def count_dept_llm_this_month(org_id: str, dept_id: str) -> int:
    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    tenant_id = f"org:{oid}"
    mk = _month_key()
    start = time.mktime(time.strptime(mk + "-01", "%Y-%m-%d"))
    _, last_day = calendar.monthrange(int(mk[:4]), int(mk[5:7]))
    end = time.mktime(time.strptime(f"{mk}-{last_day:02d}", "%Y-%m-%d")) + 86400
    conn = _conn()
    row = conn.execute(
        """SELECT COUNT(*) FROM usage_events
           WHERE tenant_id = ? AND event_type = 'llm_call' AND detail = ?
           AND created_at >= ? AND created_at < ?""",
        (tenant_id, dept_id, start, end),
    ).fetchone()
    return int(row[0]) if row else 0


def check_dept_skill_quota(tenant) -> None:
    if tenant is None or not tenant.tenant_id.startswith("org:") or not tenant.dept_id:
        return
    quota = get_dept_quota(tenant.dept_id)
    if not quota:
        return
    used = count_dept_skills(tenant.org_id or tenant.tenant_id.split(":", 1)[1], tenant.dept_id)
    if used >= quota.max_skills:
        raise QuotaExceededError(
            f"部门技能上限 {quota.max_skills} 已达。",
            code="dept_skill_limit",
        )


def check_dept_llm_quota(tenant_id: str, dept_id: str) -> None:
    if not tenant_id.startswith("org:") or not dept_id:
        return
    quota = get_dept_quota(dept_id)
    if not quota:
        return
    oid = tenant_id.split(":", 1)[1]
    used = count_dept_llm_this_month(oid, dept_id)
    if used >= quota.max_llm_monthly:
        raise QuotaExceededError(
            f"部门本月 LLM 额度（{quota.max_llm_monthly} 次）已用完。",
            code="dept_llm_limit",
        )
