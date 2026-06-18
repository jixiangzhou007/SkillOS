"""Auth endpoints — login, register, JWT, GitHub (Sprint 1)."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""


class GitHubAuthRequest(BaseModel):
    code: str
    redirect_uri: str = ""


class FeishuAuthRequest(BaseModel):
    code: str
    redirect_uri: str = ""


class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "member"


class AdminUpdateUserRequest(BaseModel):
    user_id: str
    role: str


class AdminDeleteUserRequest(BaseModel):
    user_id: str


@router.post("/register")
async def register(req: RegisterRequest):
    """Create account + Personal Free tenant + JWT."""
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    from skillos.marketplace.auth import create_user, user_to_dict
    from skillos.identity.workspaces import ensure_personal_workspace
    from skillos.identity.middleware import issue_auth_token

    user = create_user(req.username, req.password, "member", req.email)
    if not user:
        raise HTTPException(status_code=409, detail="Username already taken")

    ws = ensure_personal_workspace(user.user_id, display_name=req.username)
    token = issue_auth_token(user, tenant_id=ws.tenant_id)
    try:
        from skillos.analytics.funnel import track_funnel
        from skillos.identity.users import to_platform_user_id
        track_funnel("register", tenant_id=ws.tenant_id, user_id=to_platform_user_id(user.user_id))
    except Exception:
        pass
    return {
        "token": token,
        "token_type": "Bearer",
        "user": user_to_dict(user),
        "workspace": {
            "tenant_id": ws.tenant_id,
            "tenant_type": ws.tenant_type,
            "label": ws.label,
        },
    }


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate and return JWT (+ workspace)."""
    from skillos.marketplace.auth import authenticate_password, user_to_dict
    from skillos.identity.workspaces import ensure_personal_workspace
    from skillos.identity.middleware import issue_auth_token
    from skillos.identity.audit import log_skill_action

    user = authenticate_password(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    ws = ensure_personal_workspace(user.user_id, display_name=user.username)
    token = issue_auth_token(user, tenant_id=ws.tenant_id)
    log_skill_action(user_id=user.user_id, username=user.username, action="login", skill_name="")
    return {
        "token": token,
        "token_type": "Bearer",
        "user": user_to_dict(user),
        "workspace": {
            "tenant_id": ws.tenant_id,
            "tenant_type": ws.tenant_type,
            "label": ws.label,
        },
    }


@router.get("/me")
async def me(authorization: str = Header(None)):
    """Current user + active workspace from JWT or legacy token."""
    from skillos.marketplace.auth import user_to_dict, get_user
    from skillos.identity.middleware import auth_from_token, parse_bearer

    token = parse_bearer(authorization)
    if not token:
        return {"user": {"username": "anonymous", "role": "member"}, "workspace": None}

    ctx = auth_from_token(token)
    if not ctx:
        return {"user": {"username": "anonymous", "role": "member", "error": "invalid token"}, "workspace": None}

    user = get_user(ctx.user_id)
    user_dict = user_to_dict(user) if user else {
        "user_id": ctx.user_id,
        "username": ctx.username,
        "role": ctx.role,
    }
    return {
        "user": user_dict,
        "workspace": {
            "tenant_id": ctx.tenant_id,
            "tenant_type": ctx.tenant_type,
            "org_id": ctx.org_id,
        },
    }


@router.post("/github")
async def github_login(req: GitHubAuthRequest):
    """Exchange GitHub OAuth code for JWT + Personal tenant."""
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=501,
            detail="GitHub OAuth not configured (set GITHUB_CLIENT_ID/SECRET)",
        )

    import urllib.request
    import json

    body = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": req.code,
        "redirect_uri": req.redirect_uri or None,
    }).encode()
    request = urllib.request.Request(
        "https://github.com/login/oauth/access_token",
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            token_data = json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub token exchange failed: {e}") from e

    access = token_data.get("access_token")
    if not access:
        raise HTTPException(status_code=401, detail=token_data.get("error_description", "no access_token"))

    user_req = urllib.request.Request(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(user_req, timeout=15) as resp:
        gh_user = json.loads(resp.read().decode())

    gh_login = gh_user.get("login") or "github-user"
    gh_id = gh_user.get("id")
    username = f"gh_{gh_login}"[:32]
    email = gh_user.get("email") or ""

    from skillos.marketplace.auth import create_user, get_user, user_to_dict, _get_conn, _hash_pw
    import time
    import uuid

    conn = _get_conn()
    row = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        user = get_user(row[0])
    else:
        password = uuid.uuid4().hex
        user = create_user(username, password, "member", email)
        if not user:
            raise HTTPException(status_code=500, detail="Failed to provision GitHub user")

    from skillos.identity.workspaces import ensure_personal_workspace
    from skillos.identity.middleware import issue_auth_token

    ws = ensure_personal_workspace(user.user_id, display_name=gh_login)
    token = issue_auth_token(user, tenant_id=ws.tenant_id)
    return {
        "token": token,
        "token_type": "Bearer",
        "user": user_to_dict(user),
        "github_id": gh_id,
        "workspace": {"tenant_id": ws.tenant_id, "tenant_type": ws.tenant_type, "label": ws.label},
    }


def _require_platform_admin(authorization: str = Header(None)):
    from skillos.identity.middleware import auth_from_token, parse_bearer

    ctx = auth_from_token(parse_bearer(authorization))
    if not ctx:
        raise HTTPException(status_code=401, detail="Authentication required")
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return ctx


@router.get("/users")
async def admin_list_users(authorization: str = Header(None)):
    """List all users (platform admin)."""
    _require_platform_admin(authorization)
    from skillos.marketplace.auth import list_users, user_to_dict
    return {"users": [user_to_dict(u) for u in list_users()]}


@router.get("/audit-log")
async def admin_audit_log(limit: int = 100, authorization: str = Header(None)):
    """Platform audit log (admin)."""
    _require_platform_admin(authorization)
    from skillos.marketplace.auth import get_audit_log, get_audit_stats
    return {"entries": get_audit_log(limit=min(limit, 500)), "stats": get_audit_stats()}


@router.post("/admin/register")
async def admin_create_user(req: AdminCreateUserRequest, authorization: str = Header(None)):
    """Create user with role (platform admin)."""
    ctx = _require_platform_admin(authorization)
    from skillos.marketplace.auth import create_user, user_to_dict
    user = create_user(req.username, req.password, req.role, creator_id=ctx.user_id)
    if not user:
        raise HTTPException(status_code=409, detail="Username already taken")
    return {"user": user_to_dict(user)}


@router.post("/admin/update-user")
async def admin_update_user(req: AdminUpdateUserRequest, authorization: str = Header(None)):
    """Update user role (platform admin)."""
    _require_platform_admin(authorization)
    from skillos.marketplace.auth import update_user, user_to_dict
    user = update_user(req.user_id, role=req.role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user_to_dict(user)}


@router.post("/admin/delete-user")
async def admin_delete_user(req: AdminDeleteUserRequest, authorization: str = Header(None)):
    """Delete user (platform admin)."""
    _require_platform_admin(authorization)
    from skillos.marketplace.auth import delete_user
    delete_user(req.user_id)
    return {"deleted": True}


@router.post("/feishu")
async def feishu_login(req: FeishuAuthRequest):
    """Exchange Feishu OAuth code for JWT + Personal tenant (Sprint 5)."""
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=501,
            detail="Feishu OAuth not configured (set FEISHU_APP_ID/SECRET)",
        )

    import json
    import urllib.request

    token_body = json.dumps({
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": app_secret,
        "code": req.code,
        "redirect_uri": req.redirect_uri or None,
    }).encode()
    token_req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/authen/v2/oauth/token",
        data=token_body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(token_req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Feishu token exchange failed: {e}") from e

    access = token_data.get("access_token") or token_data.get("data", {}).get("access_token")
    if not access:
        raise HTTPException(status_code=401, detail=token_data.get("msg", "no access_token"))

    user_req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/authen/v1/user_info",
        headers={"Authorization": f"Bearer {access}"},
    )
    with urllib.request.urlopen(user_req, timeout=15) as resp:
        user_data = json.loads(resp.read().decode())

    info = user_data.get("data", user_data)
    feishu_name = info.get("name") or info.get("en_name") or "feishu-user"
    open_id = info.get("open_id") or info.get("user_id") or ""
    username = f"fs_{open_id[-12:]}" if open_id else f"fs_{feishu_name[:20]}"

    from skillos.marketplace.auth import create_user, get_user, user_to_dict, _get_conn

    conn = _get_conn()
    row = conn.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        user = get_user(row[0])
    else:
        import uuid
        user = create_user(username, uuid.uuid4().hex, "member", email="")

    from skillos.identity.workspaces import ensure_personal_workspace
    from skillos.identity.middleware import issue_auth_token

    ws = ensure_personal_workspace(user.user_id, display_name=feishu_name)
    token = issue_auth_token(user, tenant_id=ws.tenant_id)
    return {
        "token": token,
        "token_type": "Bearer",
        "user": user_to_dict(user),
        "feishu_open_id": open_id,
        "workspace": {"tenant_id": ws.tenant_id, "tenant_type": ws.tenant_type, "label": ws.label},
    }
