"""Seed local SkillHub catalog from workspace cohort skills (local productization)."""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger("skillos.marketplace.seed")

# Reference + generalize cohort — enough for a non-empty local Hub
_DEFAULT_COHORT = (
    "GitHub Pull",
    "CSV数据清洗助手",
    "电商客服退款处理",
    "财务报销审计助手",
    "合同法务审核助手",
    "安全合规审计助手",
)


def _skills_root() -> Path:
    return Path(__file__).resolve().parents[2] / "skills"


def seed_hub_from_local_skills(
    *,
    names: tuple[str, ...] | list[str] | None = None,
    force: bool = False,
) -> dict:
    """Publish cohort SKILL.md into skillhub.db as approved (score auto-gate).

    Skips when catalog already has approved skills unless ``force=True``.
    """
    from skillos.marketplace.registry import get_stats, list_skills, publish_skill, update_skill_score

    stats = get_stats()
    if not force and (stats.get("total") or 0) > 0:
        return {"seeded": 0, "skipped": "catalog_not_empty", "total": stats.get("total", 0)}

    existing = {s.name for s in list_skills(status="approved")}
    existing |= {s.name for s in list_skills(status="pending")}
    root = _skills_root()
    cohort = list(names or _DEFAULT_COHORT)
    seeded: list[str] = []
    for name in cohort:
        if name in existing:
            continue
        path = root / name / "SKILL.md"
        if not path.is_file():
            _log.debug("seed skip missing %s", path)
            continue
        content = path.read_text(encoding="utf-8")
        desc = ""
        try:
            from skillos.skills.skill_store import _split_front_matter

            meta, _ = _split_front_matter(content)
            desc = str(meta.get("description") or "")[:200]
        except Exception as exc:
            _log.debug("seed frontmatter skip %s: %s", name, exc)
        skill = publish_skill(
            name,
            content,
            author="skillos-local",
            description=desc or f"Local cohort · {name}",
            category="automation",
            tags=["local-seed", "cohort"],
        )
        # Force approved without LLM scoring (local product catalog)
        update_skill_score(skill.skill_id, execution_score=85.0, audit_score=85.0, audit_json="{}")
        seeded.append(name)
        existing.add(name)

    _log.info("SkillHub local seed: %d skills", len(seeded))
    return {"seeded": len(seeded), "names": seeded, "total": get_stats().get("total", 0)}
