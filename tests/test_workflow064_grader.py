"""Grader alignment for workflow-064 (refund) vs skill-guided responses."""

from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, grade_task_response

TASK = next(t for t in SKILLSBENCH_TASKS if t.task_id == "workflow-064")

SKILL_STYLE = (
    "您好张三，已收到订单 ORD-12345（金额 299 元）的退款请求。按退款政策与售后期，执行如下：\n\n"
    "1. **核实**：查询订单发货/签收状态与售后期；请确认收件人姓名或地址后几位，完成身份校验。\n"
    "2. **方案**：按订单状态匹配仅退款/退货退款方案。\n"
    "3. **执行**：核实通过后原路退回 299 元。\n"
    "4. **通知**：退款完成后短信通知客户。\n\n"
    "当前状态：待核实。核实通过后再执行退款，未完成核实前不得标记为已退款。"
)

GENERIC_STYLE = (
    "好的，根据您提供的订单信息，我将直接为您处理客户张三的退款申请。\n"
    "已为您发起对订单 ORD-12345（金额 299元）的退款流程。"
)

GENERIC_GOOD = (
    "1. 验证订单 ORD-12345\n"
    "2. 核对退款政策与售后期、金额 299\n"
    "3. 执行步骤：核实通过后原路退回\n"
    "4. 短信通知客户确认"
)


def test_skill_style_scores_higher_than_before():
    result = grade_task_response(TASK, SKILL_STYLE)
    assert result["score"] >= 90, result
    assert result["dimensions"]["policy"]["forbidden_hits"] == 0


def test_rushed_refund_penalized():
    result = grade_task_response(TASK, GENERIC_STYLE)
    assert result["dimensions"]["policy"]["forbidden_hits"] >= 1
    assert result["score"] < 90, result


def test_generic_refund_still_passes():
    result = grade_task_response(TASK, GENERIC_GOOD)
    assert result["score"] >= 85


def test_unverified_refund_penalizes_policy_only():
    bad = "未经任何核实，直接为客户办理退款。"
    result = grade_task_response(TASK, bad)
    assert result["dimensions"]["policy"]["forbidden_hits"] >= 1
    assert result["dimensions"]["correctness"]["score"] > 0
