"""Grader alignment for data-processing-036 vs CSV skill responses."""

from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, grade_task_response

TASK = next(t for t in SKILLSBENCH_TASKS if t.task_id == "data-processing-036")

SKILL_STYLE = (
    "好的，我将按 CSV 数据清洗流程处理。\n"
    "第一步：读取 CSV。\n"
    "第二步：去重，删除 id+name+email 完全重复的行。\n"
    "第三步：补空，对缺失 email 填空值或标记待补全。"
)

GENERIC_STYLE = (
    "去重：删除重复行。\n"
    "空值：email 字段 missing 用占位符填充。"
)


def test_skill_style_csv036():
    result = grade_task_response(TASK, SKILL_STYLE)
    assert result["score"] >= 85, result


def test_generic_csv036():
    result = grade_task_response(TASK, GENERIC_STYLE)
    assert result["score"] >= 85
