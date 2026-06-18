"""Zip bundle for one-click install (Cursor / Claude Code / Trae)."""


import io
import zipfile
from typing import TYPE_CHECKING

from skillos.skills.portable_skill import build_description, format_install_guide, tool_slug
from skillos.skills.skill_store import _compose, load_skill_raw

if TYPE_CHECKING:
    from skillos.identity.context import TenantContext


def build_portable_skill_md(name: str, *, tenant: TenantContext | None = None) -> dict:
    """Load skill and build portable SKILL.md with AgentSkills frontmatter."""
    raw = load_skill_raw(name, tenant=tenant)
    meta = raw["meta"]
    body = raw["body"]
    slug = meta.get("portable_slug") or tool_slug(name, body)
    description = meta.get("description") or build_description(name, body)
    portable_meta = {"name": slug, "description": description}
    portable_md = _compose(portable_meta, body)
    return {
        "display_name": name,
        "slug": slug,
        "description": description,
        "portable_md": portable_md,
        "meta": meta,
    }


def build_install_zip(name: str, *, tenant: TenantContext | None = None) -> tuple[bytes, str]:
    """Return (zip bytes, suggested filename)."""
    info = build_portable_skill_md(name, tenant=tenant)
    slug = info["slug"]
    readme = format_install_guide(info["display_name"], slug).strip()
    readme += (
        "\n\n## 目录结构\n"
        f"解压后将 `{slug}/` 文件夹复制到对应工具的 skills 目录，"
        f"或只复制其中的 SKILL.md。\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/SKILL.md", info["portable_md"])
        zf.writestr("README.txt", readme)
        zf.writestr(
            "INSTALL.txt",
            "Cursor:     ~/.cursor/skills/{slug}/SKILL.md\n"
            "Claude:     ~/.claude/skills/{slug}/SKILL.md\n"
            "Trae:       ~/.trae/skills/{slug}/SKILL.md\n".format(slug=slug),
        )
    return buf.getvalue(), f"{slug}-skill.zip"
