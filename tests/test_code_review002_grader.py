"""Grader alignment for code-review-002 (SQL) vs PR skill responses."""

from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, grade_task_response

TASK = next(t for t in SKILLSBENCH_TASKS if t.task_id == "code-review-002")

PR_SKILL_STYLE = (
    "## 审查结果：严重缺陷 — SQL 注入风险\n"
    "用户输入通过字符串拼接嵌入 SQL。\n"
    "修复建议：使用参数化查询（prepared statement）。"
)


def test_pr_skill_style_sql_review_scores_high():
    result = grade_task_response(TASK, PR_SKILL_STYLE)
    assert result["score"] >= 85, result
