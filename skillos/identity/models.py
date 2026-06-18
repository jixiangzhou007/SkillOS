"""Tenant / organization persistence (SQLite via skillos.db)."""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass

from skillos.identity.context import TenantContext


@dataclass
class TenantRecord:
    tenant_id: str
    tenant_type: str
    owner_user_id: str
    org_id: str
    name: str
    created_at: float


@dataclass
class Organization:
    org_id: str
    slug: str
    display_name: str
    plan: str
    created_at: float


@dataclass
class Membership:
    user_id: str
    org_id: str
    role: str
    dept_id: str
    created_at: float


def _conn() -> sqlite3.Connection:
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_personal_tenant(user_id: str, *, display_name: str = "") -> TenantRecord:
    """Register a personal tenant for a user (idempotent on tenant_id)."""
    ctx = TenantContext.personal(user_id)
    now = time.time()
    conn = _conn()
    existing = conn.execute(
        "SELECT tenant_id FROM tenants WHERE tenant_id = ?", (ctx.tenant_id,)
    ).fetchone()
    if existing:
        row = conn.execute(
            "SELECT * FROM tenants WHERE tenant_id = ?", (ctx.tenant_id,)
        ).fetchone()
        return _row_to_tenant(row)

    conn.execute(
        """INSERT INTO tenants (tenant_id, tenant_type, owner_user_id, org_id, name, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ctx.tenant_id, "personal", ctx.user_id, "", display_name or "Personal", now),
    )
    conn.commit()
    ctx.skills_root()
    return TenantRecord(
        tenant_id=ctx.tenant_id,
        tenant_type="personal",
        owner_user_id=ctx.user_id,
        org_id="",
        name=display_name or "Personal",
        created_at=now,
    )


def create_organization(
    display_name: str,
    *,
    slug: str = "",
    owner_user_id: str,
    plan: str = "team",
) -> tuple[Organization, TenantRecord, Membership]:
    """Create org tenant + membership for owner."""
    from skillos.identity.workspaces import register_org_workspace

    slug = slug or _slugify(display_name)
    org_id = _new_id("org")
    tenant_id = f"org:{org_id}"
    uid = owner_user_id if owner_user_id.startswith("usr_") else f"usr_{owner_user_id}"
    now = time.time()
    conn = _conn()

    conn.execute(
        """INSERT INTO organizations (org_id, slug, display_name, plan, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (org_id, slug, display_name, plan, now),
    )
    conn.execute(
        """INSERT INTO tenants (tenant_id, tenant_type, owner_user_id, org_id, name, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (tenant_id, "organization", uid, org_id, display_name, now),
    )
    conn.execute(
        """INSERT INTO memberships (user_id, org_id, role, dept_id, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (uid, org_id, "org_admin", "", now),
    )
    conn.commit()
    register_org_workspace(uid, org_id, label=display_name)

    org = Organization(org_id=org_id, slug=slug, display_name=display_name, plan=plan, created_at=now)
    tenant = TenantRecord(
        tenant_id=tenant_id,
        tenant_type="organization",
        owner_user_id=uid,
        org_id=org_id,
        name=display_name,
        created_at=now,
    )
    membership = Membership(user_id=uid, org_id=org_id, role="org_admin", dept_id="", created_at=now)
    return org, tenant, membership


def get_tenant(tenant_id: str) -> TenantRecord | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
    if not row:
        return None
    return _row_to_tenant(row)


def get_memberships(user_id: str) -> list[Membership]:
    uid = user_id if user_id.startswith("usr_") else f"usr_{user_id}"
    conn = _conn()
    rows = conn.execute(
        "SELECT user_id, org_id, role, dept_id, created_at FROM memberships WHERE user_id = ?",
        (uid,),
    ).fetchall()
    return [
        Membership(user_id=r[0], org_id=r[1], role=r[2], dept_id=r[3], created_at=r[4])
        for r in rows
    ]


def get_organization(org_id: str) -> Organization | None:
    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    conn = _conn()
    row = conn.execute(
        "SELECT org_id, slug, display_name, plan, created_at FROM organizations WHERE org_id = ?",
        (oid,),
    ).fetchone()
    if not row:
        return None
    return Organization(org_id=row[0], slug=row[1], display_name=row[2], plan=row[3], created_at=row[4])


def get_member_role(platform_user_id: str, org_id: str) -> str | None:
    """Return membership role or None if not a member."""
    uid = platform_user_id if platform_user_id.startswith("usr_") else f"usr_{platform_user_id}"
    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    conn = _conn()
    row = conn.execute(
        "SELECT role FROM memberships WHERE user_id = ? AND org_id = ?",
        (uid, oid),
    ).fetchone()
    return row[0] if row else None


def list_org_members(org_id: str) -> list[Membership]:
    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    conn = _conn()
    rows = conn.execute(
        "SELECT user_id, org_id, role, dept_id, created_at FROM memberships WHERE org_id = ? ORDER BY role, user_id",
        (oid,),
    ).fetchall()
    return [
        Membership(user_id=r[0], org_id=r[1], role=r[2], dept_id=r[3], created_at=r[4])
        for r in rows
    ]


def add_org_member(
    org_id: str,
    *,
    platform_user_id: str,
    role: str = "member",
    dept_id: str = "",
) -> Membership:
    """Add user to org; idempotent on (user_id, org_id)."""
    from skillos.identity.workspaces import register_org_workspace

    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    uid = platform_user_id if platform_user_id.startswith("usr_") else f"usr_{platform_user_id}"
    org = get_organization(oid)
    if not org:
        raise LookupError(f"Organization not found: {oid}")

    now = time.time()
    conn = _conn()
    conn.execute(
        """INSERT INTO memberships (user_id, org_id, role, dept_id, created_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id, org_id) DO UPDATE SET
             role=excluded.role,
             dept_id=excluded.dept_id""",
        (uid, oid, role, dept_id, now),
    )
    conn.commit()
    register_org_workspace(uid, oid, label=org.display_name)
    return Membership(user_id=uid, org_id=oid, role=role, dept_id=dept_id, created_at=now)


def list_user_organizations(platform_user_id: str) -> list[Organization]:
    uid = platform_user_id if platform_user_id.startswith("usr_") else f"usr_{platform_user_id}"
    conn = _conn()
    rows = conn.execute(
        """SELECT o.org_id, o.slug, o.display_name, o.plan, o.created_at
           FROM organizations o
           JOIN memberships m ON m.org_id = o.org_id
           WHERE m.user_id = ?
           ORDER BY o.display_name""",
        (uid,),
    ).fetchall()
    return [
        Organization(org_id=r[0], slug=r[1], display_name=r[2], plan=r[3], created_at=r[4])
        for r in rows
    ]


def register_skill_metadata(
    *,
    tenant_id: str,
    skill_slug: str,
    name: str,
    creator_user_id: str = "",
    visibility: str = "private",
    dept_id: str = "",
    approval_status: str = "draft",
) -> None:
    now = time.time()
    conn = _conn()
    conn.execute(
        """INSERT INTO skill_metadata
           (tenant_id, skill_slug, name, visibility, creator_user_id, dept_id,
            created_at, updated_at, approval_status, reviewed_by, reviewed_at, review_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', 0.0, '')
           ON CONFLICT(tenant_id, skill_slug) DO UPDATE SET
             name=excluded.name,
             visibility=excluded.visibility,
             updated_at=excluded.updated_at,
             dept_id=excluded.dept_id""",
        (tenant_id, skill_slug, name, visibility, creator_user_id, dept_id, now, now, approval_status),
    )
    conn.commit()


def get_skill_metadata(tenant_id: str, skill_slug: str) -> dict | None:
    conn = _conn()
    row = conn.execute(
        """SELECT skill_slug, name, visibility, creator_user_id, dept_id,
                  created_at, updated_at, approval_status, reviewed_by, reviewed_at, review_notes
           FROM skill_metadata WHERE tenant_id = ? AND skill_slug = ?""",
        (tenant_id, skill_slug),
    ).fetchone()
    if not row:
        return None
    return {
        "skill_slug": row[0],
        "name": row[1],
        "visibility": row[2],
        "creator_user_id": row[3],
        "dept_id": row[4],
        "created_at": row[5],
        "updated_at": row[6],
        "approval_status": row[7] if len(row) > 7 else "draft",
        "reviewed_by": row[8] if len(row) > 8 else "",
        "reviewed_at": row[9] if len(row) > 9 else 0.0,
        "review_notes": row[10] if len(row) > 10 else "",
    }


def update_skill_approval(
    *,
    tenant_id: str,
    skill_slug: str,
    approval_status: str,
    reviewed_by: str = "",
    reviewed_at: float = 0.0,
    review_notes: str = "",
) -> None:
    now = time.time()
    conn = _conn()
    conn.execute(
        """UPDATE skill_metadata SET
             approval_status = ?,
             reviewed_by = ?,
             reviewed_at = ?,
             review_notes = ?,
             updated_at = ?
           WHERE tenant_id = ? AND skill_slug = ?""",
        (approval_status, reviewed_by, reviewed_at, review_notes, now, tenant_id, skill_slug),
    )
    conn.commit()


def list_skill_metadata(tenant_id: str) -> list[dict]:
    conn = _conn()
    rows = conn.execute(
        """SELECT skill_slug, name, visibility, creator_user_id, dept_id,
                  created_at, updated_at, approval_status, reviewed_by, reviewed_at, review_notes
           FROM skill_metadata WHERE tenant_id = ? ORDER BY updated_at DESC""",
        (tenant_id,),
    ).fetchall()
    return [
        {
            "skill_slug": r[0],
            "name": r[1],
            "visibility": r[2],
            "creator_user_id": r[3],
            "dept_id": r[4],
            "created_at": r[5],
            "updated_at": r[6],
            "approval_status": r[7] if len(r) > 7 else "draft",
            "reviewed_by": r[8] if len(r) > 8 else "",
            "reviewed_at": r[9] if len(r) > 9 else 0.0,
            "review_notes": r[10] if len(r) > 10 else "",
        }
        for r in rows
    ]


def _row_to_tenant(row: sqlite3.Row | tuple) -> TenantRecord:
    if hasattr(row, "keys"):
        return TenantRecord(
            tenant_id=row["tenant_id"],
            tenant_type=row["tenant_type"],
            owner_user_id=row["owner_user_id"],
            org_id=row["org_id"],
            name=row["name"],
            created_at=row["created_at"],
        )
    return TenantRecord(
        tenant_id=row[0],
        tenant_type=row[1],
        owner_user_id=row[2],
        org_id=row[3],
        name=row[4],
        created_at=row[5],
    )


def _slugify(name: str) -> str:
    import re
    slug = re.sub(r"[^\w\-]+", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "org"
