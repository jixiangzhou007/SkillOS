"""Domain skill skeleton templates for fast extraction (P2).

Pre-built S_trigger / S_body / S_route scaffolds for high-frequency domains.
Matched from user goal keywords; injected into SkillExtractionAgent generation.
"""


from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainTemplate:
    template_id: str
    title: str
    domain: str
    bench_categories: list[str]
    keywords: tuple[str, ...]
    tool_name_hint: str
    opening: str
    skeleton: str
    negative_keywords: tuple[str, ...] = ()


@dataclass
class DomainTemplateScore:
    template: DomainTemplate
    score: int
    hits: list[str] = field(default_factory=list)


@dataclass
class DomainCompetitionResult:
    primary: DomainTemplate | None
    secondary: list[DomainTemplateScore]
    all_scored: list[DomainTemplateScore]
    conflicts: list[str]
    ambiguous: bool


# Minimum keyword score to enter competition; gap below this → ambiguous primary
_MIN_MATCH_SCORE = 2
_AMBIGUITY_GAP = 2

# Domain-template pairs that need explicit user disambiguation
_TEMPLATE_CONFLICTS: dict[frozenset[str], str] = {
    frozenset({"finance-expense-audit", "security-audit"}): (
        "财务报销审计 vs 安全审计：「审计」一词多义。"
        "请明确是费用/发票合规，还是系统/网络安全审计。"
    ),
    frozenset({"finance-expense-audit", "workflow-refund"}): (
        "财务报销 vs 电商退款：两者都涉及审批与金额，请确认主流程归属。"
    ),
    frozenset({"law-contract-review", "workflow-refund"}): (
        "合同审核 vs 退款流程：若涉及退款条款，请明确以法务审阅还是客服执行为主。"
    ),
    frozenset({"code-review-pr", "design-ui-review"}): (
        "代码审查 vs UI 设计评审：请确认评审对象是代码变更还是设计稿。"
    ),
}


DOMAIN_TEMPLATES: tuple[DomainTemplate, ...] = (
    DomainTemplate(
        template_id="workflow-refund",
        title="电商客服退款处理",
        domain="management-science",
        bench_categories=["workflow", "documentation"],
        keywords=(
            "退款", "退货", "客服", "电商", "订单退款", "refund", "售后",
        ),
        tool_name_hint="ecommerce-refund",
        opening=(
            "已匹配 **退款/售后流程** 模板。请补充：\n"
            "1. 触发条件（仅退款 / 退货退款 / 部分退款？）\n"
            "2. 需要人工复核的异常（金额阈值、重复申请等）\n"
            "3. 与支付/ERP 系统的对接方式\n\n"
            "若流程已清楚，可直接回复「可以了」生成技能。"
        ),
        skeleton="""## 建议骨架（workflow-refund）
## S_trigger
- keywords: 退款, 退货, 售后, 订单取消
- context: 买家发起退款/退货申请时
- excludes: 非订单类咨询、纯物流查询

## S_body
1. 校验订单状态与支付记录
2. 识别退款类型（仅退款 / 退货退款 / 部分退款）
3. 按政策计算可退金额与手续费
4. 异常场景升级人工（超限、重复申请、风控命中）
5. 执行退款并记录 audit trail
6. 通知买家与同步 ERP/支付渠道

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 金额 ≤ 自动阈值且无风控 | 自动通过 | 记录工单号 |
| 超阈值或重复申请 | 人工复核 | SLA 内响应 |
| 已发货仅退款 | 拦截物流/拒收流程 | [待确认] |

## S_params
- order_id: string — 订单编号
- refund_type: enum — full/partial/return
- amount: number — 申请退款金额
""",
    ),
    DomainTemplate(
        template_id="code-review-pr",
        title="GitHub PR 代码审查",
        domain="computer-science",
        bench_categories=["code-review", "api-design", "documentation"],
        keywords=(
            "pull request", "pr审查", "pr 审查", "code review", "github pr",
            "合并请求", "代码审查", "sql注入", "review",
        ),
        tool_name_hint="github-pr-review",
        opening=(
            "已匹配 **GitHub PR 审查** 模板。请补充：\n"
            "1. 审查清单优先级（安全 / 性能 / 可读性）\n"
            "2. 必须拦截的问题类型（SQL 注入、密钥泄露等）\n"
            "3. 评论风格（blocking vs suggestion）\n\n"
            "流程清楚后回复「可以了」即可生成。"
        ),
        skeleton="""## 建议骨架（code-review-pr）
## S_trigger
- keywords: pull request, PR, code review, merge request, diff
- context: 收到 PR/MR 需要审查或用户要求 review 代码变更
- excludes: 与代码无关的工单

## S_body
1. 阅读 PR 描述与变更范围（文件清单 + diff 摘要）
2. 安全扫描：SQL 注入、XSS、硬编码密钥、危险 API
3. 正确性：边界条件、错误处理、并发与资源泄漏
4. API/契约：Breaking change、版本与文档同步
5. 输出结构化审查意见（blocking / suggestion / praise）

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 存在 blocking 安全问题 | 请求修改后再合并 | 必须引用具体行 |
| 仅风格/命名问题 | suggestion 评论 | 不阻塞 |
| 变更过大 | 建议拆分 PR | [待确认] |

## S_params
- pr_url: string — PR 链接或 repo#number
- base_branch: string — 目标分支（默认 main）
- focus: enum — security/performance/readability/all
""",
    ),
    DomainTemplate(
        template_id="data-csv-clean",
        title="运营级 CSV 清洗",
        domain="engineering",
        bench_categories=["data-processing", "documentation"],
        keywords=(
            "csv", "数据清洗", "表格清洗", "excel", "去重", "空值",
            "etl", "pandas", "数据导出",
        ),
        tool_name_hint="csv-clean-ops",
        opening=(
            "已匹配 **CSV/表格清洗** 模板。请补充：\n"
            "1. 输入来源（上传文件 / S3 / 数据库导出）\n"
            "2. 必做规则（去重键、空值策略、编码）\n"
            "3. 输出格式与质量报告要求\n\n"
            "规则齐全后回复「保存」生成技能。"
        ),
        skeleton="""## 建议骨架（data-csv-clean）
## S_trigger
- keywords: csv, 清洗, 去重, 表格, excel, 数据导出
- context: 运营/分析需要清洗结构化表格数据
- excludes: 非表格类文本处理

## S_body
1. 探测编码与分隔符；加载样本行校验 schema
2. 标准化列名与类型（日期、金额、枚举）
3. 去重（指定 key）、空值填充或剔除策略
4. 异常值与跨列一致性校验
5. 输出清洗后文件 + 质量报告（行数、丢弃原因统计）

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 缺必填列 | 中止并报告 | 不静默丢弃 |
| 重复率 > 阈值 | 去重并记录 | 保留最新/最早 [待确认] |
| 编码无法识别 | 尝试 utf-8/gbk | fallback 人工 |

## S_params
- file_path: string — 输入 CSV 路径
- dedupe_keys: string — 去重字段，逗号分隔
- null_policy: enum — drop/fill/marker
""",
    ),
    # ── 5 additional domains (Sprint 8) ──
    DomainTemplate(
        template_id="finance-expense-audit", title="财务报销审计",
        domain="economics-finance", bench_categories=["workflow", "documentation"],
        keywords=(
            "报销", "发票", "财务审计", "差旅", "财务", "费用", "凭证", "对账", "expense",
        ),
        tool_name_hint="expense-audit",
        negative_keywords=(
            "安全审计", "网络安全", "渗透", "漏洞", "应急响应", "等保", "security audit",
            "退款", "退货", "客户退款", "订单", "售后期", "演练", "红蓝", "drill",
        ),
        opening=("已匹配 **财务报销审计** 模板。请补充：\n1. 公司费用标准（差旅/招待/办公上限）\n2. 审批链（金额分级：部门→财务→总经理）\n3. 与 ERP/OA 系统的对接方式\n\n若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（finance-expense-audit）
## S_trigger
- keywords: 报销, 发票, 费用, 审计, 差旅
- context: 员工提交报销申请后触发

## S_body
1. 校验发票真伪与抬头一致性（增值税发票查验平台）
2. 比对费用标准（差旅≤标准/招待≤预算/办公≤上限）
3. 金额分级审批路由（<5k部门→<20k财务→>20k总经理）
4. 超标项自动退回并注明超标金额与标准
5. 通过后生成凭证号并同步ERP/OA

## S_route
| 条件 | 动作 |
|------|------|
| 金额≤5000且无超标 | 自动通过 |
| 超标项存在 | 退回申请人 |
| 缺发票或假发票 | 退回并标记 |

## S_params
- amount: number — 报销总额
- category: enum — 差旅/招待/办公
""",
    ),
    DomainTemplate(
        template_id="law-contract-review", title="合同审核",
        domain="law", bench_categories=["workflow", "documentation"],
        keywords=("合同", "审核", "条款", "法务", "合规", "法律", "协议", "contract", "签订"),
        tool_name_hint="contract-review",
        negative_keywords=("退款", "退货", "csv", "数据清洗", "pull request"),
        opening=("已匹配 **合同审核** 模板。请补充：\n1. 主要审哪类合同（采购/销售/劳动/NDA）\n2. 必须拦截的红线条款（无限责任/霸王条款）\n3. 审批链与用印流程\n\n若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（law-contract-review）
## S_trigger
- keywords: 合同, 审核, 条款, 法务, 签订
- context: 业务部门提交合同审核申请时

## S_body
1. 收稿登记：检查合同完整性（双方信息、标的、金额、期限）
2. 条款比对：对照合同模板库中同类合同的基准条款
3. 风险识别：标记红线条款（无限责任/单方解约/管辖权陷阱）
4. 修改建议：逐条批注修改方案与法律依据
5. 审批流转：法务初审→业务确认→管理层终审→用印归档

## S_route
| 条件 | 动作 |
|------|------|
| 含无限责任条款 | 强制修改，不通过不盖章 |
| 金额>100万 | 法务总监+外部律师双审 |
| 标准模板合同 | 快速通道（1工作日） |

## S_params
- contract_type: enum — 采购/销售/劳动/NDA
- amount: number — 合同金额
""",
    ),
    DomainTemplate(
        template_id="design-ui-review", title="UI设计评审",
        domain="design", bench_categories=["documentation", "workflow"],
        keywords=("UI", "设计", "界面", "用户体验", "UX", "视觉", "可用性", "设计稿", "brand", "品牌"),
        tool_name_hint="ui-design-review",
        opening=("已匹配 **UI 设计评审** 模板。请补充：\n1. 评审维度（可用性/可访问性/品牌一致性）\n2. 设计规范与组件库（如 Ant Design）\n3. 评审流程（自检→同行→产品确认）\n\n若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（design-ui-review）
## S_trigger
- keywords: UI, 设计, 评审, 界面, 视觉
- context: 设计师提交设计稿评审时

## S_body
1. 设计自检：对照设计规范与组件库检查一致性
2. 可用性审查：信息层级、操作流程、空/错/加载态
3. 可访问性检查：对比度≥4.5:1、触控区域≥44px
4. 品牌一致性：色彩、字体、圆角是否匹配 Design Token
5. 输出评审意见（blocking/suggestion/nice-to-have）

## S_route
| 条件 | 动作 |
|------|------|
| 品牌色偏差 | blocking 修改 |
| 交互流程缺失 | suggestion 补充 |
| 新组件设计 | 同步组件库维护者 |

## S_params
- design_url: string — Figma/Sketch 链接
- platform: enum — web/iOS/Android
""",
    ),
    DomainTemplate(
        template_id="science-experiment-design", title="科学实验设计",
        domain="natural-science", bench_categories=["data-processing", "documentation"],
        keywords=("实验", "假设", "数据", "对照", "变量", "科学", "验证", "观测", "experiment", "统计"),
        tool_name_hint="experiment-design",
        opening=("已匹配 **科学实验设计** 模板。请补充：\n1. 实验类型（对照实验/自然观察/模拟）\n2. 变量设计（自变量/因变量/控制变量）\n3. 统计分析方案与样本量要求\n\n若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（science-experiment-design）
## S_trigger
- keywords: 实验, 假设, 验证, 数据, 对照
- context: 研究问题需要实验验证时

## S_body
1. 明确研究问题与可证伪假设（H₀ vs H₁）
2. 设计变量：自变量、因变量、控制变量与混淆变量
3. 确定样本量与分组方案（随机化/盲法）
4. 执行实验并记录原始数据（含异常与排除标准）
5. 统计分析（效应量+置信区间+p值，非仅p值）
6. 结论与局限性声明（不超数据支持范围）

## S_route
| 条件 | 动作 |
|------|------|
| p>0.05 | 不能拒绝H₀ |
| 样本量不足 | 补充实验或标注局限 |

## S_params
- hypothesis: string — 研究假设
- sample_size: number — 每组样本量
- alpha: number — 显著性水平（默认0.05）
""",
    ),
    DomainTemplate(
        template_id="edu-course-design", title="培训课程设计",
        domain="education", bench_categories=["documentation", "workflow"],
        keywords=("课程", "培训", "教学", "学习", "课件", "讲师", "学员", "考核", "course", "training"),
        tool_name_hint="course-design",
        opening=("已匹配 **培训课程设计** 模板。请补充：\n1. 学员画像（背景/人数/起点水平）\n2. 培训目标与评估方式（Kirkpatrick 四级）\n3. 授课形式（线下/线上/混合）与时长\n\n若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（edu-course-design）
## S_trigger
- keywords: 课程, 培训, 教学, 学员, 讲师
- context: 培训需求确认后启动课程设计

## S_body
1. 需求调研：学员背景、学习目标、时间预算、设备环境
2. 目标定义：用 Bloom 分类学撰写可测量的学习目标
3. 大纲设计：模块划分（每模块≤45min）、知识点序列、互动环节
4. 课件制作：PPT/视频/练习/案例，适配学员水平
5. 试讲迭代：小规模试讲→收集反馈→修改
6. 正式授课+效果评估（Kirkpatrick 四级：反应/学习/行为/结果）

## S_route
| 条件 | 动作 |
|------|------|
| 学员零基础 | 增加预备知识模块 |
| 线上授课 | 每20min插入互动/测验 |
| 评估<3/5 | 重修内容并重新试讲 |

## S_params
- audience_level: enum — beginner/intermediate/advanced
- duration_hours: number — 总时长
- delivery_mode: enum — online/offline/hybrid
""",
    ),
    DomainTemplate(
        template_id="security-audit",
        title="安全审计",
        domain="computer-science",
        bench_categories=["workflow", "documentation"],
        keywords=(
            "安全审计", "网络安全", "渗透测试", "漏洞", "应急响应", "合规检查",
            "security audit", "SOC", "等保", "安全评估",
        ),
        tool_name_hint="security-audit",
        negative_keywords=("报销", "发票", "差旅", "费用报销", "expense", "财务审计"),
        opening=(
            "已匹配 **安全审计** 模板。请补充：\n"
            "1. 审计类型（合规检查 / 渗透测试 / 应急响应）\n"
            "2. 审计范围（系统/网络/应用/数据）\n"
            "3. 证据收集与整改闭环要求\n\n"
            "若流程已清楚，可直接回复「可以了」生成技能。"
        ),
        skeleton="""## 建议骨架（security-audit）
## S_trigger
- keywords: 安全审计, 审计任务, 合规检查, 渗透测试
- context: 收到安全审计/合规检查任务时
- excludes: 财务审计、代码 review、日常非正式巡检

## S_body
1. 明确审计范围与标准（等保/SOC2/内部基线）
2. 收集证据（日志、配置、访问记录、漏洞扫描报告）
3. 识别风险项并分级（高/中/低）
4. 输出整改建议与责任人/SLA
5. 跟踪整改闭环并复验

## S_route
| 条件 | 动作 |
|------|------|
| 高危漏洞 | 立即阻断 + 24h 内修复 |
| 中危项 | 7 天内整改 |
| 合规缺口 | 补充证据后复评 |

## S_params
- audit_scope: enum — network/app/data/compliance
- severity: enum — high/medium/low
""",
    ),
    # ── Medicine & Health (12-discipline expansion) ──
    DomainTemplate(
        template_id="healthcare-triage",
        title="门诊分诊/医疗评估",
        domain="medicine-health",
        bench_categories=["workflow", "documentation"],
        keywords=("分诊", "门诊", "急诊", "诊断", "护理", "治疗", "患者", "病历", "体检", "triage", "症状", "处方"),
        tool_name_hint="healthcare-triage",
        opening=("已匹配 **门诊分诊/医疗评估** 模板。请补充：\n"
                 "1. 患者来源（门诊/急诊/转诊）与挂号流程\n"
                 "2. 分诊级别标准（如Ⅰ-Ⅳ级）与对应处置\n"
                 "3. 特殊人群（孕妇/儿童/老人/精神科）的差异化处理\n\n"
                 "若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（healthcare-triage）
## S_trigger
- keywords: 分诊, 门诊, 急诊, triage, 挂号
- context: 患者挂号后进入分诊台时
- excludes: 已入院患者的科室间转诊

## S_body
1. 生命体征测量：体温、血压、心率、血氧（四项必测）
2. 主诉与病史采集：主诉、既往史、用药史、过敏史（标红）
3. 流行病学调查：疫区接触史、传染病症状筛查（发热病人必做）
4. 紧急程度分级（Ⅰ-Ⅳ级）：对照分诊标准表判断
5. 科室安排与转运：Ⅰ级抢救室、Ⅱ级优先、Ⅲ-Ⅳ级候诊

## S_route
| 条件 | 动作 |
|------|------|
| 生命体征不稳（Ⅰ级） | 直接送抢救室 |
| 疑似传染病 | 发口罩→隔离候诊区 |
| 孕妇 | 优先处理（不论级别） |
| 精神科 | 需陪同+独立房间 |

## S_params
- patient_age: number — 患者年龄
- temperature: number — 体温（℃）
- blood_pressure: string — 血压
- triage_level: enum — Ⅰ/Ⅱ/Ⅲ/Ⅳ
""",
    ),

# ── Social Science & Journalism (12-discipline expansion) ──
    DomainTemplate(
        template_id="social-survey",
        title="社会调研/问卷分析",
        domain="social-science",
        bench_categories=["data-processing", "documentation"],
        keywords=("调研", "问卷", "访谈", "社会", "心理", "行为", "政策", "治理", "公共", "调查", "survey"),
        tool_name_hint="social-survey",
        opening="已匹配 **社会调研/问卷分析** 模板。请补充：\n1. 调研类型（问卷调查/深度访谈/田野观察）\n2. 抽样方法与样本量要求\n3. 数据分析方法（描述统计/回归/编码）\n\n若流程已清楚，可直接回复「可以了」生成技能。",
        skeleton="""## S_trigger
- keywords: 调研, 问卷, 访谈, survey, 调查
- context: 研究问题确定后启动数据收集时

## S_body
1. 研究设计
2. 抽样方案
3. 工具开发
4. 数据收集
5. 数据分析
6. 报告撰写

## S_route
| 条件 | 动作 |
|------|------|
| 回收率<70% | 标记低回收率 |
| 样本量不足 | 标记统计功效不足 |

## S_params
- sample_size: number
- confidence_level: number
- method: enum — questionnaire/interview/observation
""",
    ),
    DomainTemplate(
        template_id="media-publish",
        title="内容审核/发布流程",
        domain="journalism-communication",
        bench_categories=["documentation", "workflow"],
        keywords=("新闻", "写作", "编辑", "出版", "审核", "内容", "媒体", "公众号", "文案", "校对", "发布", "publish"),
        tool_name_hint="media-publish",
        opening="已匹配 **内容审核/发布流程** 模板。请补充：\n1. 内容类型（新闻/公关稿/社媒/营销）\n2. 审核层级（自审→编辑→主编→法务）\n3. 必须拦截的红线（虚假信息/侵权/违规）\n\n若流程已清楚，可直接回复「可以了」生成技能。",
        skeleton="""## S_trigger
- keywords: 新闻, 编辑, 审核, 发布, 内容, publish
- context: 内容稿件提交审核时

## S_body
1. 选题与采集
2. 写稿
3. 编辑初审
4. 事实核查
5. 合规审查
6. 排版发布

## S_route
| 条件 | 动作 |
|------|------|
| 涉及敏感话题 | 法务+主编双审 |
| 数据来源不明 | 退回补充 |
| AI生成内容 | 标注+人工核验 |

## S_params
- content_type: enum — news/opinion/social_media/ad
- author: string
- sources: list
- review_level: enum — standard/sensitive/legal
""",
    ),
    # ── Agriculture (12-discipline completion) ──
    DomainTemplate(
        template_id="agriculture-crop-management",
        title="农作物种植管理",
        domain="agriculture",
        bench_categories=["workflow", "documentation"],
        keywords=("种植", "养殖", "畜牧", "兽医", "检疫", "食品安全", "土壤", "灌溉", "施肥", "收割", "储藏",
                  "转基因", "有机", "农药", "质检", "种子", "农产品", "田间", "agriculture", "crop", "farm"),
        tool_name_hint="crop-management",
        opening=("已匹配 **农作物种植管理** 模板。请补充：\n"
                 "1. 作物类型（粮食/蔬菜/水果/经济作物）\n"
                 "2. 种植规模（小农户/合作社/企业农场）\n"
                 "3. 认证要求（有机/绿色/无公害/GAP）\n\n"
                 "若流程已清楚，可直接回复「可以了」生成技能。"),
        skeleton="""## 建议骨架（agriculture-crop-management）
## S_trigger
- keywords: 种植, 作物, 田间管理, 施肥, 收割
- context: 种植季开始前或日常田间巡查时
- excludes: 畜牧业、水产养殖

## S_body
1. 土壤检测：pH、有机质、N-P-K、重金属（参照GB 15618标准）
2. 品种选择：根据气候区、土壤类型、市场需求选择
3. 播种/定植：播期、密度、深度；种子处理（温汤浸种/药剂拌种）
4. 水肥管理：滴灌/喷灌方案；基肥+追肥；叶面肥补充
5. 病虫害防治：IPM综合防治；定期巡查记录；生物防治优先
6. 采收与采后处理：成熟度判断→采收→预冷→分级→包装→冷链

## S_route
| 条件 | 动作 |
|------|------|
| 土壤pH<5.5 | 施用石灰调节 |
| 病虫害爆发 | 启动应急防治方案 |
| 采收期遇雨 | 延迟采收+排水 |

## S_params
- crop_type: enum — grain/vegetable/fruit/cash_crop
- area_mu: number — 种植面积（亩）
- certification: enum — organic/green/conventional/GAP
""",
    ),
)
def list_domain_templates() -> list[dict]:
    """Serialize templates for API / UI."""
    return [
        {
            "template_id": t.template_id,
            "title": t.title,
            "domain": t.domain,
            "bench_categories": t.bench_categories,
            "keywords": list(t.keywords),
            "tool_name_hint": t.tool_name_hint,
        }
        for t in DOMAIN_TEMPLATES
    ]


def get_template(template_id: str) -> DomainTemplate | None:
    return next((t for t in DOMAIN_TEMPLATES if t.template_id == template_id), None)


def _score_template(text: str, tmpl: DomainTemplate) -> DomainTemplateScore:
    """Score a template against text; 0 if vetoed by negative keywords."""
    if not text or len(text.strip()) < 2:
        return DomainTemplateScore(tmpl, 0, [])

    lowered = text.lower()
    for neg in tmpl.negative_keywords:
        if neg.lower() in lowered:
            return DomainTemplateScore(tmpl, 0, [])

    hits: list[str] = []
    score = 0
    for kw in tmpl.keywords:
        if kw.lower() in lowered:
            hits.append(kw)
            score += 2 if len(kw) >= 3 else 1

    try:
        from skillos.knowledge.taxonomy import detect_domain
        domain = detect_domain(text)
        if domain and domain.key == tmpl.domain:
            score += 3
    except Exception:
        pass

    if tmpl.title.lower() in lowered:
        score += 2

    return DomainTemplateScore(tmpl, score, hits)


def score_domain_templates(text: str, top_k: int = 5) -> list[DomainTemplateScore]:
    """Return templates ranked by keyword score (excludes vetoed / zero-score)."""
    if not text or len(text.strip()) < 2:
        return []
    scored = [_score_template(text, tmpl) for tmpl in DOMAIN_TEMPLATES]
    scored = [s for s in scored if s.score > 0]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:top_k]


def cross_template_conflict_check(templates: list[DomainTemplate]) -> list[str]:
    """Detect domain-template pairs that need user disambiguation."""
    ids = {t.template_id for t in templates}
    conflicts: list[str] = []
    for pair, msg in _TEMPLATE_CONFLICTS.items():
        if pair.issubset(ids):
            conflicts.append(msg)
    return conflicts


def resolve_domain_competition(text: str, top_k: int = 3) -> DomainCompetitionResult:
    """Pick primary + secondary domain templates with conflict/ambiguity flags."""
    scored = score_domain_templates(text, top_k=top_k + 2)
    eligible = [s for s in scored if s.score >= _MIN_MATCH_SCORE]
    if not eligible:
        return DomainCompetitionResult(None, [], scored, [], False)

    primary = eligible[0].template
    secondary = eligible[1:top_k]
    ambiguous = (
        len(eligible) >= 2
        and (eligible[0].score - eligible[1].score) < _AMBIGUITY_GAP
    )
    templates = [primary] + [s.template for s in secondary]
    conflicts = cross_template_conflict_check(templates)
    return DomainCompetitionResult(
        primary=primary,
        secondary=secondary,
        all_scored=scored,
        conflicts=conflicts,
        ambiguous=ambiguous,
    )


def format_competition_notice(comp: DomainCompetitionResult) -> str:
    """User-facing notice when multiple domain templates compete."""
    if not comp.primary:
        return ""
    parts: list[str] = []
    if len(comp.secondary) >= 1:
        alts = "、".join(s.template.title for s in comp.secondary[:2])
        parts.append(f"📎 **关联领域模板**（次要继承）：{alts}")
    if comp.ambiguous:
        parts.append(
            "⚠️ **多域竞争**：多个模板得分接近，请在对话中说明哪条流程是主线，"
            "避免把财务/法务/安全步骤混进同一 S_route。"
        )
    if comp.conflicts:
        parts.append("⚠️ **领域冲突**：" + " | ".join(comp.conflicts[:2]))
    return ("\n\n" + "\n".join(parts)) if parts else ""


def match_domain_template(text: str) -> DomainTemplate | None:
    """Pick best domain template by keyword hits (≥2)."""
    comp = resolve_domain_competition(text, top_k=1)
    return comp.primary


def match_domain_templates(text: str, top_k: int = 3) -> list[DomainTemplate]:
    """Return top-k matching domain templates (for multi-domain inheritance)."""
    comp = resolve_domain_competition(text, top_k=top_k)
    if not comp.primary:
        return []
    return [comp.primary] + [s.template for s in comp.secondary]


def evolve_domain_template(
    template_id: str,
    skill_content: str,
    skill_score: int,
    *,
    skill_name: str = "",
) -> bool:
    """Evolve persisted domain DNA from a high-score skill; bump semver on novel steps."""
    from skillos.knowledge.dna_evolution import evolve_domain_template_record

    result = evolve_domain_template_record(
        template_id,
        skill_name or "anonymous",
        skill_content,
        skill_score,
    )
    return bool(result.get("evolved"))


def template_opening(tmpl: DomainTemplate) -> str:
    return tmpl.opening


def get_generation_boost(template_id: str) -> str:
    from skillos.knowledge.dna_evolution import get_template_generation_boost

    tmpl = get_template(template_id)
    if not tmpl:
        return ""
    return get_template_generation_boost(template_id, tmpl.skeleton)


def taxonomy_meta_for_template(tmpl: DomainTemplate) -> dict:
    """Frontmatter fields aligned with skill_routing."""
    return {
        "domain": tmpl.domain,
        "bench_categories": list(tmpl.bench_categories),
        "domain_template": tmpl.template_id,
    }


