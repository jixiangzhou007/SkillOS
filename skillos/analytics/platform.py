"""Platform-wide scale metrics (Sprint 9 — 200 skill goal)."""


SKILL_GOAL = 200
ORG_GOAL = 5


def _conn():
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def get_platform_overview() -> dict:
    conn = _conn()
    orgs = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()
    skills = conn.execute("SELECT COUNT(*) FROM skill_metadata").fetchone()
    tenants = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()
    org_count = int(orgs[0]) if orgs else 0
    skill_count = int(skills[0]) if skills else 0
    from skillos.admin.governance import build_platform_governance

    return {
        "organizations": {"count": org_count, "goal": ORG_GOAL, "progress": round(org_count / ORG_GOAL, 3)},
        "skills": {"count": skill_count, "goal": SKILL_GOAL, "progress": round(skill_count / SKILL_GOAL, 3)},
        "tenants": int(tenants[0]) if tenants else 0,
        "governance": build_platform_governance(),
    }
