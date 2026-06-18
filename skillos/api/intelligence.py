"""Intelligence API — role templates, pipeline viz helpers."""


from fastapi import APIRouter, Depends, HTTPException, Query

from skillos.identity.middleware import AuthContext, get_optional_auth

router = APIRouter()


@router.get("/role-templates")
async def role_templates():
    """List job/role skill template library entries."""
    from skillos.intelligence.role_templates import list_role_templates

    return {"templates": list_role_templates()}


@router.get("/role-templates/{role_id}/recommendations")
async def role_recommendations(
    role_id: str,
    limit: int = Query(8, ge=1, le=20),
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Skills + MetaSkill blueprint recommendations for a role."""
    from skillos.intelligence.role_templates import recommend_for_role

    tenant = auth.tenant_context() if auth else None
    try:
        return recommend_for_role(role_id, tenant=tenant, limit=limit)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Role template '{role_id}' not found")
