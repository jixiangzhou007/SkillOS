"""Phase 4 — DNA evolution, semver bumps, stale lineage queue."""


import pytest


@pytest.fixture
def dna_dirs(tmp_path, monkeypatch):
    stats = tmp_path / "philosophical_stats.json"
    templates = tmp_path / "domain_templates"
    templates.mkdir(parents=True)
    queue = tmp_path / "stale_queue.json"
    monkeypatch.setattr("skillos.knowledge.dna_store.PHILOSOPHICAL_STATS_PATH", stats)
    monkeypatch.setattr("skillos.knowledge.dna_store.DOMAIN_TEMPLATES_DIR", templates)
    monkeypatch.setattr("skillos.knowledge.dna_store.DNA_DIR", tmp_path)
    monkeypatch.setattr("skillos.knowledge.dna_evolution.DNA_DIR", tmp_path)
    monkeypatch.setattr("skillos.knowledge.dna_evolution.STALE_QUEUE_PATH", queue)
    return tmp_path


class TestSemver:
    def test_bump_patch_and_minor(self):
        from skillos.knowledge.dna_semver import bump_semver, compare_semver, is_stale_version

        assert bump_semver("1.0.0", "patch") == "1.0.1"
        assert bump_semver("1.0.0", "minor") == "1.1.0"
        assert compare_semver("1.0.0", "1.1.0") == -1
        assert is_stale_version("1.0.0", "1.1.0") is True
        assert is_stale_version("1.1.0", "1.1.0") is False


class TestDomainEvolution:
    def test_evolve_bumps_version_and_overlay(self, dna_dirs):
        from skillos.knowledge.dna_evolution import evolve_domain_template_record, get_template_generation_boost
        from skillos.knowledge.dna_store import get_template_version
        from skillos.skills.domain_templates import get_template

        content = """# Refund Skill

## Instructions
1. 校验订单状态与支付渠道是否一致
2. 识别退款类型并计算可退金额上限
3. 超阈值订单路由至人工复核队列并记录 SLA
"""
        result = evolve_domain_template_record(
            "workflow-refund", "test-refund", content, skill_score=86,
        )
        assert result["evolved"] is True
        assert result["to_version"] == "1.1.0"
        assert get_template_version("workflow-refund") == "1.1.0"

        tmpl = get_template("workflow-refund")
        boost = get_template_generation_boost("workflow-refund", tmpl.skeleton)
        assert "进化补充" in boost
        assert "人工复核" in boost

    def test_low_score_no_evolve(self, dna_dirs):
        from skillos.knowledge.dna_evolution import evolve_domain_template_record

        result = evolve_domain_template_record(
            "workflow-refund", "x", "1. step one\n", skill_score=60,
        )
        assert result["evolved"] is False

    def test_duplicate_steps_no_bump(self, dna_dirs):
        from skillos.knowledge.dna_evolution import evolve_domain_template_record
        from skillos.knowledge.dna_store import get_template_version

        content = """## Instructions
1. 校验订单状态与支付渠道是否一致
2. 识别退款类型并计算可退金额上限
"""
        evolve_domain_template_record("workflow-refund", "a", content, 80)
        v1 = get_template_version("workflow-refund")
        result = evolve_domain_template_record("workflow-refund", "b", content, 80)
        assert result["evolved"] is False
        assert get_template_version("workflow-refund") == v1


class TestStaleQueue:
    def test_detect_and_relink(self, dna_dirs, tmp_path, monkeypatch):
        from skillos.knowledge.dna_evolution import (
            evolve_domain_template_record,
            refresh_stale_queue,
            relink_skill_lineage,
            scan_stale_lineage_skills,
        )

        skills = tmp_path / "skills"
        skill_dir = skills / "测试技能"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: 测试技能
dna_lineage:
  domain:
  - id: workflow-refund
    version: 1.0.0
    primary: true
---
# 测试

## Instructions
1. 校验订单状态与支付渠道是否一致
2. 识别退款类型并计算可退金额上限
3. 新增步骤用于触发进化 semver minor bump
""",
            encoding="utf-8",
        )
        monkeypatch.setattr("skillos.skills.skill_store.get_skills_dir", lambda: skills)

        evolve_domain_template_record(
            "workflow-refund", "测试技能", skill_md.read_text(encoding="utf-8"), 88,
        )
        stale = scan_stale_lineage_skills(skills)
        assert any(s["skill"] == "测试技能" for s in stale)

        row = relink_skill_lineage(skill_md)
        assert row["changed"] is True
        assert row["still_stale"] is False

        queue = refresh_stale_queue(skills)
        assert not any(i["skill"] == "测试技能" for i in queue.get("items", []))
