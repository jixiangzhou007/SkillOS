"""Philosophical Methodology DNA — Layer 0 of the inheritance hierarchy.

Universal thinking patterns that transcend domains. Each methodology is a
"genetic blueprint" for how humans solve problems, validated across centuries
of philosophical inquiry.

Inheritance chain:
  Philosophical DNA (this file) → Domain DNA (domain_templates.py)
    → Skill DNA (pattern_miner.py) → Individual Skills (SKILL.md)

Cross-domain inheritance: a skill can inherit from multiple philosophical
patterns. When patterns conflict, the skill must choose a dominant parent.
"""


from dataclasses import dataclass
from typing import Optional


@dataclass
class PhilosophicalDNA:
    """One universal methodology — the 'phylum-level' genetic blueprint."""
    method_id: str
    name: str                    # Chinese name
    name_en: str                 # English name
    philosophical_root: str      # Which philosopher/tradition?
    pattern: list[str]           # The step sequence (canonical)
    trigger_questions: list[str] # What to ask during Socratic extraction
    evidence_standard: str       # What counts as "proof" for this methodology?
    ideal_structure: str         # Preferred S_body / S_route shape
    domain_affinities: list[str] # Which domains naturally use this methodology?
    # Inheritance metadata
    parent_id: str = ""          # Can inherit from another methodology (specialization)
    stability: float = 0.0       # How stable/reliable is this pattern? (0-1, from data)
    derived_from_skills: int = 0 # How many skills contributed to refining this DNA?


# ── Universal Methodologies ───────────────────────────────────

PHILOSOPHICAL_DNA: dict[str, PhilosophicalDNA] = {
    "pdca": PhilosophicalDNA(
        method_id="pdca",
        name="PDCA 循环",
        name_en="Plan-Do-Check-Act",
        philosophical_root="Deming 质量管理 + 泰勒科学管理。通过标准化和持续改进来提升系统效率。",
        pattern=["Plan (规划目标与标准)", "Do (执行计划)", "Check (检查结果与偏差)", "Act (标准化改进或调整)"],
        trigger_questions=[
            "这个流程的每一步是否有明确的通过标准？",
            "如果结果偏离预期，回退机制是什么？",
            "有没有形成可复制的 SOP 文档？",
        ],
        evidence_standard="可量化的效率指标（时间/成本/错误率）+ SOP 文档",
        ideal_structure="S_trigger(触发条件+输入校验) → S_body(4步循环,每步带if-then) → S_route(异常分支表) → S_params(阈值/时限/SLA)",
        domain_affinities=["management-science", "economics-finance", "engineering", "medicine-health"],
        stability=0.9,
    ),
    "ooda": PhilosophicalDNA(
        method_id="ooda",
        name="OODA 循环",
        name_en="Observe-Orient-Decide-Act",
        philosophical_root="John Boyd 军事战略。在不确定环境中快速感知、判断、行动、调整。",
        pattern=["Observe (收集态势信息)", "Orient (分析并建立认知模型)", "Decide (选择行动方案)", "Act (执行并观察反馈)"],
        trigger_questions=[
            "信息不完整时，默认假设是什么？",
            "决策的时效窗口是多长？超时后如何升级？",
            "有没有快速回滚或撤退的安全阀？",
        ],
        evidence_standard="响应时间 + 决策准确率 + 回滚/恢复时间",
        ideal_structure="S_trigger(告警/异常触发) → S_body(4步,Observe带数据源) → S_route(分级响应表:P0/P1/P2) → S_params(响应时限/升级链)",
        domain_affinities=["computer-science", "engineering", "management-science", "medicine-health"],
        stability=0.85,
    ),
    "scientific-method": PhilosophicalDNA(
        method_id="scientific-method",
        name="科学方法",
        name_en="Scientific Method",
        philosophical_root="Bacon 经验主义 + Popper 证伪主义。知识通过可复现的观察和证伪测试来推进。",
        pattern=["Observe (观察现象)", "Hypothesize (提出可证伪假设)", "Experiment (设计对照实验)", "Analyze (统计分析)", "Conclude (结论的边界与局限)"],
        trigger_questions=[
            "这个结论的可证伪条件是什么？",
            "样本量是否足够？控制变量是否完整？",
            "结论是否超越了数据支持的范围？",
        ],
        evidence_standard="可复现性 + 统计显著性 + 效应量",
        ideal_structure="S_trigger(研究问题) → S_body(5步,含统计方案) → S_route(p值判断/样本不足/混淆变量) → S_params(α水平/效应量/样本量)",
        domain_affinities=["natural-science", "education-training", "computer-science"],
        stability=0.95,
    ),
    "dialectical": PhilosophicalDNA(
        method_id="dialectical",
        name="辩证方法",
        name_en="Dialectical Method",
        philosophical_root="Hegel 正反合 + Marx 唯物辩证法 + Popper 猜想与反驳。真理在矛盾的对立统一中涌现。",
        pattern=["Thesis (提出正题/观点A)", "Antithesis (寻找反题/对立观点)", "Synthesis (综合更优方案)", "Verify (验证合题的优越性)"],
        trigger_questions=[
            "如果这个方案是错的，最可能的原因是什么？",
            "有没有和当前方案矛盾的另一套方案？各自的依据是什么？",
            "如何在分歧中找到更优的第三条路？",
        ],
        evidence_standard="两套独立方案 + 比较测试 + 合题优于两者",
        ideal_structure="S_trigger(TODO?) → S_body(4步,Thesis+Antithesis带来源) → S_route(分歧升级/僵局仲裁) → S_params(评审人/比较维度)",
        domain_affinities=["law-compliance", "design-creative", "business-management"],
        stability=0.8,
    ),
    "reductionist": PhilosophicalDNA(
        method_id="reductionist",
        name="还原论方法",
        name_en="Reductionist Method",
        philosophical_root="Descartes 方法论 + 分析哲学。将复杂系统拆解为可独立理解的原子组件。",
        pattern=["Decompose (分解为原子组件)", "Analyze (逐组件独立分析)", "Validate (组件级验证)", "Recompose (重组并验证整体)", "Optimize (全局优化)"],
        trigger_questions=[
            "这个流程的最小可独立验证单元是什么？",
            "如果跳过某一步直接到最后，会发生什么？",
            "每个子组件是否有独立的通过标准？",
        ],
        evidence_standard="组件级测试通过率 + 集成测试通过率",
        ideal_structure="S_trigger(变更/请求触发) → S_body(5步,逐层分解) → S_route(模块依赖矩阵) → S_params(测试覆盖率/复杂度阈值)",
        domain_affinities=["computer-science", "natural-science"],
        stability=0.9,
    ),
    "pragmatic": PhilosophicalDNA(
        method_id="pragmatic",
        name="实用主义方法",
        name_en="Pragmatic Method",
        philosophical_root="Dewey 实用主义 + Simon 有限理性。最优解不来自理论推导，而来自迭代实验和用户反馈。",
        pattern=["Problem (定义核心问题)", "Prototype (最低成本方案)", "Test (真实用户反馈)", "Reflect (学到了什么)", "Iterate (基于反馈改进)"],
        trigger_questions=[
            "最小的可行版本（MVP）是什么？",
            "用户反馈的评判标准是什么？",
            "迭代多少次后如果无效就放弃？",
        ],
        evidence_standard="用户反馈数据 + 迭代收敛速度",
        ideal_structure="S_trigger(需求/创意触发) → S_body(5步,Prototype带MVP定义) → S_route(用户反馈门/Pivot条件) → S_params(迭代次数上限/反馈指标)",
        domain_affinities=["design-creative", "education-training", "business-management"],
        stability=0.75,
    ),
}


def detect_philosophical_dna(topic: str, content: str = "", domain_key: str = "") -> list[PhilosophicalDNA]:
    """Detect which philosophical methodologies apply to a skill.

    Returns list sorted by relevance (best match first). Multiple matches
    are intentional — a skill can inherit from multiple philosophical patterns.
    """
    text = (topic + " " + content[:2000]).lower()
    scored: list[tuple[float, PhilosophicalDNA]] = []

    for dna in PHILOSOPHICAL_DNA.values():
        score = 0.0
        # Domain affinity: if skill's domain matches, strong signal
        if domain_key and domain_key in dna.domain_affinities:
            score += 3.0
        # Pattern keywords in content
        for step in dna.pattern:
            keywords = step.split("(")[0].strip().lower().split()
            score += sum(0.5 for kw in keywords if kw in text)
        # Methodology keywords (broader matching for extraction context)
        method_keywords = {
            "pdca": ("标准", "sop", "检查", "改进", "偏差", "规范", "审批", "流程", "核实", "验收",
                     "绩效", "评估", "评分", "考核", "采购", "预算", "合规"),
            "ooda": ("响应", "告警", "紧急", "升级", "决策", "窗口", "事故", "故障", "恢复",
                     "安全", "审计", "风险", "威胁", "应急"),
            "scientific-method": ("实验", "假设", "数据", "统计", "显著", "样本", "对照", "变量"),
            "dialectical": ("评审", "分歧", "矛盾", "对比", "正反", "比较", "校准", "复核", "辩论"),
            "reductionist": ("分解", "拆解", "原子", "组件", "模块", "集成", "测试", "单元"),
            "pragmatic": ("迭代", "反馈", "原型", "mvp", "用户", "试错", "自评", "面谈", "改进"),
        }
        for kw in method_keywords.get(dna.method_id, ()):
            if kw in text:
                score += 1.0
        scored.append((score, dna))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Return all with score >= 2.0 (significant match) or top-1 if none significant
    result = [dna for s, dna in scored if s >= 2.0]
    if not result and scored[0][0] > 0:
        result = [scored[0][1]]
    return result


def get_philosophical_dna(method_id: str) -> Optional[PhilosophicalDNA]:
    """Get a specific philosophical DNA by ID."""
    return PHILOSOPHICAL_DNA.get(method_id)


def list_philosophical_dna() -> list[dict]:
    """All philosophical DNAs for API/UI."""
    return [
        {
            "method_id": d.method_id, "name": d.name, "name_en": d.name_en,
            "philosophical_root": d.philosophical_root,
            "pattern": d.pattern, "trigger_questions": d.trigger_questions,
            "domain_affinities": d.domain_affinities, "stability": d.stability,
        }
        for d in PHILOSOPHICAL_DNA.values()
    ]


def cross_domain_conflict_check(methods: list[PhilosophicalDNA]) -> list[str]:
    """Detect potential conflicts when a skill inherits from multiple methodologies.

    Returns list of conflict descriptions, or empty if no conflicts.
    """
    conflicts = []
    for i in range(len(methods)):
        for j in range(i + 1, len(methods)):
            a, b = methods[i], methods[j]
            # PDCA vs OODA: both are iterative, but PDCA is slow/standardized, OODA is fast/adaptive
            if {a.method_id, b.method_id} == {"pdca", "ooda"}:
                conflicts.append(
                    "PDCA(标准化渐进) vs OODA(快速适应): "
                    "两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。"
                )
            # Scientific vs Pragmatic: rigor vs speed
            if {a.method_id, b.method_id} == {"scientific-method", "pragmatic"}:
                conflicts.append(
                    "科学方法(严谨可复现) vs 实用主义(快速迭代): "
                    "两者对待'实验'的标准不同。请明确本流程偏向严谨验证还是快速试错。"
                )
            # Reductionist vs Dialectical: decomposition vs synthesis
            if {a.method_id, b.method_id} == {"reductionist", "dialectical"}:
                conflicts.append(
                    "还原论(分解分析) vs 辩证论(对立统一): "
                    "两者分析问题的方式相反。请明确本流程侧重逐层分解还是寻找对立观点。"
                )
    return conflicts


def build_philosophical_context(methods: list[PhilosophicalDNA]) -> str:
    """Build a prompt injection context from detected philosophical DNAs."""
    if not methods:
        return ""
    parts = ["\n## 🧬 哲学方法论 DNA（跨领域通用思维模式）\n"]
    for m in methods[:3]:
        parts.append(f"### {m.name} ({m.name_en})")
        parts.append(f"哲学根基：{m.philosophical_root}")
        parts.append(f"标准模式：{' → '.join(m.pattern)}")
        parts.append(f"追问框架：{' | '.join(m.trigger_questions[:2])}")
        parts.append(f"证据标准：{m.evidence_standard}")
        parts.append("")
    conflicts = cross_domain_conflict_check(methods)
    if conflicts:
        parts.append("### ⚠️ DNA 继承冲突（请在萃取中追问用户偏好）")
        for c in conflicts:
            parts.append(f"- {c}")
        parts.append("")
    return "\n".join(parts)
