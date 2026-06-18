"""Build TenantContext from request/session dict."""

from __future__ import annotations

from skillos.identity.context import TenantContext


def tenant_from_context(ctx: dict | None) -> TenantContext | None:
    if not ctx:
        return None
    tid = (ctx.get("tenant_id") or "").strip()
    if tid:
        return TenantContext.from_tenant_id(
            tid,
            user_id=ctx.get("user_id", ""),
            dept_id=ctx.get("dept_id", ""),
        )
    org_id = (ctx.get("org_id") or "").strip()
    user_id = (ctx.get("user_id") or "").strip()
    if org_id:
        return TenantContext.organization(
            org_id, user_id=user_id, dept_id=ctx.get("dept_id", "")
        )
    if user_id:
        return TenantContext.personal(user_id)
    return None
