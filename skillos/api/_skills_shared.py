"""Shared helpers and models used by both skills.py and skills_extract.py.

Extracted to avoid circular imports when splitting the API module.
"""

from pydantic import BaseModel

from skillos.identity.middleware import AuthContext

# ── Shared request models ──────────────────────────────────────

class CreateSkillRequest(BaseModel):
    text: str
    content: str = ""
    model: str = ""


class DispatchRequest(BaseModel):
    message: str
    history: list[dict] = []
    mode: str = "chat"
    model: str = ""
    session_id: str = ""
    channel: str = ""       # feishu | wechat | cursor (optional)
    chat_id: str = ""       # IM chat / group id
    user_id: str = ""       # IM user id
    tenant_id: str = ""     # active workspace tenant
    org_id: str = ""
    dept_id: str = ""
    quick_mode: bool = False   # Sprint 4: skip EXPLORING for long input


# ── Shared helpers ─────────────────────────────────────────────


def _tenant_context_from_auth(auth: AuthContext | None):
    """Set thread-local tenant for quota / path resolution within request."""
    if not auth:
        return None
    from skillos.identity.context import set_tenant_context
    return set_tenant_context(auth.tenant_context())


def _reset_tenant(token) -> None:
    if token is None:
        return
    from skillos.identity.context import reset_tenant_context
    reset_tenant_context(token)


def _skills_list(auth: AuthContext | None = None):
    from skillos.skills.skill_store import list_skills
    tenant = auth.tenant_context() if auth else None
    return list_skills(tenant=tenant)


def _tenant_from_context(ctx: dict):
    from skillos.identity.resolver import tenant_from_context
    return tenant_from_context(ctx)
