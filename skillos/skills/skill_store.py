"""Skill persistence — Markdown files with YAML frontmatter.

Ported from Skill Distiller's skill_store.py. Cleaned up for SkillOS:
  - Uses pathlib consistently
  - Type hints on all public functions
  - Simplified error handling
  - agentskills.io compatible export path
  - Multi-tenant paths via ``skillos.identity`` (Sprint 0)
"""


import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from skillos.identity.context import TenantContext

_DEFAULT_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _legacy_skills_dir() -> Path:
    """Pre–multi-tenant skills directory (``SKILLOS_SKILLS_DIR`` or ``skills/``)."""
    env = os.getenv("SKILLOS_SKILLS_DIR", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
    else:
        p = _DEFAULT_SKILLS_DIR.resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_skills_dir() -> Path:
    """Primary skills directory for legacy mode or when no tenant context is set."""
    from skillos.identity.context import get_tenant_context, is_legacy_mode

    ctx = get_tenant_context()
    if ctx is not None:
        return ctx.skills_root()
    if is_legacy_mode():
        return _legacy_skills_dir()
    return _legacy_skills_dir()


def resolve_skills_root(tenant: TenantContext | None = None) -> Path:
    """Resolve filesystem root for skill storage under current or explicit tenant."""
    from skillos.identity.context import get_tenant_context, is_legacy_mode

    if tenant is not None:
        return tenant.skills_root()
    ctx = get_tenant_context()
    if ctx is not None:
        return ctx.skills_root()
    if is_legacy_mode():
        return _legacy_skills_dir()
    return _legacy_skills_dir()


# Backward-compatible alias (evaluated at import; prefer get_skills_dir() in new code)
SKILLS_DIR = get_skills_dir()


def mirror_skill_to_workspace(skill_name: str, source_path: Path) -> Path | None:
    """Copy saved SKILL.md to workspace dir when ``SKILLOS_WORKSPACE_SKILLS`` is set."""
    ws = os.getenv("SKILLOS_WORKSPACE_SKILLS", "").strip()
    if not ws or not source_path.exists():
        return None
    dest_root = Path(ws).expanduser()
    if not dest_root.is_absolute():
        dest_root = (Path.cwd() / dest_root).resolve()
    safe = re.sub(r'[<>:"/\\|?*]', "_", skill_name)[:64]
    dest_dir = dest_root / safe
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "SKILL.md"
    shutil.copy2(source_path, dest)
    return dest


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w一-鿿\-]+", "-", name.strip(), flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-").lower()
    return slug or "skill"


def _skill_path(name: str, *, root: Path | None = None) -> Path:
    """Return the path to SKILL.md for a given skill name.

    Uses kebab-case directory name when name is ASCII, otherwise
    falls back to a sanitized form compatible with AgentSkills.io standard.
    """
    from skillos.skills.portable_skill import tool_slug

    # Try kebab-case slug first (AgentSkills.io standard)
    slug = tool_slug(name)
    base = root if root is not None else resolve_skills_root()

    # If the slug directory exists, use it; otherwise use sanitized name
    slug_dir = base / slug
    if slug_dir.exists():
        return slug_dir / "SKILL.md"

    # Legacy path: sanitized original name (backward compat)
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)[:64]
    legacy_dir = base / safe
    if legacy_dir.exists():
        return legacy_dir / "SKILL.md"

    # New skills: use kebab-case slug directory (AgentSkills.io standard)
    return slug_dir / "SKILL.md"


def _split_front_matter(content: str) -> tuple[dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(content)
    if not match:
        return {}, content.lstrip()
    meta = yaml.safe_load(match.group(1)) or {}
    body = content[match.end():]
    return meta, body


def _compose(meta: dict[str, Any], body: str) -> str:
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{header}\n---\n\n{body.lstrip()}"


def _ensure_standard_dirs(skill_dir: Path) -> None:
    """Create AgentSkills.io standard subdirectories if they don't exist.

    Standard: scripts/, references/, assets/
    SkillOS private: .skillos/, .skillos/versions/
    """
    for subdir in ("scripts", "references", "assets",
                   ".skillos", ".skillos/versions"):
        (skill_dir / subdir).mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════

def save_skill(
    name: str,
    body: str,
    meta: dict[str, Any] | None = None,
    *,
    source: str = "",
    source_type: str = "llm_generated",
    llm_args: tuple | None = None,
    epistemic: bool = True,
    tenant: TenantContext | None = None,
) -> Path:
    """Save or update a skill. Auto-increments version, archives old version.

    When epistemic=True and not a draft, runs the epistemology bridge before write.
    When a tenant context is active, writes under ``data/tenants/...`` and records metadata.
    """
    from skillos.identity.context import get_tenant_context

    root = resolve_skills_root(tenant)
    path = _skill_path(name, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure AgentSkills.io standard directory structure
    _ensure_standard_dirs(path.parent)

    now = _now_iso()

    front: dict[str, Any] = {"name": name, "created_at": now, "updated_at": now}
    ctx = tenant or get_tenant_context()
    if ctx is not None:
        front["tenant_id"] = ctx.tenant_id
        front.setdefault("visibility", "private")
        if ctx.dept_id:
            front["dept_id"] = ctx.dept_id

    is_new = not path.exists()
    if is_new and ctx is not None:
        try:
            from skillos.billing.usage import check_skill_quota
            check_skill_quota(ctx, is_new=True)
        except Exception as exc:
            from skillos.billing.usage import QuotaExceededError
            if isinstance(exc, QuotaExceededError):
                raise
            pass

    if meta:
        front.update(meta)

    is_draft = bool(front.get("draft"))

    if not is_draft and not front.get("dna_lineage"):
        try:
            from skillos.knowledge.dna_context import build_skill_dna_meta
            tpl = front.get("domain_template") or front.get("domain_template_id")
            tids = front.get("domain_template_ids")
            dna_meta = build_skill_dna_meta(
                name, body,
                domain_template_id=tpl,
                domain_template_ids=tids if isinstance(tids, list) else None,
            )
            for key, val in dna_meta.items():
                front.setdefault(key, val)
        except Exception:
            pass

    if epistemic and not is_draft:
        try:
            from skillos.knowledge.epistemic_bridge import apply_epistemics_to_skill
            body, summary = apply_epistemics_to_skill(
                body, name,
                source=source or name,
                source_type=source_type,
                llm_args=llm_args,
                run_falsify=True,
            )
            front.update(summary.to_meta())
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Epistemic processing skipped for '%s': %s", name, exc,
            )

    if path.exists():
        existing_meta, _ = _split_front_matter(path.read_text(encoding="utf-8"))
        front["created_at"] = existing_meta.get("created_at", now)
        current_version = existing_meta.get("version", 1)
        new_version = current_version + 1
        front["version"] = new_version
        _archive_version(name, path, current_version, root=root)
    else:
        front["version"] = 1

    front["updated_at"] = now

    # Security scan (non-blocking warning)
    import logging
    _log = logging.getLogger(__name__)
    try:
        from skillos.api.middleware import scan_skill_security
        findings = scan_skill_security(body)
        if findings:
            _log.warning("Skill '%s' has %d security concern(s): %s",
                        name, len(findings),
                        "; ".join(f["description"][:60] for f in findings[:3]))
    except Exception:
        pass

    # Auto-detect variant archetype and register
    try:
        from skillos.skills.variants import VariantRegistry, auto_detect_variants
        groups = auto_detect_variants()
        reg = VariantRegistry()
        for group in groups:
            if group["skill_a"] == name and group["similarity"] == "same_structure":
                reg.register_variant(
                    archetype=group["skill_b"],
                    creator=name, content=body,
                    source="auto-detected", epistemic_level="experience",
                )
            elif group["skill_b"] == name and group["similarity"] == "same_structure":
                reg.register_variant(
                    archetype=group["skill_a"],
                    creator=name, content=body,
                    source="auto-detected", epistemic_level="experience",
                )
    except Exception:
        pass

    path.write_text(_compose(front, body), encoding="utf-8")
    mirror_skill_to_workspace(name, path)

    if ctx is not None:
        try:
            from skillos.identity.models import register_skill_metadata
            register_skill_metadata(
                tenant_id=ctx.tenant_id,
                skill_slug=_slugify(name),
                name=name,
                creator_user_id=ctx.user_id,
                visibility=str(front.get("visibility", "private")),
                dept_id=ctx.dept_id,
                approval_status=str(front.get("approval_status", "draft")),
            )
        except Exception as exc:
            _log.warning("skill_metadata registration skipped for '%s': %s", name, exc)

    if is_new and ctx is not None:
        try:
            from skillos.analytics.funnel import track_funnel
            from skillos.billing.usage import count_skills
            if count_skills(ctx) == 1:
                track_funnel(
                    "first_skill",
                    tenant_id=ctx.tenant_id,
                    user_id=ctx.user_id,
                    detail=name,
                )
        except Exception:
            pass

    return path


def _archive_version(name: str, src_path: Path, version: int, *, root: Path | None = None) -> None:
    """Copy current skill to skills/<name>/v<N>.md."""
    import shutil
    base = root if root is not None else resolve_skills_root()
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)[:64]
    version_dir = base / safe
    version_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src_path), str(version_dir / f"v{version}.md"))


def load_skill(name: str, version: int | None = None, *, tenant: TenantContext | None = None) -> str:
    """Load a skill. If version is None, loads the latest."""
    root = resolve_skills_root(tenant)
    if version is not None:
        safe = re.sub(r'[<>:"/\\|?*]', "_", name)[:64]
        version_path = root / safe / f"v{version}.md"
        if not version_path.exists():
            raise FileNotFoundError(f"Skill version not found: {name} v{version}")
        return version_path.read_text(encoding="utf-8")

    path = _skill_path(name, root=root)
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {name}")
    return path.read_text(encoding="utf-8")


def get_skill_body(content: str) -> str:
    """Extract the body (everything after YAML frontmatter)."""
    _, body = _split_front_matter(content)
    return body.strip()


def list_skills(*, tenant: TenantContext | None = None) -> list[str]:
    """List all skill names under the resolved tenant (or legacy) root."""
    root = resolve_skills_root(tenant)
    root.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for p in sorted(root.glob("*/SKILL.md")):
        content = p.read_text(encoding="utf-8")
        meta, _ = _split_front_matter(content)
        name = meta.get("name") or p.parent.name
        if name not in names:
            names.append(name)
    return names


def delete_skill(name: str, *, tenant: TenantContext | None = None) -> bool:
    """Delete a skill and all associated files including standard subdirectories."""
    import shutil
    root = resolve_skills_root(tenant)
    path = _skill_path(name, root=root)
    # Delete the skill directory (kebab-case slug dir with all contents)
    skill_dir = path.parent
    if skill_dir.exists():
        shutil.rmtree(str(skill_dir))
    # Also try legacy Chinese-name directory for backward compat
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)[:64]
    legacy_dir = root / safe
    if legacy_dir.exists() and legacy_dir != skill_dir:
        shutil.rmtree(str(legacy_dir))
    return True


def skill_exists(name: str, *, tenant: TenantContext | None = None) -> bool:
    return _skill_path(name, root=resolve_skills_root(tenant)).exists()


def load_skill_raw(name: str, *, tenant: TenantContext | None = None) -> dict[str, Any]:
    """Return full skill data: {name, meta, body, path}."""
    root = resolve_skills_root(tenant)
    path = _skill_path(name, root=root)
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {name}")
    content = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(content)
    return {
        "name": meta.get("name", name),
        "meta": meta,
        "body": body.strip(),
        "path": str(path),
    }


def get_skill_versions(name: str, *, tenant: TenantContext | None = None) -> list[int]:
    """Return list of available version numbers."""
    root = resolve_skills_root(tenant)
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)[:64]
    version_dir = root / safe
    if not version_dir.exists():
        return [1]
    versions = []
    for p in version_dir.glob("v*.md"):
        num = re.search(r"v(\d+)\.md$", p.name)
        if num:
            versions.append(int(num.group(1)))
    return sorted(versions) if versions else [1]
