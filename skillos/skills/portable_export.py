"""Zip bundle for one-click install (Cursor / Claude / agents / DeepSeek Harness)."""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING, Any

from skillos.skills.discovery import catalog_summary, plugin_vs_skill_hint
from skillos.skills.portable_skill import (
    build_description,
    format_install_guide,
    install_paths,
    tool_slug,
)
from skillos.skills.skill_store import _compose, load_skill_raw

if TYPE_CHECKING:
    from skillos.identity.context import TenantContext


def build_portable_skill_md(name: str, *, tenant: TenantContext | None = None) -> dict[str, Any]:
    """Load skill and build portable SKILL.md with AgentSkills frontmatter."""
    raw = load_skill_raw(name, tenant=tenant)
    meta = dict(raw["meta"] or {})
    body = raw["body"]
    slug = meta.get("portable_slug") or tool_slug(name, body)
    description = meta.get("description") or build_description(name, body)
    from skillos.evaluation.trust_tier import enrich_epistemic_with_trust
    from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload

    ep = enrich_epistemic_with_trust(format_epistemic_api_payload(meta), meta)
    tier = str(ep.get("trust_tier") or meta.get("trust_tier") or "draft")
    cat = catalog_summary(
        name=name,
        description=description,
        trust_tier=tier,
        meta=meta,
        portable_slug=str(slug),
    )
    portable_meta: dict[str, Any] = {
        "name": slug,
        "description": description,
        "metadata": {
            "skillos_trust_tier": tier,
            "skillos_source": cat["source"],
            "skillos_model_invocable": "true" if cat["model_invocable"] else "false",
        },
    }
    portable_md = _compose(portable_meta, body)
    return {
        "display_name": name,
        "slug": slug,
        "description": description,
        "portable_md": portable_md,
        "meta": meta,
        "trust_tier": tier,
        "catalog": cat,
        "paths": install_paths(str(slug)),
    }


def _trust_txt(info: dict[str, Any]) -> str:
    cat = info["catalog"]
    tier = info["trust_tier"]
    lines = [
        f"Skill: {info['display_name']}",
        f"Slug: {info['slug']}",
        f"Trust Tier: {tier}",
        f"Source layer: {cat['source']} ({cat['source_label']})",
        f"model_invocable: {cat['model_invocable']}",
        f"user_invocable: {cat['user_invocable']}",
        "",
        plugin_vs_skill_hint(),
        "",
        "Draft skills should not be placed in model-facing catalogs.",
        "Provisional = apprentice trial; Verified = Dual Gate passed.",
        "Local Quick8 / smoke ≠ official SkillsBench pass rate.",
    ]
    return "\n".join(lines) + "\n"


def _install_txt(info: dict[str, Any]) -> str:
    paths = info["paths"]
    slug = info["slug"]
    lines = [
        "Copy the extracted folder (or SKILL.md) into ONE of:",
        "",
        f"Cursor:              {paths.get('cursor')}",
        f"Claude Code:         {paths.get('claude_code')}",
        f"Codex:               {paths.get('codex')}",
        f"Project .agents:     {paths.get('agents_project')}",
        f"User .agents:        {paths.get('agents_user')}",
        f"DeepSeek Harness:    {paths.get('dsh_user')}",
        f"Project .dsh:        {paths.get('dsh_project')}",
        "",
        "Then:",
        f"  - Cursor: new chat, @{slug}",
        "  - DeepSeek Harness: npx @deepseek-ai/dsh web",
        "",
        "Or from SkillOS repo:",
        f'  python scripts/install_skill_to_harness.py "{info["display_name"]}" --target dsh',
    ]
    return "\n".join(lines) + "\n"


def build_install_zip(name: str, *, tenant: TenantContext | None = None) -> tuple[bytes, str]:
    """Return (zip bytes, suggested filename)."""
    info = build_portable_skill_md(name, tenant=tenant)
    slug = info["slug"]
    readme = format_install_guide(info["display_name"], slug).strip()
    readme += (
        "\n\n## 目录结构\n"
        f"解压后将 `{slug}/` 文件夹复制到对应工具的 skills 目录，"
        f"或只复制其中的 SKILL.md。\n"
        f"\n本包另含 INSTALL.txt / TRUST.txt（发现层与调用策略）。\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/SKILL.md", info["portable_md"])
        zf.writestr("README.txt", readme + "\n")
        zf.writestr("INSTALL.txt", _install_txt(info))
        zf.writestr("TRUST.txt", _trust_txt(info))
    return buf.getvalue(), f"{slug}-skill.zip"
