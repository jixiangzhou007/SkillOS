"""User workspace (tenant) selection — personal + org memberships."""


import sqlite3
import time
from dataclasses import dataclass

from skillos.identity.context import TenantContext
from skillos.identity.models import create_personal_tenant, get_memberships
from skillos.identity.users import to_platform_user_id


@dataclass
class WorkspaceInfo:
    tenant_id: str
    tenant_type: str
    label: str
    org_id: str = ""
    is_default: bool = False


def _conn() -> sqlite3.Connection:
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def ensure_personal_workspace(user_id: str, *, display_name: str = "") -> WorkspaceInfo:
    """Create personal tenant + workspace row if missing."""
    pid = to_platform_user_id(user_id)
    create_personal_tenant(pid, display_name=display_name or "Personal")
    tenant_id = f"personal:{pid}"
    now = time.time()
    conn = _conn()
    conn.execute(
        """INSERT OR IGNORE INTO user_workspaces
           (user_id, tenant_id, tenant_type, label, org_id, is_default, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (pid, tenant_id, "personal", display_name or "Personal", "", 1, now),
    )
    conn.commit()
    return WorkspaceInfo(
        tenant_id=tenant_id,
        tenant_type="personal",
        label=display_name or "Personal",
        is_default=True,
    )


def register_org_workspace(user_id: str, org_id: str, *, label: str) -> WorkspaceInfo:
    pid = to_platform_user_id(user_id)
    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    tenant_id = f"org:{oid}"
    conn = _conn()
    conn.execute(
        """INSERT OR IGNORE INTO user_workspaces
           (user_id, tenant_id, tenant_type, label, org_id, is_default, created_at)
           VALUES (?, ?, ?, ?, ?, 0, ?)""",
        (pid, tenant_id, "organization", label, oid, time.time()),
    )
    conn.commit()
    return WorkspaceInfo(tenant_id=tenant_id, tenant_type="organization", label=label, org_id=oid)


def list_workspaces(user_id: str) -> list[WorkspaceInfo]:
    pid = to_platform_user_id(user_id)
    ensure_personal_workspace(user_id)
    conn = _conn()
    rows = conn.execute(
        """SELECT tenant_id, tenant_type, label, org_id, is_default
           FROM user_workspaces WHERE user_id = ? ORDER BY is_default DESC, created_at""",
        (pid,),
    ).fetchall()
    workspaces = [
        WorkspaceInfo(
            tenant_id=r[0],
            tenant_type=r[1],
            label=r[2],
            org_id=r[3] or "",
            is_default=bool(r[4]),
        )
        for r in rows
    ]
    # Sync org memberships not yet in user_workspaces
    for m in get_memberships(pid):
        tid = f"org:{m.org_id}"
        if not any(w.tenant_id == tid for w in workspaces):
            workspaces.append(register_org_workspace(user_id, m.org_id, label=m.org_id))
    return workspaces


def get_default_workspace(user_id: str) -> WorkspaceInfo:
    workspaces = list_workspaces(user_id)
    for w in workspaces:
        if w.is_default:
            return w
    return workspaces[0]


def set_default_workspace(user_id: str, tenant_id: str) -> WorkspaceInfo:
    pid = to_platform_user_id(user_id)
    if not _can_access(pid, tenant_id):
        raise PermissionError(f"Cannot access workspace {tenant_id}")
    conn = _conn()
    conn.execute("UPDATE user_workspaces SET is_default = 0 WHERE user_id = ?", (pid,))
    conn.execute(
        "UPDATE user_workspaces SET is_default = 1 WHERE user_id = ? AND tenant_id = ?",
        (pid, tenant_id),
    )
    conn.commit()
    for w in list_workspaces(user_id):
        if w.tenant_id == tenant_id:
            return w
    raise LookupError(tenant_id)


def tenant_context_for_user(user_id: str, tenant_id: str | None = None) -> TenantContext:
    tid = tenant_id or get_default_workspace(user_id).tenant_id
    pid = to_platform_user_id(user_id)
    if not _can_access(pid, tid):
        raise PermissionError(tenant_id)
    if tid.startswith("personal:"):
        return TenantContext.personal(pid)
    oid = tid.split(":", 1)[1]
    return TenantContext.organization(oid, user_id=pid)


def _can_access(platform_user_id: str, tenant_id: str) -> bool:
    if tenant_id.startswith("personal:"):
        return tenant_id == f"personal:{platform_user_id}"
    conn = _conn()
    row = conn.execute(
        "SELECT 1 FROM user_workspaces WHERE user_id = ? AND tenant_id = ? LIMIT 1",
        (platform_user_id, tenant_id),
    ).fetchone()
    if row:
        return True
    if tenant_id.startswith("org:"):
        oid = tenant_id.split(":", 1)[1]
        return any(m.org_id == oid for m in get_memberships(platform_user_id))
    return False
