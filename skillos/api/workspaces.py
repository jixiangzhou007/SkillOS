"""Workspace switch API (Sprint 1 · F5)."""


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skillos.identity.middleware import AuthContext, require_auth

router = APIRouter()


class SwitchWorkspaceRequest(BaseModel):
    tenant_id: str


@router.get("/list")
async def list_workspaces(auth: AuthContext = Depends(require_auth)):
    from skillos.identity.workspaces import list_workspaces

    items = list_workspaces(auth.user_id)
    return {
        "workspaces": [
            {
                "tenant_id": w.tenant_id,
                "tenant_type": w.tenant_type,
                "label": w.label,
                "org_id": w.org_id,
                "is_default": w.is_default,
            }
            for w in items
        ],
        "active_tenant_id": auth.tenant_id,
    }


@router.post("/switch")
async def switch_workspace(req: SwitchWorkspaceRequest, auth: AuthContext = Depends(require_auth)):
    from skillos.identity.audit import log_workspace_switch
    from skillos.identity.middleware import issue_auth_token
    from skillos.identity.workspaces import set_default_workspace
    from skillos.marketplace.auth import get_user, user_to_dict

    try:
        ws = set_default_workspace(auth.user_id, req.tenant_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Cannot access this workspace")
    except LookupError:
        raise HTTPException(status_code=404, detail="Workspace not found")

    user = get_user(auth.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log_workspace_switch(auth.user_id, auth.username, ws.tenant_id)
    token = issue_auth_token(user, tenant_id=ws.tenant_id)
    return {
        "token": token,
        "token_type": "Bearer",
        "workspace": {
            "tenant_id": ws.tenant_id,
            "tenant_type": ws.tenant_type,
            "label": ws.label,
            "org_id": ws.org_id,
        },
        "user": user_to_dict(user),
    }
