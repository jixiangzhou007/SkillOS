"""Bench quality and post-extraction hooks."""

from skillos.skills.bench_quality import build_bench_quality_meta


def test_bench_quality_includes_moe_dimensions():
    moe = {
        "overall_score": 82,
        "passed": True,
        "confidence": 0.91,
        "dimensions": {"clarity": 85, "actionability": 80},
        "boost_rounds": [{"round": 1}],
    }
    out = build_bench_quality_meta(
        "测试技能",
        "## S_trigger\n- context: 测试时\n\n## S_body\n1. 执行操作检查验证步骤\n",
        moe=moe,
    )
    assert out["moe"]["overall_score"] == 82
    assert out["moe"]["confidence"] == 0.91
    assert "dimensions" in out["moe"]
    assert out["moe"]["boost_rounds"] == [{"round": 1}]


def test_pickle_task_scores_100_with_keywords():
    import os
    from pathlib import Path

    from skillos.skillsbench_tasks import run_task_evaluation

    os.environ["SKILLSBENCH_LLM_CACHE"] = "0"
    content = Path("skills/GitHub Pull/SKILL.md").read_text(encoding="utf-8")
    r = run_task_evaluation(
        "code-review-011",
        skill_content=content,
        model="",
        route_by_category=True,
        bench_categories=["code-review"],
        skill_name="GitHub Pull",
    )
    assert r.get("skill_used") is True
    assert r.get("score") == 100, r.get("dimensions")
