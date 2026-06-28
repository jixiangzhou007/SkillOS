#!/usr/bin/env python3
"""Seed comprehensive test data for SkillOS — skills, knowledge, lineage, evolution.

Usage:
  python scripts/seed_test_data.py [--admin] [--count N]

Creates realistic test data across domains so all UI pages have content.
Run with --admin to also create admin-level data (teams, org configs).
"""

import argparse
import logging
import random
import time
import uuid

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
_log = logging.getLogger("seed")


# ── Skill definitions ─────────────────────────────────────────────

DOMAINS = {
    "engineering": {"label": "工程技术", "philosophical_dna": "reductionist"},
    "finance": {"label": "财务金融", "philosophical_dna": "first-principles"},
    "hr": {"label": "人力资源", "philosophical_dna": "empiricist"},
    "customer-service": {"label": "客户服务", "philosophical_dna": "pragmatist"},
    "operations": {"label": "运营管理", "philosophical_dna": "holist"},
    "legal": {"label": "法律合规", "philosophical_dna": "skeptical-rationalist"},
    "marketing": {"label": "市场营销", "philosophical_dna": "empiricist"},
    "data-science": {"label": "数据科学", "philosophical_dna": "scientific-method"},
}

SKILL_TEMPLATES = [
    {
        "name": "合同审核流程",
        "domain": "legal",
        "quality": "high",
        "desc": "采购合同从初审到出具意见的标准化审核流程",
        "trigger": "收到采购合同或协议草案需要法务审核时触发",
        "steps": [
            "收件登记：记录合同编号、对方主体、金额、提交人",
            "形式审查：检查合同完整性（页码、签章、附件）",
            "实质审查：审查关键条款（标的、价款、交付、验收、违约）",
            "风险标记：在问题条款旁标注风险等级（高/中/低）",
            "修订建议：逐条给出修改建议文本",
            "意见书出具：汇总形成法务审核意见书",
        ],
        "route_conditions": [
            ("存在高风险条款", "返回修改，重新审查"),
            ("仅有中低风险项", "附意见书通过"),
            ("无风险项", "直接通过"),
        ],
        "edge_cases": ["对方主体为境外公司", "合同金额超过授权范围", "涉及个人数据跨境传输"],
    },
    {
        "name": "员工入职办理",
        "domain": "hr",
        "quality": "high",
        "desc": "新员工从Offer到正式入职的全流程办理",
        "trigger": "新员工在约定入职日前3天触发",
        "steps": [
            "入职前准备：工位、电脑、权限申请",
            "入职材料核验：身份证、学历证书、离职证明",
            "合同签署：劳动合同、保密协议",
            "制度宣导：公司制度、信息安全培训",
            "IT 配置：邮箱、VPN、内部系统权限开通",
            "导师分配：指定入职导师，安排前两周工作计划",
        ],
        "route_conditions": [
            ("核心岗位", "增加背景调查环节"),
            ("涉密岗位", "增加保密协议签署 + 安全审查"),
            ("普通岗位", "标准流程"),
        ],
        "edge_cases": ["入职日遇法定节假日", "外籍员工工作许可办理", "远程入职场景"],
    },
    {
        "name": "API 接口设计规范",
        "domain": "engineering",
        "quality": "high",
        "desc": "RESTful API 接口设计标准与审查流程",
        "trigger": "新建 API 接口或修改现有接口时触发",
        "steps": [
            "需求分析：明确接口使用者、场景、数据量",
            "URL 设计：遵循 /resources/{id} 命名规范",
            "请求方法选择：GET/ POST/ PUT/ DELETE 语义正确",
            "参数设计：分页、排序、过滤统一格式",
            "响应设计：统一 envelope、错误码规范",
            "安全审查：认证、授权、频率限制、数据脱敏",
        ],
        "route_conditions": [
            ("对外 API", "增加签名认证 + API 文档发布"),
            ("内部 API", "仅需 Token 认证"),
            ("敏感数据接口", "增加审计日志 + 数据脱敏"),
        ],
        "edge_cases": ["批量操作超时处理", "并发请求幂等性", "大文件传输方案"],
    },
    {
        "name": "费用报销审批",
        "domain": "finance",
        "quality": "high",
        "desc": "员工费用报销从提交到到账的完整审批链路",
        "trigger": "员工提交报销单后触发",
        "steps": [
            "提交审核：发票真实性、合规性、预算内",
            "部门审批：业务必要性确认",
            "财务审核：发票合规、税务合规、科目正确",
            "CFO 审批：超预算或超权限报销",
            "出纳支付：安排付款并通知员工",
        ],
        "route_conditions": [
            ("金额 < 5000", "部门审批 → 财务审核 → 支付"),
            ("5000 ≤ 金额 < 50000", "增加 CFO 审批"),
            ("金额 ≥ 50000", "增加总经理审批"),
        ],
        "edge_cases": ["发票丢失处理", "跨年报销", "外币报销汇率"],
    },
    {
        "name": "故障应急响应",
        "domain": "engineering",
        "quality": "high",
        "desc": "线上故障从发现到恢复的应急处理流程",
        "trigger": "监控告警或用户报障触发 P0/P1 事件",
        "steps": [
            "告警确认：判断真实故障还是误报",
            "事件定级：P0(核心业务中断) / P1(功能受损) / P2(轻微影响)",
            "应急响应：召集 on-call 工程师建立通讯群",
            "故障定位：查看日志、指标、链路追踪",
            "止损恢复：回滚、降级、限流、切流",
            "复盘改进：5Why 根因分析、改进项跟进",
        ],
        "route_conditions": [
            ("P0 故障", "5分钟响应 → 15分钟定位 → 30分钟止损"),
            ("P1 故障", "15分钟响应 → 1小时恢复"),
            ("P2 故障", "24小时内修复"),
        ],
        "edge_cases": ["on-call 人员联系不上", "故障跨多个团队", "依赖第三方服务故障"],
    },
    {
        "name": "客户投诉处理",
        "domain": "customer-service",
        "quality": "medium",
        "desc": "客户投诉从受理到闭环的标准流程",
        "trigger": "客户通过电话/在线/邮件发起投诉",
        "steps": [
            "投诉受理：记录客户信息、投诉内容、期望诉求",
            "分类定级：紧急程度（1-3级）、问题类型",
            "调查核实：对接相关部门了解情况",
            "方案制定：给出解决方案或补偿方案",
            "客户沟通：回复客户方案并达成一致",
            "闭环归档：记录处理结果，分析根因",
        ],
        "route_conditions": [
            ("1级(紧急)", "2小时内首次回复，24小时闭环"),
            ("2级(普通)", "8小时内回复，3日闭环"),
            ("3级(一般)", "24小时内回复，5日闭环"),
        ],
        "edge_cases": ["客户要求不合理补偿", "重复投诉", "投诉内容涉法务"],
    },
    {
        "name": "SEO 内容优化",
        "domain": "marketing",
        "quality": "medium",
        "desc": "网站内容 SEO 优化标准流程",
        "trigger": "新页面发布或现有页面流量下滑时触发",
        "steps": [
            "关键词研究：挖掘高潜力长尾关键词",
            "竞品分析：分析排名靠前页面的内容结构",
            "内容优化：标题、描述、H标签、内链",
            "技术检查：加载速度、移动适配、结构化数据",
            "效果监控：排名、流量、CTR 跟踪",
        ],
        "route_conditions": [
            ("新页面", "标准优化流程"),
            ("老页面改版", "保留 URL、301 重定向、更新 sitemap"),
        ],
        "edge_cases": ["关键词搜索意图不明", "行业季节性波动"],
    },
    {
        "name": "A/B 实验设计",
        "domain": "data-science",
        "quality": "high",
        "desc": "数据驱动的 A/B 实验从设计到分析的完整流程",
        "trigger": "产品/运营同学提出改动需求并需要数据验证时触发",
        "steps": [
            "实验假设：明确改动点和预期效果指标",
            "指标定义：主指标、辅助指标、守护指标",
            "分流设计：样本量计算、分流比例、分流单元",
            "实验实施：埋点检查、流量分配、灰度和全量",
            "数据收集：运行时长、样本量达标确认",
            "统计分析：显著性检验、效应量、MDE 确认",
        ],
        "route_conditions": [
            ("高风险改动", "增加 AA 测试 + 延长观察期"),
            ("低风险 UI 改动", "标准 7 天实验"),
        ],
        "edge_cases": ["节假日影响", "样本量不足", "实验交叉干扰"],
    },
    {
        "name": "需求评审规范",
        "domain": "operations",
        "quality": "low",
        "desc": "产品需求从提出到评审通过的基本流程",
        "steps": [
            "需求收集",
            "PRD 撰写",
            "需求评审",
            "技术评审",
            "排期开发",
        ],
        "route_conditions": [],
        "edge_cases": [],
    },
    {
        "name": "数据报表自动生成",
        "domain": "data-science",
        "quality": "low",
        "desc": "日报/周报/月报的自动化生成与分发流程",
        "steps": [
            "确定报表模板",
            "数据源配置",
            "报表生成",
            "审核确认",
            "自动分发",
        ],
        "route_conditions": [],
        "edge_cases": ["数据源连接失败"],
    },
]


def _make_skill_md(name: str, domain: str, template: dict, quality: str) -> str:
    """Generate a SKILL.md string from template."""
    domain_info = DOMAINS.get(domain, {"label": "通用", "philosophical_dna": "pragmatist"})
    now = time.time()
    slug = name.lower().replace(" ", "-").replace("/", "-")

    # Frontmatter
    lines = ["---"]
    lines.append(f"name: {name}")
    lines.append(
        f"created_at: '{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now - 86400 * random.randint(1, 30)))}'"
    )
    lines.append(f"updated_at: '{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}'")
    lines.append(f"domain: {domain}")
    lines.append(f"domain_label: {domain_info['label']}")
    lines.append(f"philosophical_dna: {domain_info['philosophical_dna']}")
    lines.append(f"description: {template['desc']}")
    lines.append(f"portable_slug: {slug}")
    lines.append("draft: false")

    # Quality-dependent metadata
    if quality == "high":
        total_claims = random.randint(20, 50)
        verified = random.randint(int(total_claims * 0.6), total_claims - 2)
        pending = total_claims - verified
        claim_ids = [f"ec_{int(now)}_{uuid.uuid4().hex[:6]}" for _ in range(total_claims)]
        lines.append("\nepistemic:")
        lines.append(f"  total_claims: {total_claims}")
        lines.append(f"  verified: {verified}")
        lines.append(f"  pending: {pending}")
        lines.append("  preferences: 0")
        lines.append("  errors: 0")
        lines.append("  claim_ids:")
        for cid in claim_ids[:10]:
            lines.append(f"  - {cid}")

        # DNA lineage
        lines.append("\ndna_lineage:")
        lines.append("  philosophical:")
        lines.append(f"  - id: {domain_info['philosophical_dna']}")
        lines.append(f"    weight: {round(random.uniform(0.3, 0.6), 2)}")
        lines.append("  domain:")
        lines.append(f"  - id: {slug}")
        lines.append("    version: 1.0.0")
        lines.append("    weight: 0.7")
        lines.append("    primary: true")
        lines.append(f"  detected_at: '{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}'")

        # Version
        lines.append(f"\nversion: {random.randint(1, 5)}")
    elif quality == "medium":
        total_claims = random.randint(5, 15)
        verified = random.randint(1, total_claims - 1)
        pending = total_claims - verified
        lines.append("\nepistemic:")
        lines.append(f"  total_claims: {total_claims}")
        lines.append(f"  verified: {verified}")
        lines.append(f"  pending: {pending}")
        lines.append(f"\nversion: {random.randint(1, 3)}")
    else:  # low
        lines.append("\nversion: 1")

    lines.append("---\n")

    # Body
    lines.append(f"# {name}")
    lines.append("## trigger")
    lines.append(template.get("trigger", template["desc"]))
    lines.append("")
    lines.append("## S_body")
    for i, step in enumerate(template["steps"], 1):
        lines.append(f"{i}. {step}")

    if template.get("route_conditions"):
        lines.append("")
        lines.append("## S_route")
        for cond, action in template["route_conditions"]:
            lines.append(f"| {cond} | {action} |")

    if template.get("edge_cases"):
        lines.append("")
        lines.append("## Edge Cases")
        for ec in template["edge_cases"]:
            lines.append(f"- {ec}")

    return "\n".join(lines)


def seed_skills(skill_store, count: int = None):
    """Create test skills."""
    templates = SKILL_TEMPLATES[:count] if count else SKILL_TEMPLATES
    created = []
    for tmpl in templates:
        content = _make_skill_md(tmpl["name"], tmpl["domain"], tmpl, tmpl["quality"])
        try:
            skill_store.save_skill(tmpl["name"], content, epistemic=False)
            _log.info("  ✅ %s (domain=%s, quality=%s)", tmpl["name"], tmpl["domain"], tmpl["quality"])
            created.append(tmpl["name"])
        except Exception as e:
            _log.error("  ❌ %s: %s", tmpl["name"], e)
    return created


def seed_knowledge_items(knowledge_store, skill_names: list[str]):
    """Create knowledge items linked to skills."""
    from skillos.knowledge.knowledge_store import KnowledgeStore

    store = KnowledgeStore()
    for skill_name in skill_names:
        for i in range(random.randint(2, 5)):
            item = {
                "id": f"test_ki_{uuid.uuid4().hex[:8]}",
                "content": f"从 {skill_name} 萃取的知识要点 {i + 1}："
                f"{random.choice(['最佳实践是', '关键在于', '需要注意', '核心原则是', '标准流程为'])}"
                f"{random.choice(['提前验证', '数据驱动决策', '保持沟通透明', '建立反馈机制', '持续迭代优化'])}",
                "category": random.choice(["fact", "concept", "heuristic", "pattern"]),
                "confidence": round(random.uniform(0.3, 0.99), 2),
                "skill": skill_name,
                "source": "seed_script",
            }
            try:
                store.save_item(**item)
            except Exception:
                pass


def seed_lineage(lineage_module, skill_names: list[str]):
    """Create skill precipitation lineage events."""
    for skill_name in skill_names:
        try:
            lineage_module.record_skill_precipitation(
                skill_name,
                session_id=f"seed:session:{uuid.uuid4().hex[:8]}",
                channel="seed",
                chat_id="seed_chat",
                user_id="admin",
                source="seed_script",
            )
        except Exception as e:
            _log.debug("Lineage record skipped: %s", e)


def seed_admin_data():
    """Create org/team config data for admin UI pages."""
    from skillos.identity.models import create_org

    try:
        org = create_org("TestOrg", owner="admin")
        _log.info("  ✅ Org created: %s", org)
    except Exception as e:
        _log.info("  ℹ️  Org creation skipped (likely exists): %s", e)


def main():
    parser = argparse.ArgumentParser(description="Seed test data for SkillOS")
    parser.add_argument("--admin", action="store_true", help="Also create admin/org data")
    parser.add_argument("--count", type=int, default=None, help="Number of skills (default: all)")
    args = parser.parse_args()

    _log.info("=== Seeding test data ===")

    # 1. Skills
    _log.info("\n📦 Creating skills...")
    from skillos.skills import skill_store

    skills = seed_skills(skill_store, count=args.count)

    if not skills:
        _log.warning("No skills created — check if they already exist or error above")
        return

    # 2. Knowledge items
    _log.info("\n🧠 Creating knowledge items...")
    try:
        seed_knowledge_items(None, skills)
    except Exception as e:
        _log.info("  ℹ️  Knowledge store not available: %s", e)

    # 3. Lineage
    _log.info("\n🔗 Creating lineage events...")
    try:
        from skillos.knowledge import lineage

        seed_lineage(lineage, skills)
    except Exception as e:
        _log.info("  ℹ️  Lineage record skipped: %s", e)

    # 4. Admin data
    if args.admin:
        _log.info("\n🏢 Creating admin data...")
        seed_admin_data()

    _log.info("\n🎉 Done! Created %d skills with supporting data.", len(skills))
    _log.info("   Refresh the UI or restart the server to see new data.")
    _log.info("   Skills: %s", "、".join(skills))


if __name__ == "__main__":
    main()
