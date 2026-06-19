"""Universal skill extraction test suite.
Validates the extraction pipeline across 6 domains, multiple structures,
and edge cases — answering: "Can SkillOS extract skills from any domain?"
"""

import pytest
from skillos.skills.agent_learning import _extract_claims_from_skill
from skillos.skills.agent import SkillExtractionAgent


# ═══════════════════════════════════════════════════════════════
# Test Data: 6 domains × varied structures
# ═══════════════════════════════════════════════════════════════

DOMAIN_SKILLS = {
    "customer_service": {
        "domain": "客服退款",
        "content": """# 技能名称：电商退款处理
## 核心问题
处理客户退款申请，核实订单状态后执行退款或转人工

## S_body
1. 第一步：核对订单号、实付金额、付款渠道（支付宝/微信）
2. 在ERP中查询发货状态和物流签收时间
3. 如果已发货未签收：联系物流拦截；已签收：要求买家退货
4. 如果未发货：检查是否可取消订单
5. 退款金额>500元：升级主管审批，不自动退款
6. 确认退款后：原支付渠道退回，短信通知，同步ERP状态

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 仅退款+未发货 | 直接退款 | 需确认订单可取消 |
| 退货退款+已签收 | 先退货后退款 | 需物流单号+仓库确认 |
| 金额超500元 | 升级主管审批 | 风控规则 |

## S_trigger
- keywords: 退款, 退货, 退款申请, 我要退款
- context: 电商客服处理客户退款场景
- excludes: 换货、维修
""",
        "expected": {"min_body": 5, "min_route": 2, "has_trigger": True},
    },
    "legal_contract": {
        "domain": "合同审核",
        "content": """# 技能名称：销售合同审核
## 核心问题
审核销售合同中的关键条款，识别风险点并给出修改建议

## S_body
1. 第一步：检查合同主体信息（甲方乙方名称、统一社会信用代码、地址）
2. 核查金额条款：总金额、付款方式、付款节点是否明确
3. 核查交付条款：交付物清单、交付时间、验收标准
4. 核查违约责任条款：违约金比例是否合理（不超过合同总金额30%）
5. 核查争议解决条款：管辖法院是否对己方有利
6. 如发现格式条款（加重对方责任、免除己方义务）：特别标注风险
7. 汇总审核意见，标注每项风险等级（高/中/低）

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 违约金>30% | 建议修改为30%以下 | 民法典585条 |
| 管辖法院在对方所在地 | 建议修改为甲方所在地 | 减少诉讼成本 |
| 格式条款+单方免责 | 标注高风险，建议删除 | 民法典496条 |

## S_trigger
- keywords: 审合同, 合同审核, 审核合同, 看合同
- context: 收到销售合同需要法务审核
""",
        "expected": {"min_body": 6, "min_route": 2, "has_trigger": True},
    },
    "code_review": {
        "domain": "代码审查",
        "content": """# 技能名称：代码审查
## 核心问题
对Pull Request进行系统审查，检查正确性、安全性、性能和可维护性

## S_body
1. 阅读PR描述，理解变更动机和范围
2. 检查CI状态：所有测试必须通过，覆盖率不下降
3. 逐文件审查diff，关注：逻辑正确性、边界条件、错误处理
4. 安全审查：SQL注入、XSS、敏感信息硬编码、不安全的反序列化
5. 性能审查：N+1查询、不必要的循环、大对象加载
6. 如果发现阻塞性问题：标记"Request Changes"并说明原因
7. 如果只有建议性改进：标记"Approve"并列出建议

## S_route
| 条件 | 动作 |
|------|------|
| CI未通过 | Request Changes |
| 安全漏洞（SQL注入/XSS） | Request Changes + 紧急修复 |
| 仅代码风格问题 | Approve + 建议 |
| 新增代码无测试覆盖 | Request Changes |

## S_trigger
- keywords: review, PR, code review, 审查代码, 看代码
- context: 收到Pull Request需要代码审查
""",
        "expected": {"min_body": 6, "min_route": 3, "has_trigger": True},
    },
    "data_cleaning": {
        "domain": "数据清洗",
        "content": """# 技能名称：CSV数据清洗
## 核心问题
清洗运营从销售系统导出的CSV文件，去重、补全、统一格式

## S_body
1. 读取CSV文件，自动检测编码（UTF-8/GBK）
2. 按主键去重，保留最早一条记录
3. 检查email列格式，非法email导出到异常表
4. 金额列：去掉¥符号和千分位逗号，转为decimal
5. 日期列：统一为YYYY-MM-DD，无法解析的标注并导出
6. 空值处理：必填列（订单号、金额）为空时整行导出到异常表
7. 输出：清洗表 + 异常表 + 清洗报告（总行数、去重数、异常数、填充率）

## S_trigger
- keywords: 清洗数据, 处理CSV, 清洗表格, 去重
- context: 运营需要清洗导出的原始数据
""",
        "expected": {"min_body": 6, "min_route": 0, "has_trigger": True},
    },
    "finance_reimbursement": {
        "domain": "财务报销",
        "content": """# 技能名称：报销审批
## 核心问题
审核员工报销单，核验发票真伪、金额合规性和审批流程

## S_body
1. 检查报销单基本信息：员工姓名、部门、报销类型、总金额
2. 核验发票：通过税务接口查询发票真伪，核对发票金额、日期、抬头
3. 检查金额是否在员工级别限额内（普通员工2000/月，经理5000/月）
4. 如果金额超限：要求补充说明，提交上级审批
5. 检查报销类型与发票内容是否匹配（差旅费需附行程单）
6. 如果全部合规：审批通过，通知财务打款
7. 如果存在不合规项：退回并说明原因

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 金额≤限额+发票真实 | 自动通过 | |
| 金额>限额 | 提交上级审批 | 需补充说明 |
| 发票验证失败 | 退回+标记异常 | 疑似假发票 |
| 缺少必要附件 | 退回+提示补交 | |

## S_trigger
- keywords: 报销, 报销审批, 发票, 差旅费
- context: 员工提交报销单需要审批
""",
        "expected": {"min_body": 6, "min_route": 3, "has_trigger": True},
    },
    "content_compliance": {
        "domain": "内容合规",
        "content": """# 技能名称：营销内容合规审查
## 核心问题
审查营销内容是否违反广告法、涉及敏感词或虚假宣传

## S_body
1. 扫描全文，标记所有绝对化用语（"最好"、"第一"、"唯一"、"国家级"等违反广告法第9条）
2. 检查是否涉及医疗功效宣称（普通食品/化妆品不得宣称治疗效果）
3. 检查价格表述：原价必须有真实成交记录支撑，划线价需标明含义
4. 检查数据引用：统计数据必须注明来源和时间范围
5. 检查竞品提及：不得贬低竞争对手产品或服务
6. 输出审查报告：违规项列表 + 修改建议 + 合规替代文案

## S_route
| 条件 | 动作 |
|------|------|
| 含绝对化用语 | 建议替换为可验证描述 |
| 含医疗功效宣称 | 标注违规+建议删除 |
| 引用数据无来源 | 标注缺失+要求补充 |
| 贬低竞品 | 标注风险+建议删除 |

## S_trigger
- keywords: 合规审查, 广告审核, 检查内容, 审文案
- context: 营销团队提交内容需要合规审查
""",
        "expected": {"min_body": 5, "min_route": 3, "has_trigger": True},
    },
}

# Edge cases
EDGE_CASES = {
    "minimal_skill": {
        "content": "# 技能\n## S_body\n1. 第一步\n2. 第二步",
        "expected_claims": 0,  # steps too short (<12 chars), intentionally filtered
    },
    "empty_content": {
        "content": "",
        "expected_claims": 0,
    },
    "no_s_body": {
        "content": "# 技能\n## 核心问题\n测试\n## S_trigger\n- keywords: test",
        "expected_claims": 1,
    },
    "multi_line_steps": {
        "content": """## S_body
1. 第一步：这个步骤包含多行描述
   补充说明第一点
   补充说明第二点
2. 第二步：单个步骤
""",
        "expected_claims": 1,
    },
    "no_separator_route": {
        "content": """## S_route
| A | B | C |
|---|---|---|
| X | Y | Z |
""",
        "expected_claims": 2,  # generic header (A/B/C) not in filter keyword list → both rows extracted
    },
}


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════

class TestDomainUniversality:
    """Across 6 domains, extraction must produce meaningful claims."""

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_extracts_minimum_body_steps(self, key):
        case = DOMAIN_SKILLS[key]
        claims = _extract_claims_from_skill(case["content"])
        body_claims = [c for c in claims if not c.startswith("触发条件") and "|" not in c]
        assert len(body_claims) >= case["expected"]["min_body"], \
            f"{case['domain']}: expected >= {case['expected']['min_body']} body steps, got {len(body_claims)}"

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_extracts_minimum_route_rows(self, key):
        case = DOMAIN_SKILLS[key]
        claims = _extract_claims_from_skill(case["content"])
        route_claims = [c for c in claims if "|" in c]
        if case["expected"]["min_route"] > 0:
            assert len(route_claims) >= case["expected"]["min_route"], \
                f"{case['domain']}: expected >= {case['expected']['min_route']} route rows, got {len(route_claims)}"

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_extracts_trigger_when_present(self, key):
        case = DOMAIN_SKILLS[key]
        claims = _extract_claims_from_skill(case["content"])
        trigger_claims = [c for c in claims if c.startswith("触发条件")]
        if case["expected"]["has_trigger"]:
            assert len(trigger_claims) >= 1, \
                f"{case['domain']}: expected trigger claim, got none"

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_no_header_row_leakage(self, key):
        """Table header rows must never appear in claims."""
        case = DOMAIN_SKILLS[key]
        claims = _extract_claims_from_skill(case["content"])
        for c in claims:
            assert "用户意图" not in c, f"{case['domain']}: header leaked: {c[:50]}"
            assert "执行动作" not in c, f"{case['domain']}: header leaked: {c[:50]}"

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_no_html_or_markdown_artifacts(self, key):
        """Claims must be clean — no HTML tags or raw markdown artifacts."""
        case = DOMAIN_SKILLS[key]
        claims = _extract_claims_from_skill(case["content"])
        for c in claims:
            assert "<div" not in c, f"{case['domain']}: HTML in claim: {c[:50]}"
            assert "```" not in c, f"{case['domain']}: code block in claim: {c[:50]}"

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_claims_are_substantive(self, key):
        """Every claim must be at least 12 characters (not fragments)."""
        case = DOMAIN_SKILLS[key]
        claims = _extract_claims_from_skill(case["content"])
        for c in claims:
            assert len(c) >= 12, \
                f"{case['domain']}: claim too short ({len(c)} chars): '{c}'"


class TestEdgeCases:
    """Boundary conditions and malformed inputs."""

    @pytest.mark.parametrize("key", list(EDGE_CASES.keys()))
    def test_claim_count(self, key):
        case = EDGE_CASES[key]
        claims = _extract_claims_from_skill(case["content"])
        assert len(claims) == case["expected_claims"], \
            f"{key}: expected {case['expected_claims']}, got {len(claims)}"

    def test_all_filtered_when_all_steps_too_short(self):
        claims = _extract_claims_from_skill("## S_body\n1. a\n2. b\n3. c")
        assert claims == []

    def test_handles_content_with_only_frontmatter(self):
        claims = _extract_claims_from_skill("---\nname: test\ndescription: desc\n---\n# Skill")
        assert claims == []


class TestTopicExtraction:
    """Topic extraction must work across varied input phrasings."""

    TOPIC_CASES = [
        ("帮我创建一个处理客户投诉的技能", "处理客户投诉"),
        ("帮我沉淀一下电商客服处理退款的标准流程", "电商客服处理退款的标准"),
        ("创建一个合同审核的skill", "合同审核"),
        ("我想做一个代码审查的工作流", "代码审查"),
        ("帮我写一个数据分析报告的技能", "数据分析报告"),
        ("萃取一个财务报销审批流程", "财务报销审批"),
        ("帮我整理一套CSV数据清洗的操作指南", "CSV数据清洗"),  # strips "帮我整理一套" + "的操作指南"
        ("新建一个营销内容合规审查", "营销内容合规审查"),
        ("帮我创建技能", ""),  # Generic, no topic
        ("", ""),  # Empty
    ]

    @pytest.mark.parametrize("raw,expected", TOPIC_CASES)
    def test_topic_extraction(self, raw, expected):
        agent = SkillExtractionAgent()
        result = agent._extract_topic(raw)
        assert result == expected, f"input='{raw}': expected '{expected}', got '{result}'"


class TestStructuralCompleteness:
    """Skills must have all required sections for downstream tools."""

    REQUIRED_SECTIONS = ["S_body", "S_trigger"]

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_has_required_sections(self, key):
        content = DOMAIN_SKILLS[key]["content"]
        for section in self.REQUIRED_SECTIONS:
            assert f"## {section}" in content, \
                f"{key}: missing required section '{section}'"

    @pytest.mark.parametrize("key", list(DOMAIN_SKILLS.keys()))
    def test_s_route_has_minimum_rows(self, key):
        """S_route tables must have at least 2 data rows for adequate coverage."""
        content = DOMAIN_SKILLS[key]["content"]
        if "## S_route" in content:
            # Count non-header, non-separator table rows
            rows = [l for l in content.split("\n")
                    if l.strip().startswith("|") and "---" not in l
                    and not any(h in l for h in ["用户意图", "条件", "动作"])]
            assert len(rows) >= 2, \
                f"{key}: S_route has only {len(rows)} data rows (need >= 2)"


class TestClaimRoundTrip:
    """Claims extracted from a skill should capture its essential structure."""

    def test_generated_skill_produces_meaningful_claims(self):
        """End-to-end: a well-formed skill → claims capture all sections."""
        content = DOMAIN_SKILLS["customer_service"]["content"]
        claims = _extract_claims_from_skill(content)

        # Should get body + route + trigger
        assert len(claims) >= 8, f"Expected >= 8 claims, got {len(claims)}"

        # First body step should mention 订单号 (order ID)
        body_text = " ".join(c for c in claims if "|" not in c and not c.startswith("触发条件"))
        assert "订单号" in body_text, f"Missing key term '订单号' in body claims"

    def test_all_domains_have_unique_body_content(self):
        """Each domain's body claims should contain domain-specific terms."""
        domain_terms = {
            "customer_service": "退款",
            "legal_contract": "合同",
            "code_review": "PR" if False else "审查",  # "审查" appears in multiple
            "data_cleaning": "CSV",
            "finance_reimbursement": "发票",
            "content_compliance": "广告法",
        }
        for key, term in domain_terms.items():
            content = DOMAIN_SKILLS[key]["content"]
            claims = _extract_claims_from_skill(content)
            body_text = " ".join(claims)
            assert term in body_text, \
                f"{key}: domain term '{term}' not found in extracted claims"
