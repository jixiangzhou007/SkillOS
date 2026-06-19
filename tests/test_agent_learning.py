"""Unit tests for agent_learning.py — URL pipeline + claim extraction (no LLM)."""

import pytest
from skillos.skills.agent_learning import _extract_claims_from_skill as extract_claims_from_skill


SAMPLE_SKILL = """# 技能名称：退款处理
## 核心问题
处理客户退款申请

## S_body
1. 第一步：核对订单号和实付金额
2. 如果已发货：要求买家先退货再退款；如果未发货：可直接退款
3. 联系仓库确认退货入库后通知财务

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 仅退款未发货 | 直接退款 | 需订单状态确认 |
| 退货退款已发货 | 先退货后退款 | 需物流单号 |
| 退款金额>500 | 升级主管审批 | 风控规则 |

## S_trigger
- keywords: 退款, 退货, 退款申请
"""


class TestExtractClaims:
    def test_extracts_s_body_steps(self):
        claims = extract_claims_from_skill(SAMPLE_SKILL)
        body_claims = [c for c in claims if not c.startswith("触发条件") and "|" not in c]
        assert len(body_claims) == 3, f"Expected 3 S_body claims, got {len(body_claims)}"

    def test_extracts_s_route_rows(self):
        claims = extract_claims_from_skill(SAMPLE_SKILL)
        route_claims = [c for c in claims if "|" in c]
        assert len(route_claims) == 3, f"Expected 3 S_route claims, got {len(route_claims)}"

    def test_extracts_s_trigger(self):
        claims = extract_claims_from_skill(SAMPLE_SKILL)
        trigger_claims = [c for c in claims if c.startswith("触发条件")]
        assert len(trigger_claims) == 1, f"Expected 1 trigger claim, got {len(trigger_claims)}"
        assert "退款" in trigger_claims[0]

    def test_total_claims_count(self):
        claims = extract_claims_from_skill(SAMPLE_SKILL)
        assert len(claims) == 7, f"Expected 7 total claims (3 body + 3 route + 1 trigger), got {len(claims)}"

    def test_empty_skill_returns_empty(self):
        claims = extract_claims_from_skill("# 空技能\n## 核心问题\n无")
        assert claims == []

    def test_skill_without_s_body(self):
        claims = extract_claims_from_skill("# 技能\n## S_trigger\n- keywords: test")
        assert len(claims) == 1  # only trigger

    def test_filters_table_header_row(self):
        claims = extract_claims_from_skill(SAMPLE_SKILL)
        # Header row "用户意图/条件 | 执行动作 | 备注" should NOT appear
        for c in claims:
            assert "用户意图" not in c, f"Header row leaked into claims: {c}"


class TestExtractClaimsEdgeCases:
    def test_steps_with_number_prefix_are_cleaned(self):
        claims = extract_claims_from_skill("""# 技能
## S_body
1. 第一步：验证用户身份
2. 第二步：检查订单状态
""")
        for c in claims:
            assert not c.startswith("1."), f"Number prefix not stripped: {c}"
            assert not c.startswith("2."), f"Number prefix not stripped: {c}"

    def test_steps_shorter_than_12_chars_filtered(self):
        claims = extract_claims_from_skill("""# 技能
## S_body
1. 短
2. 这个步骤足够长所以会被提取
""")
        assert len(claims) == 1
