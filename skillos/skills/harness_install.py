"""Install a SkillOS skill into local harness directories (Cursor / agents / dsh)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from skillos.skills.discovery import plugin_vs_skill_hint
from skillos.skills.portable_export import build_portable_skill_md

HARNESS_TARGETS = frozenset({"cursor", "agents", "dsh"})
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def resolve_harness_dest(target: str, slug: str, *, project: bool = False, cwd: Path | None = None) -> Path:
    """Resolve install directory; reject unsafe slugs."""
    target = (target or "").strip().lower()
    if target not in HARNESS_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(f"invalid skill slug: {slug!r}")
    home = Path.home()
    base_cwd = cwd or Path.cwd()
    if target == "cursor":
        return home / ".cursor" / "skills" / slug
    if target == "agents":
        root = (base_cwd / ".agents" / "skills") if project else (home / ".agents" / "skills")
        return root / slug
    # dsh
    root = (base_cwd / ".dsh" / "skills") if project else (home / ".dsh" / "skills")
    return root / slug


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
    # Ensure we never escape intended roots
    dest = dest.resolve()
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
