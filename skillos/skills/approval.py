"""Org skill approval state machine — draft → pending → published (Sprint 3)."""

from __future__ import annotations

import time
from enum import Enum
from typing import Literal

Action = Literal["submit", "approve", "reject"]


class ApprovalStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"


_TRANSITIONS: dict[tuple[ApprovalStatus, Action], ApprovalStatus] = {
    (ApprovalStatus.DRAFT, "submit"): ApprovalStatus.PENDING,
    (ApprovalStatus.PENDING, "approve"): ApprovalStatus.PUBLISHED,
    (ApprovalStatus.PENDING, "reject"): ApprovalStatus.DRAFT,
}


class ApprovalError(Exception):
    """Invalid transition or permission denied."""


def can_transition(current: str, action: Action) -> bool:
    try:
        st = ApprovalStatus(current)
    except ValueError:
        return False
    return (st, action) in _TRANSITIONS


def next_status(current: str, action: Action) -> str:
    try:
        st = ApprovalStatus(current)
    except ValueError as e:
        raise ApprovalError(f"Unknown status: {current}") from e
    key = (st, action)
    if key not in _TRANSITIONS:
        raise ApprovalError(f"Cannot {action} from {current}")
    return _TRANSITIONS[key].value


def get_metadata(tenant_id: str, skill_slug: str) -> dict | None:
    from skillos.identity.models import get_skill_metadata
    return get_skill_metadata(tenant_id, skill_slug)


def list_by_status(tenant_id: str, status: str) -> list[dict]:
    from skillos.identity.models import list_skill_metadata
    return [m for m in list_skill_metadata(tenant_id) if m.get("approval_status", "draft") == status]


def require_reviewer_role(platform_user_id: str, org_id: str) -> None:
    from skillos.identity.models import get_member_role
    role = get_member_role(platform_user_id, org_id)
    if role not in ("org_admin", "reviewer"):
        raise ApprovalError("org_admin or reviewer required")


def transition(
    *,
    tenant_id: str,
    skill_slug: str,
    action: Action,
    actor_platform_id: str,
    actor_role: str,
    notes: str = "",
) -> dict:
    """Apply approval action; returns updated metadata row."""
    from skillos.identity.models import get_skill_metadata, update_skill_approval

    if not tenant_id.startswith("org:"):
        raise ApprovalError("Approval flow applies to organization tenants only")

    meta = get_skill_metadata(tenant_id, skill_slug)
    if not meta:
        raise ApprovalError(f"Skill not registered: {skill_slug}")

    current = meta.get("approval_status", ApprovalStatus.DRAFT.value)
    if action in ("approve", "reject"):
        org_id = tenant_id.split(":", 1)[1]
        if actor_role not in ("org_admin", "reviewer"):
            require_reviewer_role(actor_platform_id, org_id)

    new_status = next_status(current, action)
    now = time.time()
    reviewed_by = actor_platform_id if action in ("approve", "reject") else meta.get("reviewed_by", "")
    reviewed_at = now if action in ("approve", "reject") else meta.get("reviewed_at", 0.0)

    update_skill_approval(
        tenant_id=tenant_id,
        skill_slug=skill_slug,
        approval_status=new_status,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        review_notes=notes,
    )

    if action == "approve":
        _publish_skill_file(tenant_id, meta.get("name") or skill_slug)

    if action == "reject":
        _mark_skill_draft(tenant_id, meta.get("name") or skill_slug)

    from skillos.identity.audit import log_skill_action
    log_skill_action(
        user_id=actor_platform_id,
        action=f"approval_{action}",
        skill_name=meta.get("name", skill_slug),
        tenant_id=tenant_id,
        detail=f"{current}→{new_status}",
    )

    updated = get_skill_metadata(tenant_id, skill_slug) or {}
    _notify_feishu(action, updated, notes)
    return updated


def _tenant_context_from_id(tenant_id: str, dept_id: str = ""):
    from skillos.identity.context import TenantContext
    if tenant_id.startswith("org:"):
        oid = tenant_id.split(":", 1)[1]
        return TenantContext.organization(oid, dept_id=dept_id)
    if tenant_id.startswith("personal:"):
        uid = tenant_id.split(":", 1)[1]
        return TenantContext.personal(uid)
    raise ApprovalError(f"Invalid tenant_id: {tenant_id}")


def _publish_skill_file(tenant_id: str, skill_name: str) -> None:
    from skillos.skills.skill_store import load_skill_raw, save_skill

    meta_row = get_metadata(tenant_id, _slug(skill_name)) or {}
    dept_id = meta_row.get("dept_id", "")
    tenant = _tenant_context_from_id(tenant_id, dept_id=dept_id)
    raw = load_skill_raw(skill_name, tenant=tenant)
    front = dict(raw.get("meta") or {})
    front.pop("draft", None)
    front["visibility"] = "team"
    front["approval_status"] = ApprovalStatus.PUBLISHED.value
    save_skill(
        skill_name,
        raw.get("body", ""),
        meta=front,
        epistemic=False,
        tenant=tenant,
    )


def _mark_skill_draft(tenant_id: str, skill_name: str) -> None:
    from skillos.skills.skill_store import load_skill_raw, save_skill

    meta_row = get_metadata(tenant_id, _slug(skill_name)) or {}
    tenant = _tenant_context_from_id(tenant_id, dept_id=meta_row.get("dept_id", ""))
    raw = load_skill_raw(skill_name, tenant=tenant)
    front = dict(raw.get("meta") or {})
    front["draft"] = True
    front["approval_status"] = ApprovalStatus.DRAFT.value
    save_skill(skill_name, raw.get("body", ""), meta=front, epistemic=False, tenant=tenant)


def _slug(name: str) -> str:
    from skillos.skills.skill_store import _slugify
    return _slugify(name)


def _notify_feishu(action: Action, meta: dict, notes: str) -> None:
    import os
    webhook = os.getenv("FEISHU_APPROVAL_WEBHOOK", "").strip()
    if not webhook:
        return
    try:
        from skillos.channels.feishu_notify import send_approval_card
        send_approval_card(webhook, action=action, skill_name=meta.get("name", ""), notes=notes)
    except Exception:
        pass
