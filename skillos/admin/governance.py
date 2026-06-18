"""Org governance metrics — verified rate target (Sprint 11, M9–M12)."""


from skillos.identity.context import TenantContext
from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload
from skillos.skills import skill_store

VERIFIED_RATE_TARGET = 0.70


def _normalize_org_id(org_id: str) -> str:
    return org_id if org_id.startswith("org_") else f"org_{org_id}"


def _skill_epistemic_stats(name: str, tenant: TenantContext) -> dict | None:
    try:
        raw = skill_store.load_skill_raw(name, tenant=tenant)
    except FileNotFoundError:
        return None
    ep = format_epistemic_api_payload(raw.get("meta") or {})
    total = int(ep.get("total_claims") or 0)
    if total <= 0:
        verified = int(ep.get("verified") or 0)
        pending = int(ep.get("pending") or 0)
        total = verified + pending
    if total <= 0:
        return None
    verified = int(ep.get("verified") or 0)
    pending = int(ep.get("pending") or 0)
    rate = verified / total
    return {
        "name": name,
        "verified": verified,
        "pending": pending,
        "total_claims": total,
        "verified_rate": round(rate, 4),
        "meets_target": rate >= VERIFIED_RATE_TARGET,
    }


def build_org_governance(org_id: str) -> dict:
    """Aggregate epistemic verified rate for an organization tenant."""
    oid = _normalize_org_id(org_id)
    tenant = TenantContext.organization(oid)
    skill_names = skill_store.list_skills(tenant=tenant)

    skill_rows: list[dict] = []
    total_verified = 0
    total_pending = 0
    total_claims = 0
    skills_meeting_target = 0

    for name in skill_names:
        row = _skill_epistemic_stats(name, tenant)
        if not row:
            continue
        skill_rows.append(row)
        total_verified += row["verified"]
        total_pending += row["pending"]
        total_claims += row["total_claims"]
        if row["meets_target"]:
            skills_meeting_target += 1

    org_rate = (total_verified / total_claims) if total_claims else None
    at_risk = sorted(
        [s for s in skill_rows if not s["meets_target"]],
        key=lambda s: s["verified_rate"],
    )[:20]

    return {
        "org_id": oid,
        "target_verified_rate": VERIFIED_RATE_TARGET,
        "org_verified_rate": round(org_rate, 4) if org_rate is not None else None,
        "meets_target": bool(org_rate is not None and org_rate >= VERIFIED_RATE_TARGET),
        "skills_total": len(skill_names),
        "skills_with_claims": len(skill_rows),
        "skills_meeting_target": skills_meeting_target,
        "claims": {
            "verified": total_verified,
            "pending": total_pending,
            "total": total_claims,
        },
        "at_risk_skills": at_risk,
    }


def build_platform_governance() -> dict:
    """Platform-wide governance snapshot across all org tenants."""
    from skillos.db import get_conn

    conn = get_conn("skillhub.db")
    rows = conn.execute("SELECT org_id FROM organizations").fetchall()

    org_snapshots: list[dict] = []
    total_verified = 0
    total_claims = 0
    orgs_meeting_target = 0

    for row in rows:
        oid = row[0]
        gov = build_org_governance(oid)
        if gov["skills_with_claims"] == 0:
            continue
        org_snapshots.append(
            {
                "org_id": oid,
                "verified_rate": gov["org_verified_rate"],
                "meets_target": gov["meets_target"],
                "skills_with_claims": gov["skills_with_claims"],
            }
        )
        total_verified += gov["claims"]["verified"]
        total_claims += gov["claims"]["total"]
        if gov["meets_target"]:
            orgs_meeting_target += 1

    platform_rate = (total_verified / total_claims) if total_claims else None
    return {
        "target_verified_rate": VERIFIED_RATE_TARGET,
        "platform_verified_rate": round(platform_rate, 4) if platform_rate is not None else None,
        "meets_target": bool(platform_rate is not None and platform_rate >= VERIFIED_RATE_TARGET),
        "orgs_with_claims": len(org_snapshots),
        "orgs_meeting_target": orgs_meeting_target,
        "claims": {"verified": total_verified, "total": total_claims},
        "organizations": sorted(org_snapshots, key=lambda o: o.get("verified_rate") or 0),
    }
