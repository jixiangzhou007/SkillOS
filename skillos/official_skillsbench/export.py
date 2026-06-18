"""Export SkillOS skills to official BenchFlow --skills-dir layout."""


import re
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "skill"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        import yaml

        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return meta, parts[2].lstrip("\n")


def export_skill_for_official(
    skill_name: str,
    dest_skills_dir: Path,
    *,
    skills_root: Path | None = None,
) -> Path:
    """Write ``dest_skills_dir/<slug>/SKILL.md`` in official BenchFlow format."""
    root = skills_root or SKILLS_ROOT
    src = root / skill_name / "SKILL.md"
    if not src.exists():
        raise FileNotFoundError(f"SKILL.md not found: {src}")

    raw = src.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    name = str(meta.get("name") or skill_name)
    description = str(meta.get("description") or "").strip()
    slug = str(meta.get("portable_slug") or _slugify(name))

    lines = [
        "---",
        f"name: {slug}",
        f"description: {description or name}",
        "allowed-tools: Read Write Edit Bash",
        "license: Proprietary",
        "metadata:",
        "  skillos-export: true",
        f"  skillos-source: {name}",
        "---",
        "",
        body.strip(),
        "",
    ]
    out_dir = dest_skills_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "SKILL.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_dir
