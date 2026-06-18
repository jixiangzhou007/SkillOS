"""Copy skills between tenants (Sprint 6 — Personal → Org)."""

from __future__ import annotations

import re

from skillos.identity.context import TenantContext
from skillos.skills.skill_store import get_skill_body, load_skill_raw, save_skill, skill_exists


class SkillCopyError(Exception):
    pass


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", name.strip().lower())
    return re.sub(r"-+", "-", slug).strip("-") or "skill"


def copy_skill_to_org(
    skill_name: str,
    *,
    personal_tenant: TenantContext,
    org_id: str,
    dept_id: str = "",
    creator_user_id: str = "",
    new_name: str | None = None,
) -> str:
    """Copy a skill from personal workspace into an org tenant (draft approval)."""
    if not personal_tenant.tenant_id.startswith("personal:"):
        raise SkillCopyError("Source must be a personal tenant")
    try:
        raw = load_skill_raw(skill_name, tenant=personal_tenant)
    except FileNotFoundError as exc:
        raise SkillCopyError(f"Skill not found in personal workspace: {skill_name}") from exc

    target_name = (new_name or raw["name"]).strip()
    dest = TenantContext.organization(org_id, user_id=creator_user_id, dept_id=dept_id)
    if skill_exists(target_name, tenant=dest):
        raise SkillCopyError(f"Skill already exists in org: {target_name}")

    body = raw["body"] or get_skill_body(raw.get("content", ""))
    meta = dict(raw.get("meta") or {})
    for key in ("tenant_id", "created_at", "updated_at", "version"):
        meta.pop(key, None)
    meta["visibility"] = "org"
    meta["approval_status"] = "draft"
    meta["copied_from"] = skill_name
    meta["copied_from_tenant"] = personal_tenant.tenant_id
    if dept_id:
        meta["dept_id"] = dept_id

    save_skill(
        target_name,
        body,
        meta=meta,
        source=f"copy:{personal_tenant.tenant_id}",
        source_type="copy",
        epistemic=False,
        tenant=dest,
    )
    return target_name
