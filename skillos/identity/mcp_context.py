"""MCP runtime auth — resolve personal/org tenant from env token (Sprint 3)."""


import os
from contextlib import contextmanager


def apply_mcp_auth_from_env():
    """Set thread-local tenant from ``SKILLOS_MCP_TOKEN`` or ``SKILLOS_AUTH_TOKEN``."""
    token = os.getenv("SKILLOS_MCP_TOKEN", "").strip() or os.getenv("SKILLOS_AUTH_TOKEN", "").strip()
    if not token:
        return None
    from skillos.identity.middleware import auth_from_token
    auth = auth_from_token(token)
    if not auth:
        return None
    from skillos.identity.context import set_tenant_context
    set_tenant_context(auth.tenant_context())
    return auth


@contextmanager
def mcp_tenant_context():
    from skillos.identity.context import reset_tenant_context, set_tenant_context

    auth = apply_mcp_auth_from_env()
    token = None
    if auth:
        token = set_tenant_context(auth.tenant_context())
    try:
        yield auth
    finally:
        if token is not None:
            reset_tenant_context(token)
