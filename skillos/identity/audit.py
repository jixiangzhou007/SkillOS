"""Skill & workspace audit helpers (Sprint 1)."""

from __future__ import annotations


def log_skill_action(
    *,
    user_id: str = "",
    username: str = "",
    action: str,
    skill_name: str,
    tenant_id: str = "",
    detail: str = "",
) -> None:
    from skillos.marketplace.auth import _log_audit

    merged = detail
    if tenant_id:
        merged = f"tenant={tenant_id}" + (f" {detail}" if detail else "")
    _log_audit(user_id, username, f"skill_{action}", skill_name, merged)


def log_workspace_switch(user_id: str, username: str, tenant_id: str) -> None:
    from skillos.marketplace.auth import _log_audit

    _log_audit(user_id, username, "workspace_switch", tenant_id, "")
