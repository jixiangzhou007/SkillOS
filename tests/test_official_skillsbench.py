"""Tests for official SkillsBench export helpers."""
from pathlib import Path

from skillos.official_skillsbench.export import export_skill_for_official
from skillos.official_skillsbench.tasks import suggest_tasks_for_skill


def test_export_csv_skill(tmp_path: Path):
    root = Path(__file__).resolve().parents[1] / "skills"
    if not (root / "CSV数据清洗助手" / "SKILL.md").exists():
        return
    out = export_skill_for_official("CSV数据清洗助手", tmp_path, skills_root=root)
    md = (out / "SKILL.md").read_text(encoding="utf-8")
    assert md.startswith("---")
    assert "name:" in md
    assert "description:" in md
    assert "Instructions" in md or "When to use" in md


def test_suggest_tasks():
    tasks = suggest_tasks_for_skill("CSV数据清洗助手")
    assert "sales-pivot-analysis" in tasks
