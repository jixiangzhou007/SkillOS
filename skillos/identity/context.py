"""Tenant context — thread-local workspace for skill path isolation."""


import contextvars
import os
from dataclasses import dataclass
from pathlib import Path

_tenant_ctx: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar(
    "skillos_tenant_context", default=None
)


def is_legacy_mode() -> bool:
    """When true (default), skills use ``SKILLOS_SKILLS_DIR`` / ``skills/`` layout."""
    return os.getenv("SKILLOS_LEGACY_MODE", "true").lower() in ("true", "1", "yes")


def get_data_dir() -> Path:
    env = os.getenv("SKILLOS_DATA_DIR", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        return p
    return (Path(__file__).resolve().parents[2] / "data").resolve()


@dataclass(frozen=True)
class TenantContext:
    """Runtime tenant scope for API / MCP / agent requests."""

    tenant_id: str
    tenant_type: str  # personal | organization
    user_id: str = ""
    org_id: str = ""
    dept_id: str = ""

    @classmethod
    def personal(cls, user_id: str) -> TenantContext:
        uid = user_id if user_id.startswith("usr_") else f"usr_{user_id}"
        return cls(
            tenant_id=f"personal:{uid}",
            tenant_type="personal",
            user_id=uid,
        )

    @classmethod
    def organization(cls, org_id: str, user_id: str = "", dept_id: str = "") -> TenantContext:
        oid = org_id if org_id.startswith("org_") else f"org_{org_id}"
        uid = user_id
        if user_id and not user_id.startswith("usr_"):
            uid = f"usr_{user_id}"
        return cls(
            tenant_id=f"org:{oid}",
            tenant_type="organization",
            user_id=uid,
            org_id=oid,
            dept_id=dept_id,
        )

    @classmethod
    def from_tenant_id(cls, tenant_id: str, user_id: str = "", dept_id: str = "") -> TenantContext:
        if tenant_id.startswith("personal:"):
            uid = tenant_id.split(":", 1)[1]
            return cls.personal(uid)
        if tenant_id.startswith("org:"):
            oid = tenant_id.split(":", 1)[1]
            return cls.organization(oid, user_id=user_id, dept_id=dept_id)
        raise ValueError(f"Invalid tenant_id: {tenant_id}")

    def skills_root(self) -> Path:
        """Filesystem root for this tenant's skill directories."""
        base = get_data_dir() / "tenants"
        if self.tenant_type == "personal":
            uid = self.user_id or self.tenant_id.split(":", 1)[1]
            root = base / "personal" / uid / "skills"
        else:
            oid = self.org_id or self.tenant_id.split(":", 1)[1]
            if self.dept_id:
                dept = self.dept_id.replace("/", "_")
                root = base / "org" / oid / "departments" / dept / "skills"
            else:
                root = base / "org" / oid / "skills"
        root.mkdir(parents=True, exist_ok=True)
        return root


def get_tenant_context() -> TenantContext | None:
    return _tenant_ctx.get()


def set_tenant_context(ctx: TenantContext | None) -> contextvars.Token:
    return _tenant_ctx.set(ctx)


def reset_tenant_context(token: contextvars.Token) -> None:
    _tenant_ctx.reset(token)
