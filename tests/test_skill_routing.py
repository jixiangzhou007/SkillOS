"""Tests for SkillsBench category routing (P1)."""

from __future__ import annotations

from unittest.mock import patch

from skillos.knowledge.skill_routing import (
    build_skill_taxonomy_meta,
    infer_bench_categories,
    parse_bench_categories_from_skill,
    resolve_bench_categories,
    should_inject_skill,
    skill_body_from_file,
)
from skillos.skillsbench_tasks import compare_with_without, run_skillsbench_suite


class TestInferBenchCategories:
    def test_refund_skill_maps_workflow(self):
        cats = infer_bench_categories(
            "电商客服退款处理",
            "退款流程 工单 客服 审批 退货 SLA 处理步骤",
        )
        assert "workflow" in cats

    def test_csv_skill_maps_data_processing(self):
        cats = infer_bench_categories(
            "运营级CSV清洗工坊",
            "csv 数据清洗 去重 空值 excel pandas 表格",
        )
        assert "data-processing" in cats

    def test_pr_skill_maps_code_review(self):
        cats = infer_bench_categories(
            "GitHub PR",
            "pull request code review diff merge github sql注入",
        )
        assert "code-review" in cats

    def test_build_taxonomy_meta_includes_domain(self):
        meta = build_skill_taxonomy_meta(
            "GitHub PR 审查",
            "pull request code review github diff",
        )
        assert "bench_categories" in meta
        assert meta.get("domain") == "computer-science"
        assert "code-review" in meta["bench_categories"]


class TestShouldInjectSkill:
    def test_match(self):
        assert should_inject_skill(["workflow", "documentation"], "workflow") is True

    def test_no_match(self):
        assert should_inject_skill(["workflow"], "code-review") is False

    def test_empty_categories_never_inject(self):
        assert should_inject_skill([], "workflow") is False


class TestFrontmatterParsing:
    def test_parse_bench_categories_yaml(self):
        content = """---
name: test-skill
bench_categories:
  - code-review
  - api-design
---
# Body
"""
        assert parse_bench_categories_from_skill(content) == ["code-review", "api-design"]
        assert skill_body_from_file(content).startswith("# Body")

    def test_resolve_prefers_meta(self):
        cats = resolve_bench_categories(
            "x",
            "---\nbench_categories: [workflow]\n---\n",
            meta_categories=["code-review"],
        )
        assert cats == ["code-review"]


class TestRoutedSuite:
    def test_suite_routes_by_category(self):
        def fake_eval(task_id, **kwargs):
            return {
                "task_id": task_id,
                "score": 10 if kwargs.get("inject_skill") else 5,
                "max_score": 10,
                "grade": "A",
            }

        with patch("skillos.skillsbench_tasks.run_task_evaluation", side_effect=fake_eval):
            out = run_skillsbench_suite(
                skill_content="# skill",
                bench_categories=["workflow"],
                route_by_category=True,
            )
        matched = [r for r in out["results"] if r.get("category_matched") is True]
        skipped = [r for r in out["results"] if r.get("category_matched") is False]
        assert len(matched) >= 1
        assert len(skipped) >= 1


class TestInferTaskCategory:
    def test_code_review_message(self):
        from skillos.knowledge.skill_routing import infer_task_category
        assert infer_task_category("Review this pull request for SQL injection") == "code-review"

    def test_workflow_message(self):
        from skillos.knowledge.skill_routing import infer_task_category
        assert infer_task_category("处理客户退款工单审批流程") == "workflow"


class TestFilterSkills:
    def test_filters_mismatch(self):
        from skillos.knowledge.skill_routing import filter_skills_for_message
        skills = [
            {
                "name": "退款",
                "body": "退款流程",
                "meta": {"bench_categories": ["workflow"]},
            },
            {
                "name": "PR",
                "body": "code review github",
                "meta": {"bench_categories": ["code-review"]},
            },
        ]
        kept = filter_skills_for_message(skills, "Review pull request SQL injection diff")
        assert len(kept) == 1
        assert kept[0]["name"] == "PR"


class TestBackfillMeta:
    def test_backfill_writes_categories(self, tmp_path):
        from skillos.knowledge.skill_routing import backfill_skill_routing_meta
        md = tmp_path / "退款" / "SKILL.md"
        md.parent.mkdir()
        md.write_text(
            "---\nname: 退款处理\ndraft: false\n---\n# 退款 工单 审批\n",
            encoding="utf-8",
        )
        row = backfill_skill_routing_meta(md)
        assert row["changed"] is True
        assert "workflow" in row["bench_categories"]
        text = md.read_text(encoding="utf-8")
        assert "bench_categories:" in text


class TestCompareRouted:
    def test_compare_returns_matched_and_harm(self, tmp_path):
        skill_md = tmp_path / "refund" / "SKILL.md"
        skill_md.parent.mkdir()
        skill_md.write_text(
            """---
name: 退款处理
bench_categories:
  - workflow
---
# 退款流程
""",
            encoding="utf-8",
        )

        scores = {"workflow": (80, 60), "code-review": (40, 70)}

        def fake_eval(task_id, **kwargs):
            from skillos.skillsbench_tasks import SKILLSBENCH_TASKS
            task = next(t for t in SKILLSBENCH_TASKS if t.task_id == task_id)
            base, forced = scores.get(task.category, (50, 50))
            use = kwargs.get("skill_content") and kwargs.get("inject_skill", True)
            return {
                "task_id": task_id,
                "category": task.category,
                "score": forced if use else base,
                "max_score": 100,
                "grade": "B",
            }

        with patch("skillos.skillsbench_tasks.run_task_evaluation", side_effect=fake_eval):
            result = compare_with_without(str(skill_md), routed=True)

        assert result["routed"] is True
        assert result["bench_categories"] == ["workflow"]
        assert "matched_delta" in result
        assert "harm_score" in result
        assert isinstance(result["cross_domain"], list)
        assert result["matched_tasks"] >= 1
