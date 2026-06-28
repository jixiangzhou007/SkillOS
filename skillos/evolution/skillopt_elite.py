"""Elite pool management for EvoSkill-style tournament selection.

Maintains a fixed-capacity pool of top-K competing skill versions.
Candidates must beat the weakest member to enter; eliminated candidates
are archived with failure reasons.
"""

import json
import logging

from .skillopt_engine import (
    build_optimizer_prompt,
    build_protection_context,
    identify_protected_regions,
)
from .skillopt_traces import collect_traces
from .skillopt_types import ElitePool, OptimizationSession

_log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Batch Collective Diagnosis (Trace2Skill §Collective Diagnosis)
# ═══════════════════════════════════════════════════════════════

def batch_diagnose(
    skill_name: str,
    skill_content: str,
    traces: list[dict],
    llm_args: tuple,
    min_pattern_occurrence: int = 2,
) -> str:
    """Collective diagnosis across ALL recent traces before proposing edits.

    Trace2Skill's key insight: don't diagnose one trace at a time.
    Look across the full batch — patterns that appear in MULTIPLE traces
    are signal; single-trace anomalies are noise.

    Returns a diagnostic report for the optimizer prompt.
    """
    if len(traces) < 3:
        return ""  # Not enough data for batch diagnosis

    successes = [t for t in traces if t.get("score", 0) >= 4]
    failures = [t for t in traces if 0 < t.get("score", 0) < 3]

    if len(failures) < 2:
        return ""  # Not enough failures to find patterns

    # Build failure summary for LLM
    failure_summary = []
    for t in failures[-10:]:
        failure_summary.append({
            "task": t.get("task", "")[:150],
            "score": t.get("score", 0),
            "root_cause": t.get("failure_root_cause", "")[:120],
            "feedback": t.get("feedback", "")[:150],
        })

    success_tasks = [t.get("task", "")[:100] for t in successes[-5:]]

    from skillos.llm_client import call

    prompt = f"""你是技能故障诊断专家。对以下批量执行轨迹进行**集体诊断**。

## 核心原则（Trace2Skill 方法论）
- 不要把单条轨迹的个例当成通用规则
- 只有在 ≥ {min_pattern_occurrence} 条失败轨迹中**反复出现**的模式，才值得修改 Skill
- 只出现一次的问题 → 噪声，忽略
- 成功轨迹中没出现过的问题 → 可能是用户个例，不是 Skill 缺陷

## 当前技能
```
{skill_content[:1000]}
```

## 成功轨迹（参考基线）
{chr(10).join(f'- {t}' for t in success_tasks) if success_tasks else '（无成功轨迹）'}

## 失败轨迹（需要诊断）
{json.dumps(failure_summary, ensure_ascii=False, indent=2)}

## 诊断步骤
1. **聚类失败模式**：把这些失败按根因归类（同一类问题可能在不同任务中以不同形式出现）
2. **区分信号与噪声**：
   - 信号 = 同一类根因出现在 ≥ {min_pattern_occurrence} 条轨迹中 → 值得改
   - 噪声 = 只出现一次的个例 → 标记为"无需处理"
3. **对照成功轨迹**：成功轨迹中是否也出现过类似场景但处理正确？
   如果是 → 说明 Skill 是对的，是某次执行的偶然失败
   如果否 → 说明 Skill 确实没覆盖这类场景
4. **提出修改建议**：只针对"信号"级别的模式提出修改建议
5. **标记受保护区域**：成功轨迹频繁使用的 Skill 段落 → 建议保护，不要修改

## 输出格式
```
### 诊断报告

#### 🔴 信号级问题（出现在 ≥{min_pattern_occurrence} 条轨迹中，值得修改）
- 问题: <描述> | 出现次数: N | 根因: <归类> | 建议修改: <具体段落>
- ...

#### 🟡 噪声级问题（单次出现，忽略）
- 问题: <描述> | 原因: 为什么判断为噪声
- ...

#### 🟢 受保护区域（成功轨迹验证，禁止修改）
- <段落名>: 在 N 条成功轨迹中被正确使用
- ...
```"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=1000, temperature=0.2)
        return raw.strip()
    except Exception as e:
        _log.warning("Batch diagnosis failed: %s", e)
        return ""


def batch_diagnose_context(
    skill_name: str,
    skill_content: str,
    traces: list[dict],
    llm_args: tuple,
) -> str:
    """Wrapper that returns a formatted context block for the optimizer prompt."""
    report = batch_diagnose(skill_name, skill_content, traces, llm_args)
    if not report:
        return ""

    return f"""\n## 🔬 批量集体诊断（Trace2Skill 方法论）

> 以下诊断基于 {len(traces)} 条批量轨迹的跨轨迹模式分析。
> 只有出现在 ≥2 条独立轨迹中的模式才被认定为"信号"。
> 单次出现的个例标记为"噪声"并忽略。

{report}
"""


# ═══════════════════════════════════════════════════════════════
# Enhanced Optimizer Pipeline (integrating all three methods)
# ═══════════════════════════════════════════════════════════════

def build_enhanced_optimizer_prompt(
    session: OptimizationSession,
    user_feedback: str = "",
    elite_pool: ElitePool | None = None,
    llm_args: tuple | None = None,
) -> str:
    """Build optimizer prompt with ALL three defenses against '创可贴式进化':

    1. Protected Regions (SkillOpt) — core logic is locked
    2. Elite Pool Tournament (EvoSkill) — candidates must fight to survive
    3. Batch Collective Diagnosis (Trace2Skill) — only cross-trace patterns count
    """
    prompt = build_optimizer_prompt(session, user_feedback)

    # Layer 1: Protected Regions
    traces = collect_traces(session.skill_name)
    protected = identify_protected_regions(session.current_content, traces)
    if protected:
        prompt += "\n" + build_protection_context(protected)

    # Layer 2: Batch Diagnosis
    if llm_args and len(traces) >= 3:
        batch_ctx = batch_diagnose_context(
            session.skill_name, session.current_content, traces, llm_args,
        )
        if batch_ctx:
            prompt += "\n" + batch_ctx

    # Layer 3: Elite Pool feedback
    if elite_pool and elite_pool.eliminated:
        prompt += "\n" + elite_pool.get_elimination_feedback()

    # Add the "创可贴式进化" warning
    prompt += """

## ⚠️ 防创可贴式进化原则
1. **不要为个例贴创可贴** — 批量诊断中标记为"噪声"的问题，不要修改
2. **不要碰受保护区域** — 成功率 ≥90% 且零失败关联的段落，一个字符都别改
3. **通用性优先** — 改完后问自己：这个修改能让**大多数**场景受益，还是只解决了一个具体个例？
4. **越改越短是好事** — 能删掉的条件分支比能加上的更有价值
5. **如果批断报告说"无信号级问题"，本轮跳过优化** — 别没事找事改"""

    return prompt
