"""Skill approval API (Sprint 3)."""


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skillos.identity.middleware import AuthContext, require_auth
from skillos.skills.approval import ApprovalError, list_by_status, transition

router = APIRouter()


class ReviewRequest(BaseModel):
    notes: str = ""


def _require_org_tenant(auth: AuthContext) -> str:
    if not auth.tenant_id.startswith("org:"):
        raise HTTPException(status_code=400, detail="Switch to an organization workspace first")
    return auth.tenant_id


@router.get("/queue")
async def approval_queue(auth: AuthContext = Depends(require_auth)):
    """Pending skills for current org workspace."""
    tenant_id = _require_org_tenant(auth)
    pending = list_by_status(tenant_id, "pending")
    drafts = list_by_status(tenant_id, "draft")
    published = list_by_status(tenant_id, "published")
    return {
        "tenant_id": tenant_id,
        "pending": pending,
        "drafts": drafts,
        "published_count": len(published),
    }


@router.post("/{skill_slug}/submit")
async def submit_skill(skill_slug: str, auth: AuthContext = Depends(require_auth)):
    try:
        meta = transition(
            tenant_id=_require_org_tenant(auth),
            skill_slug=skill_slug,
            action="submit",
            actor_platform_id=auth.platform_user_id,
            actor_role=auth.role,
        )
    except ApprovalError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": meta.get("approval_status"), "skill": meta}


@router.post("/{skill_slug}/approve")
async def approve_skill(
    skill_slug: str,
    req: ReviewRequest,
    auth: AuthContext = Depends(require_auth),
):
    try:
        meta = transition(
            tenant_id=_require_org_tenant(auth),
            skill_slug=skill_slug,
            action="approve",
            actor_platform_id=auth.platform_user_id,
            actor_role=auth.role,
            notes=req.notes,
        )
    except ApprovalError as e:
        raise HTTPException(status_code=403 if "required" in str(e) else 400, detail=str(e)) from e
    return {"status": meta.get("approval_status"), "skill": meta}


@router.post("/{skill_slug}/reject")
async def reject_skill(
    skill_slug: str,
    req: ReviewRequest,
    auth: AuthContext = Depends(require_auth),
):
    try:
        meta = transition(
            tenant_id=_require_org_tenant(auth),
            skill_slug=skill_slug,
            action="reject",
            actor_platform_id=auth.platform_user_id,
            actor_role=auth.role,
            notes=req.notes,
        )
    except ApprovalError as e:
        raise HTTPException(status_code=403 if "required" in str(e) else 400, detail=str(e)) from e
    return {"status": meta.get("approval_status"), "skill": meta}
