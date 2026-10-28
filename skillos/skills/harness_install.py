"""Install a SkillOS skill into local harness directories (Cursor / agents / dsh)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from skillos.skills.discovery import plugin_vs_skill_hint
from skillos.skills.portable_export import build_portable_skill_md

HARNESS_TARGETS = frozenset({"cursor", "agents", "dsh"})
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _skills_root(target: str, *, project: bool = False, cwd: Path | None = None) -> Path:
    """Allowed parent directory for harness installs (before slug)."""
    target = (target or "").strip().lower()
    home = Path.home()
    base_cwd = (cwd or Path.cwd()).resolve()
    if target == "cursor":
        return (home / ".cursor" / "skills").resolve()
    if target == "agents":
        root = (base_cwd / ".agents" / "skills") if project else (home / ".agents" / "skills")
        return root.resolve()
    if target == "dsh":
        root = (base_cwd / ".dsh" / "skills") if project else (home / ".dsh" / "skills")
        return root.resolve()
    raise ValueError(f"unsupported target: {target}")


def _ensure_under(dest: Path, root: Path) -> Path:
    """Reject path escape after resolve (symlinks / ..)."""
    dest_r = dest.resolve()
    root_r = root.resolve()
    try:
        dest_r.relative_to(root_r)
    except ValueError as exc:
        raise ValueError(f"install path escapes harness root: {dest_r}") from exc
    return dest_r


def resolve_harness_dest(target: str, slug: str, *, project: bool = False, cwd: Path | None = None) -> Path:
    """Resolve install directory; reject unsafe slugs and path escape."""
    target = (target or "").strip().lower()
    if target not in HARNESS_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(f"invalid skill slug: {slug!r}")
    root = _skills_root(target, project=project, cwd=cwd)
    return _ensure_under(root / slug, root)


def install_skill_to_harness(
    name: str,
    *,
    target: str = "cursor",
    project: bool = False,
    tenant=None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Write portable SKILL.md (+ trust marker) into a harness folder."""
    info = build_portable_skill_md(name, tenant=tenant)
    slug = str(info["slug"])
    dest = resolve_harness_dest(target, slug, project=project, cwd=cwd)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "SKILL.md").write_text(info["portable_md"], encoding="utf-8")
    (dest / "SKILLOS_TRUST.txt").write_text(
        f"trust_tier={info['trust_tier']}\n"
        f"model_invocable={info['catalog']['model_invocable']}\n"
        f"source={info['catalog']['source']}\n"
        f"{plugin_vs_skill_hint()}\n",
        encoding="utf-8",
    )
    hint = ""
    if target == "dsh":
        hint = "npx @deepseek-ai/dsh web"
    elif target == "cursor":
        hint = f"@{slug}"
    return {
        "ok": True,
        "name": info["display_name"],
        "slug": slug,
        "target": target,
        "project": bool(project and target in ("agents", "dsh")),
        "path": str(dest),
        "trust_tier": info["trust_tier"],
        "model_invocable": info["catalog"]["model_invocable"],
        "hint": hint,
    }
