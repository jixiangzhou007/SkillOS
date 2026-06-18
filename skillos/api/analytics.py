"""Analytics API — funnel + stability (Sprint 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from skillos.analytics.funnel import get_error_rate, get_funnel_summary
from skillos.analytics.platform import get_platform_overview
from skillos.analytics.sla import get_sla_metrics
from skillos.identity.middleware import AuthContext, require_auth

router = APIRouter()


@router.get("/funnel")
async def funnel_summary(
    days: int = Query(30, ge=1, le=365),
    auth: AuthContext = Depends(require_auth),
):
    """Conversion funnel counts for current tenant (or global for org admin)."""
    tid = auth.tenant_id
    if tid.startswith("org:"):
        from skillos.identity.models import get_member_role
        oid = tid.split(":", 1)[1]
        if get_member_role(auth.platform_user_id, oid) != "org_admin":
            raise HTTPException(status_code=403, detail="org_admin required")
    elif tid.startswith("personal:"):
        pass
    else:
        tid = ""
    return get_funnel_summary(days=days, tenant_id=tid if tid.startswith("personal:") else "")


@router.get("/stability")
async def stability_metrics(days: int = Query(7, ge=1, le=90)):
    """Public stability snapshot (error rate vs 1% target)."""
    return get_error_rate(days=days)


@router.get("/sla")
async def sla_metrics(days: int = Query(7, ge=1, le=30)):
    """SLA uptime based on health pings vs API errors."""
    return get_sla_metrics(days=days)


@router.get("/platform")
async def platform_overview(auth: AuthContext = Depends(require_auth)):
    """Scale metrics toward 200-skill / 5-org goals."""
    allowed = auth.role == "admin"
    if auth.tenant_id.startswith("org:"):
        from skillos.identity.models import get_member_role
        oid = auth.tenant_id.split(":", 1)[1]
        if get_member_role(auth.platform_user_id, oid) == "org_admin":
            allowed = True
    if not allowed:
        raise HTTPException(status_code=403, detail="org_admin or platform admin required")
    return get_platform_overview()
