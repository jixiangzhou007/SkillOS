"""Organization departments (Sprint 6)."""


import sqlite3
import time
import uuid
from dataclasses import dataclass

from skillos.identity.models import get_organization


@dataclass
class Department:
    dept_id: str
    org_id: str
    name: str
    created_at: float


def _conn() -> sqlite3.Connection:
    from skillos.db import get_conn
    return get_conn("skillhub.db")


def _normalize_org_id(org_id: str) -> str:
    return org_id if org_id.startswith("org_") else f"org_{org_id}"


def create_department(org_id: str, name: str) -> Department:
    oid = _normalize_org_id(org_id)
    if not get_organization(oid):
        raise LookupError(f"Organization not found: {oid}")
    dept_id = f"dept_{uuid.uuid4().hex[:10]}"
    now = time.time()
    conn = _conn()
    conn.execute(
        "INSERT INTO departments (dept_id, org_id, name, created_at) VALUES (?, ?, ?, ?)",
        (dept_id, oid, name.strip(), now),
    )
    conn.commit()
    return Department(dept_id=dept_id, org_id=oid, name=name.strip(), created_at=now)


def list_departments(org_id: str) -> list[Department]:
    oid = _normalize_org_id(org_id)
    conn = _conn()
    rows = conn.execute(
        "SELECT dept_id, org_id, name, created_at FROM departments WHERE org_id = ? ORDER BY name",
        (oid,),
    ).fetchall()
    return [Department(dept_id=r[0], org_id=r[1], name=r[2], created_at=r[3]) for r in rows]


def get_department(dept_id: str) -> Department | None:
    conn = _conn()
    row = conn.execute(
        "SELECT dept_id, org_id, name, created_at FROM departments WHERE dept_id = ?",
        (dept_id,),
    ).fetchone()
    if not row:
        return None
    return Department(dept_id=row[0], org_id=row[1], name=row[2], created_at=row[3])
