"""Organization management API (Sprint 2 — pilot)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skillos.identity.middleware import AuthContext, issue_auth_token, require_auth

router = APIRouter()


class CreateOrgRequest(BaseModel):
    display_name: str
    slug: str = ""
    plan: str = "team"


class AddMemberRequest(BaseModel):
    username: str
    role: str = "member"
    dept_id: str = ""


def _normalize_org_id(org_id: str) -> str:
    return org_id if org_id.startswith("org_") else f"org_{org_id}"


def _require_org_admin(auth: AuthContext, org_id: str) -> None:
    from skillos.identity.models import get_member_role

    role = get_member_role(auth.platform_user_id, org_id)
    if role != "org_admin":
        raise HTTPException(status_code=403, detail="org_admin required")


def _require_org_member(auth: AuthContext, org_id: str) -> None:
    from skillos.identity.models import get_member_role

    if not get_member_role(auth.platform_user_id, org_id):
        raise HTTPException(status_code=403, detail="Not an organization member")


@router.post("")
async def create_org(req: CreateOrgRequest, auth: AuthContext = Depends(require_auth)):
    """Create organization; caller becomes org_admin."""
    from skillos.identity.models import create_organization
    from skillos.marketplace.auth import get_user, user_to_dict

    org, tenant, _ = create_organization(
        req.display_name,
        slug=req.slug,
        owner_user_id=auth.user_id,
        plan=req.plan,
    )
    user = get_user(auth.user_id)
    token = issue_auth_token(user, tenant_id=tenant.tenant_id) if user else ""
    try:
        from skillos.analytics.funnel import track_funnel
        track_funnel("create_team", tenant_id=tenant.tenant_id, user_id=auth.platform_user_id, detail=org.org_id)
    except Exception:
        pass
    return {
        "org": {
            "org_id": org.org_id,
            "slug": org.slug,
            "display_name": org.display_name,
            "plan": org.plan,
            "tenant_id": tenant.tenant_id,
        },
        "token": token,
        "token_type": "Bearer",
        "user": user_to_dict(user) if user else None,
    }


@router.get("")
async def list_my_orgs(auth: AuthContext = Depends(require_auth)):
    """Organizations the current user belongs to."""
    from skillos.identity.models import get_member_role, list_user_organizations

    orgs = list_user_organizations(auth.platform_user_id)
    return {
        "organizations": [
            {
                "org_id": o.org_id,
                "slug": o.slug,
                "display_name": o.display_name,
                "plan": o.plan,
                "tenant_id": f"org:{o.org_id}",
                "role": get_member_role(auth.platform_user_id, o.org_id),
            }
            for o in orgs
        ]
    }


@router.get("/{org_id}/members")
async def list_members(org_id: str, auth: AuthContext = Depends(require_auth)):
    """List org members (members only)."""
    from skillos.identity.models import list_org_members
    from skillos.identity.users import from_platform_user_id
    from skillos.marketplace.auth import get_user

    oid = _normalize_org_id(org_id)
    _require_org_member(auth, oid)
    members = []
    for m in list_org_members(oid):
        u = get_user(from_platform_user_id(m.user_id))
        members.append({
            "user_id": m.user_id,
            "username": u.username if u else m.user_id,
            "role": m.role,
            "dept_id": m.dept_id,
        })
    return {"org_id": oid, "members": members}


@router.post("/{org_id}/members")
async def add_member(org_id: str, req: AddMemberRequest, auth: AuthContext = Depends(require_auth)):
    """Invite existing user to org (org_admin only)."""
    from skillos.identity.models import add_org_member
    from skillos.identity.users import to_platform_user_id
    from skillos.marketplace.auth import _get_conn

    oid = _normalize_org_id(org_id)
    _require_org_admin(auth, oid)

    conn = _get_conn()
    row = conn.execute(
        "SELECT user_id FROM users WHERE username = ? AND active = 1",
        (req.username,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"User not found: {req.username}")

    if req.role not in ("org_admin", "member"):
        raise HTTPException(status_code=400, detail="role must be org_admin or member")

    pid = to_platform_user_id(row[0])
    membership = add_org_member(
        oid,
        platform_user_id=pid,
        role=req.role,
        dept_id=req.dept_id,
    )
    return {
        "org_id": oid,
        "member": {
            "user_id": membership.user_id,
            "username": req.username,
            "role": membership.role,
            "dept_id": membership.dept_id,
        },
    }
