"""Full extraction pipeline integration test — topic → claims → quality → description.

Verifies the complete pipeline without LLM: topic extraction, claim extraction,
quality self-check, and description generation all work end-to-end.
"""

import pytest
from skillos.skills.agent import SkillExtractionAgent


class TestFullExtractionPipeline:
    """End-to-end: topic → generate → claims → quality check → description."""

    def test_topic_to_claims_pipeline(self):
        """A complete skill body should produce claims, pass quality, and generate description."""
        agent = SkillExtractionAgent()

        # Step 1: Topic extraction
        topic = agent._extract_topic("帮我创建一个合同审核的技能")
        assert topic == "合同审核"

        # Step 2: Simulate generated content
        content = """# 合同审核
## 核心问题
审核销售合同的关键条款，识别法律风险

## S_body
1. [动作] 检查合同主体信息（甲方乙方名称、信用代码、地址）
2. [门禁] 合同主体信息必须完整 → 不完整则中止，提示补充
3. [动作] 核查金额条款：总金额、付款方式、付款节点是否明确
4. [门禁] 违约金比例不得超过合同总金额30% → 超过则标注高风险
5. [动作] 核查争议解决条款：管辖法院是否对己方有利

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 违约金>30% | 建议修改 | 民法典585条 |
| 管辖法院在对方所在地 | 建议修改 | 减少诉讼成本 |

## S_trigger
- keywords: 审合同, 合同审核, 审核合同, contract review
- context: 收到销售合同需要法务审核
- excludes: 劳动合同、租赁合同
"""

        # Step 3: Claim extraction
        claims = agent._extract_claims_from_skill(content)
        assert len(claims) >= 5, f"Expected >=5 claims, got {len(claims)}"

        # Step 4: Quality check
        finalized = {
            "slug": "contract-review",
            "description": "Review sales contracts for key clauses and legal risks. Use when user mentions 审合同, 合同审核, contract review. Do NOT trigger for 劳动合同 or 租赁合同.",
        }
        issues = agent._post_generation_check("合同审核", content, finalized)
        assert len(issues) == 0, f"Expected 0 issues, got: {issues}"

        # Step 5: Description generation
        from skillos.skills.portable_skill import build_description
        desc = build_description("合同审核", content)
        assert len(desc) > 50
        assert "审合同" in desc or "contract" in desc.lower()

    def test_gate_steps_in_route(self):
        """Gate steps in S_body should be auto-added to S_route."""
        from skillos.skills.skill_structure import extract_gate_steps, ensure_gate_steps_in_route
        content = """## S_body
1. [动作] 核对订单
2. [门禁] 金额>500必须审批 → 中止
3. [动作] 执行退款
## S_route
| 条件 | 动作 |
|------|------|
| 已发货 | 退货退款 |
"""
        gates = extract_gate_steps(content)
        assert len(gates) == 1
        result = ensure_gate_steps_in_route(content)
        assert "[门禁]" in result

    def test_resource_classification_pipeline(self):
        """User messages should be correctly classified for resource capture."""
        from skillos.skills.resource_capture import classify_resource_type

        assert classify_resource_type("```python\nprint('hello')\n```") == "script"
        assert classify_resource_type("邮件模板如下：亲爱的客户您好，您的订单已处理") == "asset"
        assert classify_resource_type("https://example.com/policy.pdf 参考这个") == "reference"
        assert classify_resource_type("好的，继续") is None

    def test_metaskill_role_pipeline(self):
        """Full MetaSkill with 7 roles should parse and serialize correctly."""
        from skillos.skills.metaskill import parse_metaskill, ROLE_TEMPLATES

        content = """---
type: metaskill
name: full-pipeline
---
# MetaSkill: full-pipeline
## Goal
End-to-end process
## Pipeline
```pipeline
clarify: need-clarify  # role: business_analyst | accept: requirements clear | handoff_to: process_designer
design: process-design  # role: process_designer | depends_on: [clarify] | accept: >=3 steps
review: process-review  # role: reviewer | depends_on: [design]
test: qa-test  # role: qa_lead | depends_on: [review]
audit: security-audit  # role: security_auditor | depends_on: [test]
write: doc-write  # role: tech_writer | depends_on: [audit]
release: final-release  # role: release_manager | depends_on: [write] | accept: all gates passed
```
"""
        ms = parse_metaskill(content)
        assert ms is not None
        assert ms.role_count == 7
        assert ms.roles == ['business_analyst', 'process_designer', 'reviewer',
                           'qa_lead', 'security_auditor', 'tech_writer', 'release_manager']
        assert ms.steps[0].handoff_to == 'process_designer'
        assert ms.steps[-1].acceptance_criteria == 'all gates passed'

        markdown = ms.to_markdown()
        assert '## Roles' in markdown
        assert '## Acceptance Gates' in markdown
        for rid in ms.roles:
            assert rid in ROLE_TEMPLATES, f"Missing role template: {rid}"
