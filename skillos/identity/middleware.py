"""FastAPI auth dependencies."""


from dataclasses import dataclass

from fastapi import Header, HTTPException

from skillos.identity.jwt_auth import JWTError, verify_jwt
from skillos.identity.users import from_platform_user_id, to_platform_user_id
from skillos.identity.workspaces import get_default_workspace, tenant_context_for_user


@dataclass
class AuthContext:
    user_id: str
    platform_user_id: str
    username: str
    tenant_id: str
    tenant_type: str
    org_id: str = ""
    role: str = "member"

    def tenant_context(self):
        from skillos.identity.context import TenantContext
        if self.tenant_id.startswith("personal:"):
            return TenantContext.personal(self.platform_user_id)
        oid = self.org_id or self.tenant_id.split(":", 1)[1]
        return TenantContext.organization(oid, user_id=self.platform_user_id)


def parse_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    token = authorization.strip()
    if token.lower().startswith("bearer "):
        return token[7:].strip()
    return token


def auth_from_token(token: str) -> AuthContext | None:
    if not token:
        return None
    # Legacy SkillHub token
    if token.startswith("skh_"):
        from skillos.marketplace.auth import authenticate_token
        user = authenticate_token(token)
        if not user:
            return None
        ws = get_default_workspace(user.user_id)
        return AuthContext(
            user_id=user.user_id,
            platform_user_id=to_platform_user_id(user.user_id),
            username=user.username,
            tenant_id=ws.tenant_id,
            tenant_type=ws.tenant_type,
            org_id=ws.org_id,
            role=user.role.value,
        )
    try:
        payload = verify_jwt(token)
    except JWTError:
        return None
    uid = payload.get("sub", "")
    tid = payload.get("tenant_id", "")
    if not uid:
        return None
    if not tid:
        ws = get_default_workspace(uid)
        tid = ws.tenant_id
    return AuthContext(
        user_id=from_platform_user_id(payload.get("platform_user_id", to_platform_user_id(uid))),
        platform_user_id=to_platform_user_id(payload.get("platform_user_id", uid)),
        username=payload.get("username", ""),
        tenant_id=tid,
        tenant_type=payload.get("tenant_type", "personal"),
        org_id=payload.get("org_id", ""),
        role=payload.get("role", "member"),
    )


async def get_optional_auth(authorization: str | None = Header(None)) -> AuthContext | None:
    return auth_from_token(parse_bearer(authorization))


async def require_auth(authorization: str | None = Header(None)) -> AuthContext:
    ctx = auth_from_token(parse_bearer(authorization))
    if not ctx:
        raise HTTPException(status_code=401, detail="Authentication required")
    return ctx


def issue_auth_token(user, *, tenant_id: str | None = None) -> str:
    """Build JWT for a marketplace User."""
    from skillos.identity.jwt_auth import issue_jwt
    from skillos.identity.workspaces import get_default_workspace

    ws = get_default_workspace(user.user_id) if not tenant_id else None
    tid = tenant_id or ws.tenant_id
    ctx = tenant_context_for_user(user.user_id, tid)
    return issue_jwt({
        "sub": user.user_id,
        "platform_user_id": to_platform_user_id(user.user_id),
        "username": user.username,
        "role": user.role.value,
        "tenant_id": ctx.tenant_id,
        "tenant_type": ctx.tenant_type,
        "org_id": ctx.org_id,
    })
