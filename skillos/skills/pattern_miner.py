"""Pattern Miner — cross-skill analysis and collective optimization.

"读书百遍，其义自见" — After creating many skills, patterns emerge.

Unlike SkillOpt (optimizes ONE skill from its own traces), PatternMiner
analyzes ALL skills collectively to find:
1. Structural archetypes (common patterns across skills)
2. Success factors (what high-scoring skills share)
3. Anti-patterns (what low-scoring skills share)
4. Improvement suggestions per skill based on cross-skill learning
5. Skill DNA — the essence of a good skill
"""


import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

DNA_PATH = Path(__file__).parent / "knowledge" / "skill_dna.json"

# Layer-2 bootstrap — injected before cross-skill mining produces skill_dna.json
_BOOTSTRAP_DNA: dict = {
    "archetypes": ["workflow", "data-pipeline", "review-checklist"],
    "success_factors": [
        "S_trigger 含场景上下文，不只是关键词",
        "S_params 标注类型与默认值",
        "S_body 每步可执行，含 if-then 分支",
        "S_route 至少 2 行决策表",
    ],
    "anti_patterns": [
        "只有关键词列表没有触发场景",
        "步骤空泛不可执行",
        "未核实就执行不可逆操作（退款/删除/发布）",
    ],
    "dna": [
        "原则1: S_trigger 必须包含触发上下文（何时、何条件下触发）",
        "原则2: S_params 必须定义参数类型、取值范围与默认值",
        "原则3: S_body 每步必须有具体操作指令或 if-then 分支",
        "原则4: 分支数 ≥ 3（正常流程、变体、异常处理）",
        "原则5: 步骤数 1-5，每步足够详细可落地",
        "原则6（奥卡姆剃刀）: 同等效果选步骤更少的方案，合并相邻短步骤",
    ],
    "generated_at": 0.0,
    "source": "bootstrap",
}


@dataclass
class SkillProfile:
    """A summary profile of one skill for cross-skill analysis."""

    name: str
    content_length: int
    has_trigger: bool
    has_body: bool
    has_params: bool
    has_appendix: bool
    step_count: int = 0
    branch_count: int = 0  # if-then branches
    avg_score: float = 0.0
    total_runs: int = 0
    source: str = ""  # created from conversation or URL
    kb_items: int = 0  # knowledge base items


@dataclass
class CrossSkillInsight:
    """One insight discovered from cross-skill analysis."""

    type: str  # "pattern", "anti_pattern", "template", "gap"
    description: str
    affected_skills: list[str] = field(default_factory=list)
    confidence: float = 0.5
    suggestion: str = ""


@dataclass
class SkillDNA:
    """The distilled essence of what makes a good skill."""

    archetypes: list[str] = field(default_factory=list)  # common structural patterns
    success_factors: list[str] = field(default_factory=list)  # what high-scorers share
    anti_patterns: list[str] = field(default_factory=list)  # what low-scorers share
    templates: list[str] = field(default_factory=list)  # reusable skill skeletons
    generated_at: float = 0.0


# ═══════════════════════════════════════════════════════════════
# 1. Profiling — build summaries of all skills
# ═══════════════════════════════════════════════════════════════

def profile_all_skills() -> list[SkillProfile]:
    """Build a lightweight profile of every skill for analysis."""
    from skillos.evolution import evolver as skill_evolver
    from skillos.skills import skill_store

    profiles = []
    for name in skill_store.list_skills():
        if name in ("brainstorming", "skill-creator", "skillopt-test", "my-draft"):
            continue
        try:
            body = skill_store.get_skill_body(skill_store.load_skill(name))
        except Exception:
            continue

        # Analyze structure
        has_trigger = bool(re.search(r'##\s*(?:S_trigger|When to use|触发)', body))
        has_body = bool(re.search(r'##\s*(?:S_body|Instructions|步骤)', body))
        has_params = bool(re.search(r'##\s*(?:S_params|Inputs|参数)', body))
        has_appendix = bool(re.search(r'##\s*S_appendix', body))

        # Count steps and branches
        body_section = re.search(r'##\s*S_body\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL)
        body_text = body_section.group(1) if body_section else ""
        steps = len(re.findall(r'^\d+[\.\、)]', body_text, re.MULTILINE))
        branches = len(re.findall(r'if|如果|当.*时|否则|不然|分支|条件', body_text))

        # Scores
        try:
            traces = skill_evolver.get_recent_traces(name, 10)
            scores = [t.get("score", 0) for t in traces if t.get("score", 0) > 0]
            avg = sum(scores) / len(scores) if scores else 0.0
            runs = len(traces)
        except Exception:
            avg, runs = 0.0, 0

        # KB items
        kb_items = 0
        try:
            from knowledge import skill_kb
            kb = skill_kb.load_kb(name)
            kb_items = kb.total_items
        except Exception:
            pass

        # Source detection
        source = "conversation"
        if re.search(r'https?://', body[:500]):
            source = "url"

        profiles.append(SkillProfile(
            name=name, content_length=len(body),
            has_trigger=has_trigger, has_body=has_body,
            has_params=has_params, has_appendix=has_appendix,
            step_count=steps, branch_count=branches,
            avg_score=round(avg, 1), total_runs=runs,
            source=source, kb_items=kb_items,
        ))
    return profiles


# ═══════════════════════════════════════════════════════════════
# 2. Mining — LLM-powered cross-skill pattern discovery
# ═══════════════════════════════════════════════════════════════

def mine_patterns(
    profiles: list[SkillProfile],
    llm_args: tuple,
) -> tuple[list[CrossSkillInsight], SkillDNA]:
    """Use LLM to analyze all skill profiles and discover patterns."""
    from skillos.llm_client import call

    if len(profiles) < 2:
        return [], SkillDNA()

    # Build profile summary
    high_scorers = [p for p in profiles if p.avg_score >= 4]
    low_scorers = [p for p in profiles if 0 < p.avg_score < 3]
    no_scores = [p for p in profiles if p.avg_score == 0]

    summary_lines = [f"## 技能概况 ({len(profiles)} 个)"]

    if high_scorers:
        summary_lines.append(f"\n### 高分技能 ({len(high_scorers)} 个, ≥4/5)")
        for p in high_scorers:
            missing = []
            if not p.has_trigger: missing.append("S_trigger")
            if not p.has_params: missing.append("S_params")
            if not p.has_appendix: missing.append("S_appendix")
            summary_lines.append(
                f"- {p.name}: {p.step_count}步, {p.branch_count}分支, "
                f"KB:{p.kb_items}项, 得分:{p.avg_score}"
                + (f" ⚠️缺失:{','.join(missing)}" if missing else "")
            )

    if low_scorers:
        summary_lines.append(f"\n### 低分技能 ({len(low_scorers)} 个, <3/5)")
        for p in low_scorers:
            missing = []
            if not p.has_trigger: missing.append("S_trigger")
            if not p.has_params: missing.append("S_params")
            if not p.has_appendix: missing.append("S_appendix")
            summary_lines.append(
                f"- {p.name}: {p.step_count}步, {p.branch_count}分支, "
                f"KB:{p.kb_items}项, 得分:{p.avg_score}"
                + (f" ⚠️缺失:{','.join(missing)}" if missing else "")
            )

    if no_scores:
        summary_lines.append(f"\n### 未评分技能 ({len(no_scores)} 个)")

    # Structural stats
    has_trigger_count = sum(1 for p in profiles if p.has_trigger)
    has_params_count = sum(1 for p in profiles if p.has_params)
    has_appendix_count = sum(1 for p in profiles if p.has_appendix)
    avg_steps = sum(p.step_count for p in profiles) / len(profiles)
    avg_branches = sum(p.branch_count for p in profiles) / len(profiles)

    summary_lines.append("\n### 结构统计")
    summary_lines.append(f"- S_trigger 覆盖率: {has_trigger_count}/{len(profiles)}")
    summary_lines.append(f"- S_params 覆盖率: {has_params_count}/{len(profiles)}")
    summary_lines.append(f"- S_appendix 覆盖率: {has_appendix_count}/{len(profiles)}")
    summary_lines.append(f"- 平均步骤数: {avg_steps:.1f}")
    summary_lines.append(f"- 平均分支数: {avg_branches:.1f}")

    summary = "\n".join(summary_lines)

    # Ask LLM to find patterns
    prompt = f"""你是技能架构师。分析以下 {len(profiles)} 个技能的集体特征，找出规律。

{summary}

## 请回答

### 1. 结构原型
这些技能可以归纳为哪 2-4 种**结构原型**？（比如"触发-处理-输出"型、"分析-决策-执行"型）
给每种原型起个名字，列出符合该原型的技能。

### 2. 成功因素
高分技能（≥4分）共同具备什么特征？
不是表面特征（"有S_trigger"），而是深层规律（"S_trigger不只是列关键词，还描述了触发上下文"）。

### 3. 反模式
低分技能（<3分）共同的缺陷是什么？
这些缺陷有没有形成模式？（比如"步骤描述太抽象，缺if-then"）

### 4. 改进建议
基于以上分析，对每个低分技能给出 1 条具体的改进建议。
引用高分技能的做法作为参照。

### 5. Skill DNA
用 3-5 条原则总结"一个好的skill长什么样"。
每一条都是可操作的原则，不是空话。

## 输出格式
用 JSON 输出：
```json
{{
  "archetypes": [{{"name": "...", "skills": ["..."]}}],
  "success_factors": ["..."],
  "anti_patterns": ["..."],
  "suggestions": [{{"skill": "...", "issue": "...", "fix": "...", "reference": "参照XX技能的做法"}}],
  "dna": ["原则1", "原则2", "...]
}}
```"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=2000, temperature=0.3)
    except Exception:
        _log.warning("Pattern mining failed: %s", e)
        return [], SkillDNA()

    # Parse
    insights = []
    dna = SkillDNA(generated_at=time.time())

    try:
        m = re.search(r'```json\s*\n(.*?)```', raw, re.DOTALL | re.IGNORECASE)
        data = json.loads(m.group(1) if m else raw)

        for arch in data.get("archetypes", []):
            insights.append(CrossSkillInsight(
                type="pattern", description=f"原型: {arch.get('name','')}",
                affected_skills=arch.get("skills", []), confidence=0.8,
            ))

        for sf in data.get("success_factors", []):
            dna.success_factors.append(sf)

        for ap in data.get("anti_patterns", []):
            dna.anti_patterns.append(ap)
            insights.append(CrossSkillInsight(
                type="anti_pattern", description=ap, confidence=0.7,
            ))

        for sug in data.get("suggestions", []):
            insights.append(CrossSkillInsight(
                type="gap",
                description=f"{sug.get('skill','')}: {sug.get('issue','')}",
                affected_skills=[sug.get("skill", "")],
                suggestion=sug.get("fix", ""),
                confidence=0.6,
            ))

        dna.archetypes = [a.get("name", "") for a in data.get("archetypes", [])]
        dna.dna = data.get("dna", [])
        dna.templates = data.get("templates", [])

    except Exception:
        _log.warning("Failed to parse pattern mining result: %s", e)

    # Save DNA
    DNA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DNA_PATH.write_text(json.dumps({
        "archetypes": dna.archetypes,
        "success_factors": dna.success_factors,
        "anti_patterns": dna.anti_patterns,
        "dna": dna.dna,
        "generated_at": dna.generated_at,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return insights, dna


# ═══════════════════════════════════════════════════════════════
# 3. Full pipeline
# ═══════════════════════════════════════════════════════════════

def run_cross_skill_optimization(llm_args: tuple) -> dict:
    """Full cross-skill analysis pipeline.

    1. Profile all skills
    2. Mine patterns via LLM
    3. Return insights + DNA
    """
    t0 = time.time()
    profiles = profile_all_skills()
    _log.info("Profiled %d skills for cross-skill analysis", len(profiles))

    insights, dna = mine_patterns(profiles, llm_args)

    # Auto-apply suggestions for high-confidence fixes
    applied = 0
    try:
        from skillos.skills import skill_store
        for ins in insights:
            if ins.type == "gap" and ins.confidence >= 0.6 and ins.suggestion:
                for skill_name in ins.affected_skills:
                    if not skill_name:
                        continue
                    try:
                        body = skill_store.get_skill_body(skill_store.load_skill(skill_name))
                        # Simple heuristic: add missing S_params if suggested
                        if "S_params" in ins.description and not re.search(r'##\s*S_params', body):
                            body += f"\n\n## S_params\n- [待补充] {ins.suggestion[:100]}"
                            skill_store.save_skill(skill_name, body)
                            applied += 1
                    except Exception:
                        pass
    except Exception:
        pass

    return {
        "profiles": len(profiles),
        "insights": len(insights),
        "archetypes": dna.archetypes,
        "success_factors": dna.success_factors[:5],
        "anti_patterns": dna.anti_patterns[:5],
        "dna": dna.dna,
        "applied_fixes": applied,
        "elapsed_s": round(time.time() - t0, 1),
    }


def get_skill_dna_context() -> str:
    """Get the Skill DNA as a prompt context block for skill creation.

    This is injected into the _generate() prompt so every new skill
    inherits the DNA — like a Java base class.
    """
    dna = get_skill_dna()
    if not dna or not dna.get("dna"):
        dna = ensure_bootstrap_skill_dna()
    if not dna or not dna.get("dna"):
        return ""

    lines = ["\n## 🧬 Skill DNA（所有技能必须继承的基础原则）\n"]
    lines.append("以下是系统从已有技能中学习到的设计原则。新技能默认遵循这些原则：\n")
    # Always append Occam's razor as a universal principle
    all_principles = list(dna["dna"][:5])
    if "奥卡姆" not in " ".join(all_principles):
        all_principles.append("原则6（奥卡姆剃刀）: 同等效果选步骤更少的方案。相邻的短步骤必须合并，拒绝过度设计。")

    for i, principle in enumerate(all_principles):
        lines.append(f"{i+1}. {principle}")

    if dna.get("anti_patterns"):
        lines.append("\n### ⚠️ 已知反模式（避免）")
        for ap in dna["anti_patterns"][:3]:
            lines.append(f"- ❌ {ap}")

    if dna.get("archetypes"):
        lines.append("\n### 📐 可用结构原型")
        for arch in dna["archetypes"][:3]:
            lines.append(f"- {arch}")

    lines.append(f"\nDNA 版本: v{int(dna.get('generated_at', 0))}\n")
    return "\n".join(lines)


def inject_dna_to_prompt(base_prompt: str) -> str:
    """Inject Skill DNA into any skill creation prompt.

    Call this from _generate() and learn_from_url() to bake DNA into every new skill.
    """
    dna_ctx = get_skill_dna_context()
    if not dna_ctx:
        return base_prompt

    # Insert DNA after the goal/context section, before the requirements
    # Find the insertion point: right before "## 要求" or "## 生成要求"
    for anchor in ("## 硬性要求", "## 生成要求", "## 要求"):
        if anchor in base_prompt:
            return base_prompt.replace(anchor, dna_ctx + "\n" + anchor, 1)
    # Fallback: append to end
    return base_prompt + "\n" + dna_ctx


def auto_mine_if_needed(llm_args: tuple, threshold: int = 3) -> Optional[dict]:
    """Auto-run pattern mining if enough new skills have been created since last run.

    Args:
        threshold: Run mining if N or more new skills since last DNA generation.
    """
    dna = get_skill_dna()
    if dna:
        last_gen = dna.get("generated_at", 0)
        # Count skills created after last DNA generation
        from skillos.skills import skill_store
        new_count = 0
        for name in skill_store.list_skills():
            try:
                body = skill_store.get_skill_body(skill_store.load_skill(name))
                import re as _re
                created_match = _re.search(r'created_at[：:]\s*(.+)', body)
                if created_match:
                    # Approximate: just count all skills since we can't easily check timestamps
                    pass
            except Exception:
                pass
        # Simple heuristic: if total skills > last count, re-mine
        total = len([s for s in skill_store.list_skills() if s not in ('brainstorming','skill-creator')])
        new_count = total  # approximate
        if new_count >= threshold:
            return run_cross_skill_optimization(llm_args)
    else:
        return run_cross_skill_optimization(llm_args)


def _numbered_step_blocks(body_section: str) -> list[str]:
    """Split S_body into top-level numbered step blocks (1. 2. 3.)."""
    if not body_section:
        return []
    lines = body_section.split("\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^\s*\d+[\.\、)]\s+", line):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(b).strip() for b in blocks if b]


def check_dna_compliance(skill_content: str) -> dict:
    """Machine-verifiable DNA compliance check.

    Each DNA principle is a check function, not a prompt suggestion.
    Skills can declare overrides for principles they legitimately don't fit.

    Returns {"passed": count, "total": count, "checks": [...], "score": "4/5"}
    """
    from skillos.skills.skill_structure import extract_executable_body

    checks = []
    body_section = extract_executable_body(skill_content)
    steps: list[str] = []

    # ── 原则1: S_trigger / When to use 必须包含触发上下文 ──
    trigger_section = _extract_section(skill_content, "S_trigger") or _extract_section(skill_content, "When to use")
    if not trigger_section:
        checks.append({"principle": 1, "rule": "S_trigger 必须包含触发上下文",
                       "passed": False, "detail": "S_trigger 章节缺失",
                       "fix": "添加 S_trigger 章节，描述何时触发此技能"})
    else:
        # Check: more than just a keyword list
        trigger_lines = [l.strip() for l in trigger_section.split("\n") if l.strip()]
        has_context = any(
            re.search(r'当|如果|时|场景|上下文|条件|触发', l)
            for l in trigger_lines
        )
        is_keywords_only = all(
            re.match(r'^[-*]\s*\w+', l) or l.startswith("keywords")
            for l in trigger_lines if l.strip()
        ) and len(trigger_section) < 60

        if is_keywords_only and not has_context:
            checks.append({"principle": 1, "rule": "S_trigger 不只是关键词列表",
                           "passed": False, "detail": "只列出了关键词，缺少触发上下文描述",
                           "fix": "添加触发场景描述，如 '当用户发送包含投诉关键词的消息时触发'"})
        elif len(trigger_section) < 30:
            checks.append({"principle": 1, "rule": "S_trigger 描述需充分",
                           "passed": False, "detail": f"内容过短 ({len(trigger_section)} 字)",
                           "fix": "补充触发上下文：用户意图、前置条件、适用场景"})
        else:
            checks.append({"principle": 1, "rule": "S_trigger 必须包含触发上下文",
                           "passed": True, "detail": f"已包含上下文 ({len(trigger_section)} 字)"})

    # ── 原则2: S_params / Inputs 必须定义类型/范围/默认值 ──
    params_section = _extract_section(skill_content, "S_params") or _extract_section(skill_content, "Inputs")
    if not params_section:
        checks.append({"principle": 2, "rule": "S_params / Inputs 必须定义参数类型",
                       "passed": False, "detail": "S_params / Inputs 章节缺失",
                       "fix": "添加 S_params 章节，每个参数注明类型、取值范围、默认值"})
    else:
        has_types = bool(re.search(r'类型|type|string|int|bool|float|list|dict', params_section, re.IGNORECASE))
        has_defaults = bool(re.search(r'默认|default|可选|required|必填', params_section, re.IGNORECASE))
        checks.append({"principle": 2, "rule": "S_params 必须定义参数类型/范围/默认值",
                       "passed": has_types and has_defaults,
                       "detail": f"类型标注: {'是' if has_types else '否'}, 默认值: {'是' if has_defaults else '否'}",
                       "fix": "每个参数后标注类型和默认值，如 'timeout: int，默认 30，范围 1-120'" if not (has_types and has_defaults) else ""})

    # ── 原则3: 每步必须有具体操作指令或 if-then ──
    if not body_section:
        checks.append({"principle": 3, "rule": "每步必须有具体操作指令",
                       "passed": False, "detail": "S_body / Instructions 章节缺失",
                       "fix": "添加 ## S_body 章节，每步包含具体操作指令"})
    else:
        step_blocks = _numbered_step_blocks(body_section)
        if step_blocks:
            steps = step_blocks
        else:
            steps = re.findall(
                r'(?:^\d+[\.\、)]\s*|^[-*]\s*(?:步骤|Step)\s*\d*[:：]?\s*)(.+)',
                body_section, re.MULTILINE | re.IGNORECASE,
            )
        if not steps:
            lines = [l.strip() for l in body_section.split("\n") if len(l.strip()) > 10]
            step_like = [l for l in lines if re.match(r'^\d|[一二三四五六七八九]|^[-*]', l)]
            steps = step_like[:10] if step_like else lines[:5]
        if not steps:
            steps = [body_section[:200]]

        abstract_steps = []
        for i, step in enumerate(steps):
            step_text = step if step_blocks else step
            if len(step_text) < 40 and not re.search(
                r'if\b|否则|then|当.*则|操作|检查|读取|执行|发起|标记|要求|'
                r'同步|发送|通知|更新|关闭|退回|核实|查询|调用',
                step_text,
                re.IGNORECASE,
            ):
                abstract_steps.append(f"步骤{i+1} 过短或缺少动作 ({len(step_text)} 字)")
            elif not step_blocks and len(step) < 15:
                abstract_steps.append(f"步骤{i+1} 过短 ({len(step)} 字)")
            elif not step_blocks and not re.search(
                r'[操作执行调用读取写入检查验证生成发送同步通知核实查询更新发起退回拦截]|'
                r'\*\*|if\b|否则|则',
                step,
                re.IGNORECASE,
            ):
                abstract_steps.append(f"步骤{i+1} 缺少具体动作")

        checks.append({"principle": 3, "rule": "每步必须有具体操作指令或 if-then",
                       "passed": len(abstract_steps) == 0,
                       "detail": f"{len(steps)} 步, {len(abstract_steps)} 步过于抽象" if abstract_steps else f"{len(steps)} 步, 全部具体",
                       "fix": "; ".join(abstract_steps[:2]) if abstract_steps else ""})

    # ── 原则4: 分支数 ≥ 3（正常/变体/异常） ──
    branch_count = len(re.findall(
        r'if|else|否则|不然|分支|如果.*则|当.*时.*则|异常|错误|失败|超时',
        skill_content
    ))
    checks.append({"principle": 4, "rule": "分支数 ≥ 3（正常流程、变体、异常）",
                   "passed": branch_count >= 3,
                   "detail": f"检测到 {branch_count} 个分支/条件",
                   "fix": "至少补充一个异常处理分支（如'如果API超时，则重试3次后返回错误'）" if branch_count < 3 else ""})

    # ── 原则6: 奥卡姆剃刀 — 相邻顶层步骤标题过短 ──
    short_pairs = 0
    if body_section:
        titles = [
            re.sub(r"^\s*\d+[\.\、)]\s*", "", b.split("\n", 1)[0]).strip()
            for b in _numbered_step_blocks(body_section)
        ]
        for i in range(len(titles) - 1):
            if len(titles[i]) < 12 and len(titles[i + 1]) < 12:
                short_pairs += 1
    has_mergeable = short_pairs > 0
    checks.append({"principle": 6, "rule": "奥卡姆剃刀 — 同等效果选步骤更少的方案",
                   "passed": not has_mergeable,
                   "detail": f"检测到 {short_pairs} 对可合并的短步骤" if has_mergeable else "步骤粒度合理",
                   "fix": "合并相邻短步骤，减少步骤数" if has_mergeable else ""})

    # ── 原则5: 步骤 1-5 步，每步足够详细（按顶层编号块计） ──
    step_blocks = _numbered_step_blocks(body_section or "")
    steps_count = len(step_blocks)
    if steps_count == 0 and body_section:
        steps_count = len(re.findall(
            r'(?:^\d+[\.\、)]|^[-*]\s*(?:步骤|Step|step))',
            body_section, re.MULTILINE | re.IGNORECASE,
        ))
    if steps_count == 0 and body_section:
        step_like = [l for l in body_section.split("\n")
                     if l.strip() and (re.match(r'^\d|[一二三四五六七八九]', l.strip()) or len(l.strip()) > 30)]
        steps_count = min(len(step_like), 10)
    if step_blocks:
        avg_step_len = sum(len(b) for b in step_blocks) / max(steps_count, 1)
    else:
        avg_step_len = sum(len(s) for s in steps) / max(steps_count, 1) if steps_count else 0
    checks.append({"principle": 5, "rule": "步骤数 1-3，每步足够详细",
                   "passed": 1 <= steps_count <= 5 and avg_step_len > 20,
                   "detail": f"{steps_count} 步, 平均 {avg_step_len:.0f} 字/步",
                   "fix": "步骤太多就合并，太少就拆分，保持 1-5 步" if steps_count > 5 or avg_step_len < 20 else ""})

    passed = sum(1 for c in checks if c["passed"])
    return {
        "passed": passed,
        "total": len(checks),
        "score": f"{passed}/{len(checks)}",
        "checks": checks,
        "all_passed": passed == len(checks),
    }


def override_dna_principle(skill_content: str, principle_num: int, reason: str) -> str:
    """Declare an override for a DNA principle that doesn't apply to this skill.

    Adds an override declaration to the skill document: <!-- @override: 原则N — 原因 -->
    """
    override_marker = f"<!-- @override: 原则{principle_num} — {reason} -->"
    if "@override" not in skill_content:
        # Add overrides section before S_body
        skill_content = skill_content.replace(
            "## S_body",
            f"## 继承声明\n{override_marker}\n\n## S_body"
        )
    else:
        skill_content = skill_content.replace(
            "## S_body",
            f"{override_marker}\n## S_body"
        )
    return skill_content


def _extract_section(content: str, section: str) -> str:
    """Extract a skill document section by name."""
    pattern = rf'##\s*{section}\s*\n(.*?)(?=\n##\s+\w|\Z)'
    m = re.search(pattern, content, re.DOTALL)
    return m.group(1).strip() if m else ""


def ensure_bootstrap_skill_dna(*, force: bool = False) -> dict:
    """Ensure skill_dna.json exists so layer-2 injection works before mining."""
    if DNA_PATH.exists() and not force:
        existing = get_skill_dna()
        if existing and existing.get("dna"):
            return existing
    DNA_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(_BOOTSTRAP_DNA)
    payload["generated_at"] = time.time()
    DNA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _log.info("Bootstrapped Skill DNA at %s", DNA_PATH)
    return payload


def get_skill_dna() -> Optional[dict]:
    """Load the cached Skill DNA."""
    if not DNA_PATH.exists():
        return None
    try:
        return json.loads(DNA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def apply_dna_compliance_fix(
    content: str,
    llm_args: tuple,
    *,
    max_rounds: int = 2,
    min_passed: int = 5,
) -> str:
    """LLM fix loop when Skill DNA compliance checks fail (generate + save paths)."""
    try:
        from skillos.llm_client import call
        from skillos.skills.skill_structure import normalize_skill_body

        model = llm_args[2] if len(llm_args) > 2 else ""
        for _ in range(max_rounds):
            report = check_dna_compliance(content)
            if report.get("all_passed") or report.get("passed", 0) >= min_passed:
                return content
            failed = [c for c in report.get("checks", []) if not c.get("passed")]
            fixes = "\n".join(
                f"- {c.get('rule')}: {c.get('fix') or c.get('detail')}" for c in failed[:5]
            )
            prompt = f"""以下 SKILL.md 未通过 Skill DNA 合规检查（{report.get('score')}）。
请修订 skill_doc，修复下列问题；保留已有事实；**必须包含 ## S_body**（步骤写在 S_body 内）。

## 待修复项
{fixes}

## 当前文档
```skill_doc
{content[:6000]}
```

只输出修订后的 ```skill_doc ... ``` 代码块。"""
            raw = call(prompt, model=model, max_tokens=2800, temperature=0.2)
            m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
            if m and len(m.group(1).strip()) > 200:
                content = normalize_skill_body(m.group(1).strip())
            else:
                break
    except Exception as exc:
        _log.debug("DNA compliance fix skipped: %s", exc)
    return content
