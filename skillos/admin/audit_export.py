"""Org audit CSV export (Sprint 9)."""


import csv
import io
import time

from skillos.identity.models import list_org_members
from skillos.identity.users import from_platform_user_id


def export_org_audit_csv(org_id: str, *, limit: int = 5000) -> str:
    oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
    members = list_org_members(oid)
    raw_ids = {from_platform_user_id(m.user_id) for m in members}

    from skillos.marketplace.auth import _get_conn
    conn = _get_conn()
    if raw_ids:
        placeholders = ",".join("?" * len(raw_ids))
        rows = conn.execute(
            f"""SELECT id, user_id, username, action, target, detail, ip_address, created_at
                FROM audit_log WHERE user_id IN ({placeholders})
                ORDER BY created_at DESC LIMIT ?""",
            list(raw_ids) + [limit],
        ).fetchall()
    else:
        rows = []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "timestamp", "user_id", "username", "action", "target", "detail", "ip"])
    for r in rows:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["created_at"]))
        writer.writerow([r["id"], ts, r["user_id"], r["username"], r["action"], r["target"], r["detail"], r["ip_address"]])
    return buf.getvalue()
