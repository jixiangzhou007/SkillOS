"""Org admin overview, quotas, usage (Sprint 6)."""


import time
from dataclasses import dataclass

from skillos.identity.context import TenantContext
from skillos.identity.departments import list_departments
from skillos.identity.models import get_organization, list_org_members, list_skill_metadata
from skillos.skills import skill_store


@dataclass
class OrgQuota:
    max_skills: int = 9999
    max_llm_monthly: int = 9999


def _conn():
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def _normalize_org_id(org_id: str) -> str:
    return org_id if org_id.startswith("org_") else f"org_{org_id}"


def get_org_quota(org_id: str) -> OrgQuota:
    oid = _normalize_org_id(org_id)
    conn = _conn()
    row = conn.execute(
        "SELECT max_skills, max_llm_monthly FROM org_settings WHERE org_id = ?",
        (oid,),
    ).fetchone()
    if not row:
        return OrgQuota()
    return OrgQuota(max_skills=int(row[0]), max_llm_monthly=int(row[1]))


def set_org_quota(org_id: str, *, max_skills: int | None = None, max_llm_monthly: int | None = None) -> OrgQuota:
    oid = _normalize_org_id(org_id)
    current = get_org_quota(oid)
    skills = max_skills if max_skills is not None else current.max_skills
    llm = max_llm_monthly if max_llm_monthly is not None else current.max_llm_monthly
    now = time.time()
    conn = _conn()
    conn.execute(
        """INSERT INTO org_settings (org_id, max_skills, max_llm_monthly, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(org_id) DO UPDATE SET
             max_skills=excluded.max_skills,
             max_llm_monthly=excluded.max_llm_monthly,
             updated_at=excluded.updated_at""",
        (oid, skills, llm, now),
    )
    conn.commit()
    return OrgQuota(max_skills=skills, max_llm_monthly=llm)


def get_org_usage_stats(org_id: str) -> dict:
    oid = _normalize_org_id(org_id)
    tenant_id = f"org:{oid}"
    tenant = TenantContext.organization(oid)
    skills_used = len(skill_store.list_skills(tenant=tenant))
    from skillos.billing.usage import count_llm_calls_this_month
    llm_used = count_llm_calls_this_month(tenant_id)
    quota = get_org_quota(oid)
    return {
        "tenant_id": tenant_id,
        "skills": {"used": skills_used, "limit": quota.max_skills},
        "llm_calls": {"used": llm_used, "limit": quota.max_llm_monthly},
    }


def build_admin_overview(org_id: str) -> dict:
    oid = _normalize_org_id(org_id)
    org = get_organization(oid)
    if not org:
        raise LookupError(org_id)
    members = list_org_members(oid)
    depts = list_departments(oid)
    tenant = TenantContext.organization(oid)
    skill_names = skill_store.list_skills(tenant=tenant)
    meta_rows = {m["skill_slug"]: m for m in list_skill_metadata(f"org:{oid}")}
    skills_by_dept: dict[str, int] = {}
    for name in skill_names:
        slug = name.lower().replace(" ", "-")
        dept = meta_rows.get(slug, {}).get("dept_id") or "_shared"
        skills_by_dept[dept] = skills_by_dept.get(dept, 0) + 1
    return {
        "org": {
            "org_id": org.org_id,
            "display_name": org.display_name,
            "plan": org.plan,
            "tenant_id": f"org:{oid}",
        },
        "members_count": len(members),
        "departments_count": len(depts),
        "skills_count": len(skill_names),
        "skills_by_dept": skills_by_dept,
        "usage": get_org_usage_stats(oid),
        "quota": get_org_quota(oid).__dict__,
    }
