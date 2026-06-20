"""Domain Taxonomy & Methodology Detection for Skill Knowledge.

Two axes of classification:
  1. Domain/Discipline — what field of knowledge does this skill belong to?
  2. Methodology — what underlying thinking pattern drives this process?

Why this matters:
  - Domain-aware retrieval: search by field, not just keyword match
  - Cross-domain analogy: "code review" (CS) and "peer review" (Publishing) share
    the same methodology (diagnostic evaluation), enabling knowledge transfer
  - Methodology-tuned extraction: a scientific process needs reproducibility checks;
    an engineering process needs testability; a business process needs measurability
"""


from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# Domain/Discipline Taxonomy
# ═══════════════════════════════════════════════════════════════

@dataclass
class Domain:
    key: str
    name: str                # Chinese name
    name_en: str             # English name
    keywords: tuple[str, ...]
    evidence_standard: str   # What counts as "proof" in this domain?
    methodology_hint: str    # How do practitioners in this field typically think?


DOMAINS: list[Domain] = [
    # ── 12 academic disciplines ──
    Domain("computer-science", "计算机科学", "Computer Science",
           ("编程", "代码", "API", "算法", "数据库", "AI", "机器学习", "服务器", "部署", "测试",
            "PR", "CI", "CD", "DevOps", "前端", "后端", "架构", "接口", "Git", "review",
            "bug", "需求", "上线", "发布", "监控", "回滚", "软件", "程序", "开发", "工程师",
            "审查", "代码审查", "code"),
           "ISO/IEC 25010 软件质量模型 + 自动化测试覆盖率 ≥80% + 代码审查通过率 100%",
           "工程思维：需求→设计→实现→测试→部署，重逻辑严密和边界覆盖"),
    Domain("medicine-health", "医学与健康", "Medicine & Health",
           ("诊断", "分诊", "治疗", "护理", "药物", "手术", "患者", "门诊", "急诊",
            "病历", "体检", "疫苗", "核酸", "传染病", "抢救", "医嘱", "处方", "临床", "症状"),
           "JCI 国际医院认证标准 + NICE 临床指南 + 随机对照试验 Meta 分析（证据等级 A-B）",
           "诊断思维：主诉→检查→鉴别→诊断→处置，重证据链和时效性"),
    Domain("management-science", "管理学", "Management Science",
           ("管理", "流程", "审批", "绩效", "招聘", "供应链", "预算", "OKR", "KPI",
            "入职", "培训", "述职", "报销", "采购", "排期", "资源分配", "组织架构"),
           "ISO 9001 质量管理体系 + 流程周期时间缩短 ≥20% + SLA 达成率 ≥95%",
           "管理思维：流程→标准→执行→检查→优化，重可复制性和风险控制"),
    Domain("law", "法学", "Law",
           ("法律", "合规", "合同", "条款", "知识产权", "版权", "专利", "GDPR", "隐私",
            "法务", "仲裁", "诉讼", "证据", "判例", "审查", "审核", "法条", "法规"),
           "民法典 + 公司法 + 具体法条引用（含条款号） + 判例号（如有） + ISO 37301 合规管理体系",
           "法律思维：法条→事实→分析→结论，重逻辑严密和证据链完整"),
    Domain("economics-finance", "经济学与金融", "Economics & Finance",
           ("财务", "会计", "审计", "税务", "发票", "对账", "结算", "成本", "预算",
            "报表", "资金", "付款", "收款", "投资", "理财", "保险", "风控", "授信",
            "报销", "差旅", "费用", "凭证"),
           "IFRS/IAS 国际会计准则 + CPA 审计标准 + 税务合规（增值税/所得税） + 金额精确到分 + 独立审计意见",
           "审计思维：规则→核对→差异→调整→确认，重精确性和合规性"),
    Domain("education", "教育学", "Education",
           ("教学", "课程", "课堂", "学习", "考试", "评估", "教材", "讲义", "作业",
            "培训", "实训", "知识点", "MOOC", "教学法", "翻转课堂", "课程设计"),
           "Bloom 教学目标分类学 + Kirkpatrick 四级评估模型 + 学习前后测效应量 Cohen's d ≥ 0.4",
           "教学思维：目标→内容→方法→评估→反馈，重认知规律和循序渐进"),
    Domain("design", "设计学", "Design",
           ("设计", "UI", "UX", "视觉", "品牌", "配色", "排版", "用户体验", "交互",
            "插画", "动画", "视频", "创意", "美感", "可用性"),
           "WCAG 2.1 AA 无障碍标准 + Nielsen 可用性启发式 + 用户测试完成率 ≥80% + SUS 评分 ≥68",
           "设计思维：共情→定义→构思→原型→测试，重用户视角和迭代"),
    Domain("engineering", "工程学", "Engineering",
           ("工程", "建造", "制造", "质量", "检测", "安全", "电气", "机械", "土木",
            "运维", "巡检", "维护", "排班", "调度", "仓储", "物流", "配送", "库存"),
           "ISO 9001 质量管理 + ISO 45001 职业健康安全 + 行业 AQL 抽样标准 + 缺陷率 ≤1% + 校准可溯源",
           "工程思维：需求→设计→施工→验收→运维，重规范性和安全性"),
    Domain("natural-science", "自然科学", "Natural Science",
           ("实验", "物理", "化学", "生物", "统计", "数据", "假设", "验证", "观测",
            "测量", "样本", "显著性", "p值", "对照", "变量", "科学方法", "实验设计",
            "科研", "研究设计"),
           "ISO 17025 实验室认证 + 统计功效 ≥0.8 + 效应量报告（非仅 p 值） + 独立重复实验验证",
           "科学思维：观察→假设→实验→分析→结论，重可复现性和证伪"),
    Domain("social-science", "社会科学", "Social Science",
           ("调研", "问卷", "访谈", "社会", "心理", "行为", "人口", "政策", "治理",
            "统计", "公共", "社区", "民政", "NGO"),
           "AAPOR 调研标准 + 抽样误差 ≤±3% + 信度 Cronbach's α ≥0.7 + 效度检验 + IRB 伦理审批",
           "实证思维：理论→假设→数据→分析→结论，重方法严谨性和可推广性"),
    Domain("journalism-communication", "新闻传播学", "Journalism & Communication",
           ("新闻", "写作", "编辑", "出版", "审核", "发布", "内容", "媒体", "传播",
            "校对", "审稿", "公众号", "文案", "广告", "公关"),
           "AP Stylebook + 独立事实核查（≥2源） + 更正时效 ≤24h + 来源透明度 + SPJ 伦理准则",
           "编辑思维：选题→采集→写作→编辑→审核→发布，重准确性和时效性"),
    Domain("agriculture", "农学", "Agriculture",
           ("农业", "种植", "养殖", "畜牧", "兽医", "检疫", "食品安全", "土壤",
            "灌溉", "施肥", "收割", "储藏", "转基因", "有机", "农药",
            "质检", "检测", "种子", "农产品", "品质", "田间", "种植管理",
            "农作物", "耕作", "栽培"),
           "GAP 良好农业规范 + 有机认证标准（USDA Organic/EU Organic） + GlobalG.A.P. 认证 + 土壤检测 GB 15618 + 农药残留限量 GB 2763",
           "农学思维：环境→品种→管理→收获→检验，重因地制宜和周期管理"),
]


def detect_domain(topic: str, content: str = "") -> Optional[Domain]:
    """Detect which domain a skill belongs to based on topic and content keywords.

    Returns the best-matching Domain, or None if no clear match.
    """
    text = (topic + " " + content[:500]).lower()
    best, best_score = None, 0.0
    for d in DOMAINS:
        score = sum(1.0 for kw in d.keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best = d
    return best if best_score >= 1 else None  # lowered from 2: short Chinese topics may only hit 1 keyword


def domain_classification_context(topic: str, content: str = "") -> str:
    """Build a context string describing the detected domain for prompt injection."""
    domain = detect_domain(topic, content)
    if not domain:
        return ""
    return (
        f"\n## 🏷️ 领域分类\n"
        f"检测到本技能属于 **{domain.name}**（{domain.name_en}）领域。\n"
        f"- 证据标准：{domain.evidence_standard}\n"
        f"- 典型思维方式：{domain.methodology_hint}\n"
        f"- 请在萃取时用该领域的专业术语和验证标准来指导提问。\n"
    )


# ═══════════════════════════════════════════════════════════════
# Methodology / Thinking Style Detection
# ═══════════════════════════════════════════════════════════════

@dataclass
class Methodology:
    key: str
    name: str
    pattern: str             # The step pattern that defines this methodology
    philosophical_root: str  # What philosophical tradition does this come from?
    extraction_guidance: str # How should the Socratic extraction adapt?
    cross_domain_examples: list[str] = field(default_factory=list)


METHODOLOGIES: list[Methodology] = [
    Methodology(
        key="engineering",
        name="工程方法论",
        pattern="需求→设计→实现→测试→部署",
        philosophical_root="笛卡尔还原论：将复杂问题分解为可管理的组件。Popper证伪主义：通过测试失败来证明正确性。",
        extraction_guidance="追问边界条件、异常路径、回滚方案。检查每个步骤是否有可验证的通过标准。",
        cross_domain_examples=["代码审查流程", "建筑质量检查", "汽车安全检测"],
    ),
    Methodology(
        key="scientific",
        name="科学方法论",
        pattern="观察→假设→实验→分析→结论",
        philosophical_root="培根经验主义 + Popper证伪主义。知识通过可复现的观察和证伪测试来推进。",
        extraction_guidance="追问假设前提、控制变量、可复现性。检查结论是否超越了数据支持的范围。",
        cross_domain_examples=["实验设计", "数据分析报告", "医学诊断"],
    ),
    Methodology(
        key="diagnostic",
        name="诊断方法论",
        pattern="观察→分类→诊断→处理→验证",
        philosophical_root="亚里士多德范畴论 + 医学诊断传统。通过症状分类来定位根因。",
        extraction_guidance="追问诊断决策树、误判代价、升级条件。检查每个分支是否有明确的判断标准。",
        cross_domain_examples=["客服投诉处理", "医疗诊断", "系统故障排查"],
    ),
    Methodology(
        key="design-thinking",
        name="设计思维",
        pattern="共情→定义→构思→原型→测试",
        philosophical_root="杜威实用主义 + Simon设计科学。通过迭代原型和用户反馈来逼近最优解。",
        extraction_guidance="追问用户视角、迭代节奏、失败标准。检查是否有定性的用户反馈循环。",
        cross_domain_examples=["UI设计流程", "产品规划", "课程设计"],
    ),
    Methodology(
        key="business-process",
        name="业务流程方法论",
        pattern="触发→验证→执行→确认→归档",
        philosophical_root="泰勒科学管理 + 戴明PDCA循环。通过标准化和持续改进来提升效率。",
        extraction_guidance="追问SLA时限、审批链、异常升级路径。检查每个步骤的责任人和时效要求。",
        cross_domain_examples=["退款处理", "员工入职", "采购审批"],
    ),
    Methodology(
        key="creative",
        name="创作方法论",
        pattern="灵感→探索→草稿→打磨→发布",
        philosophical_root="浪漫主义 + 刻意练习。创造性工作在自由探索和严格打磨之间交替。",
        extraction_guidance='追问灵感来源、迭代次数、质量标准。区分「必须做」和「可以做」的步骤。',
        cross_domain_examples=["写作流程", "视频制作", "音乐创作"],
    ),
]


def detect_methodology(topic: str, content: str = "") -> Optional[Methodology]:
    """Detect the underlying methodology/thinking pattern from the process description.

    Uses structural pattern matching on the described steps.
    """
    text = (topic + " " + content[:1000]).lower()

    patterns = {
        "engineering": ("实现", "测试", "部署", "开发", "构建", "发布", "代码", "审查", "review", "上线", "运维", "巡检"),
        "scientific": ("假设", "实验", "数据", "分析", "结论", "验证", "观测"),
        "diagnostic": ("诊断", "分类", "检查", "排查", "定位", "根因", "症状", "判断", "识别"),
        "design-thinking": ("设计", "原型", "用户", "迭代", "反馈", "修改"),
        "business-process": ("审批", "确认", "核对", "归档", "流程", "提交", "通过", "退款", "入职", "报销", "申请", "验证", "执行", "通知", "计算"),
        "creative": ("灵感", "草稿", "打磨", "创作", "编辑", "展示"),
    }

    best, best_score = None, 0
    for key, keywords in patterns.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best = next((m for m in METHODOLOGIES if m.key == key), None)

    if best and best_score >= 1:
        return best

    # Fallback: infer methodology from discipline when keywords are insufficient
    domain = detect_domain(text[:200] if len(text) > 200 else text)
    if domain:
        return _discipline_methodology(domain.key)

    return None


def methodology_context(topic: str, content: str = "") -> str:
    """Build a methodology-awareness context string for extraction prompts."""
    method = detect_methodology(topic, content)
    if not method:
        return ""
    examples = "\n".join(f"  - {ex}" for ex in method.cross_domain_examples)
    return (
        f"\n## 🧠 方法论模式识别\n"
        f"检测到本流程遵循 **{method.name}**（{method.pattern}）。\n"
        f"- 哲学根基：{method.philosophical_root}\n"
        f"- 萃取指引：{method.extraction_guidance}\n"
        f"- 跨领域类比（结构同构的流程）：\n{examples}\n"
        f"- 请在苏格拉底追问中运用该方法论的验证标准。"
    )


def build_taxonomy_context(topic: str, content: str = "") -> str:
    """Domain-only taxonomy context (methodology via dna_context.build_dna_context)."""
    return domain_classification_context(topic, content)


# ── Discipline → Methodology mapping (fallback when keyword detection fails) ──

_DISCIPLINE_METHODOLOGY: dict[str, str] = {
    "computer-science": "engineering",
    "medicine-health": "diagnostic",
    "management-science": "business-process",
    "law": "diagnostic",
    "economics-finance": "business-process",
    "education": "design-thinking",
    "design": "design-thinking",
    "engineering": "engineering",
    "natural-science": "scientific",
    "social-science": "scientific",
    "journalism-communication": "creative",
    "agriculture": "engineering",
}


def _discipline_methodology(discipline_key: str) -> Methodology | None:
    """Get the methodology for a discipline (fallback mapping)."""
    method_key = _DISCIPLINE_METHODOLOGY.get(discipline_key)
    if method_key:
        return next((m for m in METHODOLOGIES if m.key == method_key), None)
    return None
