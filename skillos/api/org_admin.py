"""Org admin console API (Sprint 6)."""


from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from skillos.admin.audit_export import export_org_audit_csv
from skillos.admin.governance import build_org_governance
from skillos.admin.service import build_admin_overview, get_org_usage_stats, set_org_quota
from skillos.api.organizations import _normalize_org_id, _require_org_admin, _require_org_member
from skillos.identity.departments import create_department, list_departments
from skillos.identity.middleware import AuthContext, require_auth

router = APIRouter()


class CreateDeptRequest(BaseModel):
    name: str


class QuotaRequest(BaseModel):
    max_skills: int | None = None
    max_llm_monthly: int | None = None


class DeptQuotaRequest(BaseModel):
    max_skills: int = 50
    max_llm_monthly: int = 200


@router.get("/{org_id}/admin/overview")
async def admin_overview(org_id: str, auth: AuthContext = Depends(require_auth)):
    """Org admin dashboard summary."""
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    try:
        return build_admin_overview(oid)
    except LookupError:
        raise HTTPException(status_code=404, detail="Organization not found")


@router.get("/{org_id}/admin/usage")
async def admin_usage(org_id: str, auth: AuthContext = Depends(require_auth)):
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    return get_org_usage_stats(oid)


@router.get("/{org_id}/admin/governance")
async def admin_governance(org_id: str, auth: AuthContext = Depends(require_auth)):
    """Epistemic verified-rate KPIs for org compliance (M12 target ≥70%)."""
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    return build_org_governance(oid)


@router.patch("/{org_id}/admin/quota")
async def update_quota(org_id: str, req: QuotaRequest, auth: AuthContext = Depends(require_auth)):
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    quota = set_org_quota(oid, max_skills=req.max_skills, max_llm_monthly=req.max_llm_monthly)
    return {"org_id": oid, "quota": quota.__dict__}


@router.get("/{org_id}/departments")
async def get_departments(org_id: str, auth: AuthContext = Depends(require_auth)):
    oid = _normalize_org_id(org_id)
    _require_org_member(auth, oid)
    depts = list_departments(oid)
    return {
        "org_id": oid,
        "departments": [
            {"dept_id": d.dept_id, "name": d.name, "created_at": d.created_at}
            for d in depts
        ],
    }


@router.post("/{org_id}/departments")
async def add_department(org_id: str, req: CreateDeptRequest, auth: AuthContext = Depends(require_auth)):
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Department name required")
    try:
        dept = create_department(oid, req.name)
    except LookupError:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"dept_id": dept.dept_id, "name": dept.name, "org_id": oid}


@router.patch("/{org_id}/departments/{dept_id}/quota")
async def update_dept_quota(
    org_id: str,
    dept_id: str,
    req: DeptQuotaRequest,
    auth: AuthContext = Depends(require_auth),
):
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    from skillos.billing.dept_quota import set_dept_quota
    quota = set_dept_quota(dept_id, oid, max_skills=req.max_skills, max_llm_monthly=req.max_llm_monthly)
    return {"dept_id": quota.dept_id, "quota": {"max_skills": quota.max_skills, "max_llm_monthly": quota.max_llm_monthly}}


@router.get("/{org_id}/admin/audit/export")
async def export_audit(org_id: str, auth: AuthContext = Depends(require_auth)):
    """Export org audit log as CSV (org_admin)."""
    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)
    csv_text = export_org_audit_csv(oid)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_{oid}.csv"'},
    )
