#!/usr/bin/env python3
"""Bootstrap org pilot: create org, departments, demo users, print dispatch curls.

Usage:
  python scripts/pilot_bootstrap.py [--org-name "Pilot Corp"] [--dry-run]

Requires SKILLOS_DATA_DIR (optional) and SKILLOS_LEGACY_MODE=false for tenant paths.
"""


import argparse
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PASSWORD = "pilot1234"

BATCH1_USERS = [
    {"username": "champ_eng", "role": "member", "dept_id": "engineering", "label": "研发 Champion"},
    {"username": "member_eng1", "role": "member", "dept_id": "engineering", "label": "研发成员 1"},
    {"username": "champ_prod", "role": "member", "dept_id": "product", "label": "产品 Champion"},
    {"username": "member_prod1", "role": "member", "dept_id": "product", "label": "产品成员 1"},
]

BATCH1_DEPARTMENTS = [
    {"dept_id": "engineering", "name": "研发部", "max_skills": 30, "max_llm_monthly": 150},
    {"dept_id": "product", "name": "产品部", "max_skills": 30, "max_llm_monthly": 150},
]

PILOT_USERS = [
    {"username": "pilot_admin", "role": "org_admin", "dept_id": "", "label": "Org 管理员"},
    {"username": "champ_cs", "role": "member", "dept_id": "customer-service", "label": "客服 Champion"},
    {"username": "member_cs1", "role": "member", "dept_id": "customer-service", "label": "客服成员 1"},
    {"username": "member_cs2", "role": "member", "dept_id": "customer-service", "label": "客服成员 2"},
    {"username": "champ_fin", "role": "member", "dept_id": "finance", "label": "财务 Champion"},
    {"username": "member_fin1", "role": "member", "dept_id": "finance", "label": "财务成员 1"},
    {"username": "member_fin2", "role": "member", "dept_id": "finance", "label": "财务成员 2"},
]


def bootstrap(*, org_name: str = "Pilot Corp", api_base: str = "http://127.0.0.1:8765", batch1: bool = False) -> int:
    os.environ.setdefault("SKILLOS_LEGACY_MODE", "false")
    if not os.getenv("SKILLOS_JWT_SECRET"):
        os.environ["SKILLOS_JWT_SECRET"] = "pilot-dev-secret"

    from skillos.marketplace.auth import create_user, authenticate_password
    from skillos.identity.models import create_organization, add_org_member
    from skillos.identity.middleware import issue_auth_token
    from skillos.identity.workspaces import set_default_workspace
    from skillos.db import get_db_dir

    admin_user = None
    created_users = []

    users = list(PILOT_USERS)
    if batch1:
        users = users + BATCH1_USERS

    for spec in users:
        user = create_user(spec["username"], DEFAULT_PASSWORD, "member", email=f"{spec['username']}@pilot.local")
        if not user:
            user = authenticate_password(spec["username"], DEFAULT_PASSWORD)
        if not user:
            print(f"Failed to create/find user {spec['username']}", file=sys.stderr)
            return 1
        created_users.append({**spec, "user_id": user.user_id})
        if spec["username"] == "pilot_admin":
            admin_user = user

    if not admin_user:
        print("pilot_admin missing", file=sys.stderr)
        return 1

    org, tenant, _ = create_organization(org_name, owner_user_id=admin_user.user_id)

    from skillos.identity.departments import create_department
    from skillos.billing.dept_quota import set_dept_quota

    for dept in [{"dept_id": "customer-service", "name": "客服部"}, {"dept_id": "finance", "name": "财务部"}]:
        try:
            d = create_department(org.org_id, dept["name"])
            set_dept_quota(d.dept_id, org.org_id, max_skills=40, max_llm_monthly=120)
        except Exception:
            set_dept_quota(dept["dept_id"], org.org_id, max_skills=40, max_llm_monthly=120)

    if batch1:
        for dept in BATCH1_DEPARTMENTS:
            try:
                d = create_department(org.org_id, dept["name"])
                set_dept_quota(d.dept_id, org.org_id, max_skills=dept["max_skills"], max_llm_monthly=dept["max_llm_monthly"])
            except Exception:
                set_dept_quota(dept["dept_id"], org.org_id, max_skills=dept["max_skills"], max_llm_monthly=dept["max_llm_monthly"])

    for spec in created_users:
        if spec["username"] == "pilot_admin":
            continue
        from skillos.identity.users import to_platform_user_id
        add_org_member(
            org.org_id,
            platform_user_id=to_platform_user_id(spec["user_id"]),
            role=spec["role"],
            dept_id=spec["dept_id"],
        )

    set_default_workspace(admin_user.user_id, tenant.tenant_id)
    admin_token = issue_auth_token(admin_user, tenant_id=tenant.tenant_id)

    tokens = {}
    for spec in created_users:
        user = authenticate_password(spec["username"], DEFAULT_PASSWORD)
        if not user:
            continue
        tid = tenant.tenant_id
        set_default_workspace(user.user_id, tid)
        tokens[spec["username"]] = issue_auth_token(user, tenant_id=tid)

    out_dir = get_db_dir() / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "org_id": org.org_id,
        "org_name": org.display_name,
        "tenant_id": tenant.tenant_id,
        "password": DEFAULT_PASSWORD,
        "users": created_users,
        "tokens": {k: v[:20] + "..." for k, v in tokens.items()},
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Full tokens for local dev only
    secrets_path = out_dir / "tokens.local.json"
    secrets_path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")

    print(f"✓ Org created: {org.display_name} ({tenant.tenant_id})")
    print(f"✓ {len(created_users)} users · password: {DEFAULT_PASSWORD}")
    print(f"✓ Manifest: {manifest_path}")
    print()
    print("--- Sample dispatch (客服 Champion) ---")
    cs_token = tokens.get("champ_cs", admin_token)
    print(f"""curl -X POST {api_base}/api/skills/dispatch \\
  -H "Authorization: Bearer {cs_token[:40]}..." \\
  -H "Content-Type: application/json" \\
  -d '{{"message":"帮我沉淀电商退款标准流程","channel":"feishu","chat_id":"oc_pilot_cs","user_id":"ou_champ_cs","dept_id":"customer-service"}}'""")
    print()
    print("Web: login as champ_cs /", DEFAULT_PASSWORD, "→ switch workspace to", org.display_name)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap SkillOS org pilot")
    parser.add_argument("--org-name", default="Pilot Corp", help="Organization display name")
    parser.add_argument("--admin-user", default="pilot_admin", help="Org admin username (default pilot_admin)")
    parser.add_argument("--batch1", action="store_true", help="Add Batch 1 departments (engineering, product)")
    parser.add_argument("--api-base", default="http://127.0.0.1:8765", help="API base URL for curl hints")
    args = parser.parse_args()

    if args.dry_run:
        print(json.dumps({"org_name": args.org_name, "users": PILOT_USERS}, indent=2, ensure_ascii=False))
        return 0

    return bootstrap(org_name=args.org_name, api_base=args.api_base, batch1=args.batch1)


if __name__ == "__main__":
    raise SystemExit(main())
