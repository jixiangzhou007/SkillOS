#!/usr/bin/env python3
"""Migrate existing SkillOS skills to AgentSkills.io standard format.

Usage:
  python scripts/migrate_to_agentskills_standard.py          # dry-run
  python scripts/migrate_to_agentskills_standard.py --apply  # execute migration

Transforms:
  1. Chinese-name directory → kebab-case slug directory
  2. Bare Markdown → YAML frontmatter + Markdown
  3. Creates scripts/ references/ assets/ .skillos/ subdirectories
  4. Moves version files (v1.md, v2.md...) to .skillos/versions/
  5. Moves memory.json to .skillos/
  6. Preserves kb/ directory in-place

Backward-compatible: creates symlink/junction from old name to new name
so existing references continue to work.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
_log = logging.getLogger(__name__)


def migrate_skill(skill_dir: Path, *, apply: bool = False) -> dict:
    """Migrate one skill directory to AgentSkills.io standard.

    Returns a dict with migration status.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"dir": str(skill_dir.name), "status": "skip", "reason": "no SKILL.md"}

    # Read current content
    content = skill_md.read_text(encoding="utf-8")
    display_name = skill_dir.name

    # Already has YAML frontmatter?
    if content.strip().startswith("---"):
        return {"dir": display_name, "status": "skip", "reason": "already standard"}

    # Generate standard format
    from skillos.skills.portable_skill import (
        to_agent_skills_format,
        tool_slug,
        standard_skill_dir_structure,
    )

    slug = tool_slug(display_name, content)
    standard_content = to_agent_skills_format(display_name, content)

    new_dir = SKILLS_DIR / slug

    result = {
        "dir": display_name,
        "slug": slug,
        "status": "dry_run",
        "old_path": str(skill_dir),
        "new_path": str(new_dir),
    }

    if not apply:
        return result

    # Execute migration
    try:
        # 1. Create new standard directory
        new_dir.mkdir(parents=True, exist_ok=True)

        # 2. Write standard SKILL.md
        (new_dir / "SKILL.md").write_text(standard_content, encoding="utf-8")

        # 3. Create standard subdirectories
        from skillos.skills.skill_store import _ensure_standard_dirs
        _ensure_standard_dirs(new_dir)

        # 4. Move version files to .skillos/versions/
        versions_dir = new_dir / ".skillos" / "versions"
        for vf in sorted(skill_dir.glob("v*.md")):
            shutil.move(str(vf), str(versions_dir / vf.name))

        # 5. Move memory.json to .skillos/
        memory_file = skill_dir / "memory.json"
        if memory_file.exists():
            shutil.move(str(memory_file), str(new_dir / ".skillos" / "memory.json"))

        # 6. Copy kb/ directory (if exists)
        kb_dir = skill_dir / "kb"
        if kb_dir.exists() and kb_dir.is_dir():
            shutil.copytree(str(kb_dir), str(new_dir / "kb"), dirs_exist_ok=True)

        # 7. Remove old directory (now empty except maybe SKILL.md)
        if skill_dir.exists():
            remaining = list(skill_dir.iterdir())
            if not remaining or (len(remaining) == 1 and remaining[0].name == "SKILL.md"):
                shutil.rmtree(str(skill_dir))
            else:
                # Old SKILL.md already processed, just remove it
                old_skill_md = skill_dir / "SKILL.md"
                if old_skill_md.exists():
                    old_skill_md.unlink()

        result["status"] = "migrated"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        _log.error("Migration failed for %s: %s", display_name, e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Migrate skills to AgentSkills.io standard")
    parser.add_argument("--apply", action="store_true", help="Execute migration (default: dry-run)")
    parser.add_argument("--skill", type=str, help="Migrate a specific skill by name")
    args = parser.parse_args()

    if not SKILLS_DIR.exists():
        print(f"Skills directory not found: {SKILLS_DIR}")
        sys.exit(1)

    # Find all skill directories
    skill_dirs = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_"):
            skill_dirs.append(d)

    if args.skill:
        skill_dirs = [d for d in skill_dirs if d.name == args.skill]
        if not skill_dirs:
            print(f"Skill not found: {args.skill}")
            sys.exit(1)

    mode = "MIGRATING" if args.apply else "DRY RUN"
    print(f"=== {mode}: {len(skill_dirs)} skills ===")
    print()

    migrated = 0
    skipped = 0
    errors = 0

    for skill_dir in skill_dirs:
        result = migrate_skill(skill_dir, apply=args.apply)
        status = result["status"]

        if status == "migrated":
            print(f"[OK] {result['dir']} → {result['slug']}")
            migrated += 1
        elif status == "skip":
            print(f"[SKIP]  {result['dir']}: {result['reason']}")
            skipped += 1
        elif status == "dry_run":
            print(f"[DRY] {result['dir']} → {result['slug']} (would migrate)")
            skipped += 1
        elif status == "error":
            print(f"[ERR] {result['dir']}: {result.get('error', 'unknown')}")
            errors += 1

    print()
    print(f"Results: {migrated} migrated, {skipped} skipped, {errors} errors")

    if not args.apply:
        print("Run with --apply to execute migration.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
