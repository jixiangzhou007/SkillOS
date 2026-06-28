"""MoE Router & Evolution — Mixture of Experts for Skill Evolution.

Three experts, one gating network:

  Expert A — Trace2Skill (Batch Discovery)
    Best when: many traces, diverse failure patterns, new skill
    Method: collect all traces → collective diagnosis → merge patterns

  Expert B — EvoSkill (Tournament Selection)
    Best when: high score variance, competing approaches, quality filtering
    Method: maintain elite pool → candidates fight to enter → best survive

  Expert C — SkillOpt (Bounded Fine-tuning)
    Best when: stable skill, specific known issues, low variance
    Method: bounded edits → strict gate → protected regions

Gating factors:
  - trace_count: how many execution traces exist
  - score_variance: how much scores fluctuate (high variance = instability)
  - skill_maturity: total runs / time since creation
  - failure_diversity: how many distinct failure root causes
  - has_protected_regions: whether core logic has been identified as stable

Routing modes:
  - "auto": gating network decides (default)
  - "top2_vote": run top-2 experts, take the version with higher validation score
  - "all3_ensemble": run all three, majority vote on each proposed edit
  - "force_<expert>": force a specific expert for debugging
"""

import logging
import re
import time

from .skillopt_elite import batch_diagnose, build_enhanced_optimizer_prompt
from .skillopt_engine import (
    _get_best_score,
    identify_protected_regions,
    run_optimization_round,
)
from .skillopt_gate import validate_skill
from .skillopt_traces import collect_traces
from .skillopt_types import *

_log = logging.getLogger(__name__)


def compute_skill_state(skill_name: str, skill_content: str = "") -> SkillState:
    """Compute the skill state features for the gating network."""
    traces = collect_traces(skill_name)
    scores = [t.get("score", 0) for t in traces if t.get("score", 0) > 0]
    failures = [t for t in traces if 0 < t.get("score", 0) < 3]
    root_causes = set(t.get("failure_root_cause", "")[:40] for t in failures if t.get("failure_root_cause"))

    # Score variance
    mean = sum(scores) / len(scores) if scores else 0.0
    variance = sum((s - mean) ** 2 for s in scores) / len(scores) if scores else 0.0

    # Maturity: how long has this skill existed?
    days = 0.0
    try:
        from skillos.skills import skill_store
        raw = skill_store.load_skill_raw(skill_name)
        created = raw.get("meta", {}).get("created_at", "")
        if created:
            from datetime import datetime
            dt = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            days = (datetime.utcnow() - dt).total_seconds() / 86400
    except Exception:
        pass

    # Protected regions?
    has_protected = False
    if skill_content:
        protected = identify_protected_regions(skill_content, traces)
        has_protected = len(protected) > 0

    return SkillState(
        skill_name=skill_name,
        trace_count=len(traces),
        score_mean=round(mean, 2),
        score_variance=round(variance, 2),
        failure_count=len(failures),
        failure_diversity=len(root_causes),
        total_runs=sum(1 for t in traces),
        days_since_creation=round(days, 1),
        has_protected_regions=has_protected,
    )


def route(state: SkillState, mode: str = "auto") -> RoutingDecision:
    """MoE gating network: which evolution expert should handle this skill?

    This is a heuristic gating function — the "router" in the MoE architecture.
    In production, this could be replaced with a learned classifier.
    """
    # Force mode
    if mode.startswith("force_"):
        expert_name = mode.replace("force_", "").upper()
        for e in EvolutionExpert:
            if e.name == expert_name:
                return RoutingDecision(
                    primary=e, mode=mode, confidence=1.0,
                    reasoning=f"强制路由到 {e.name}",
                )

    # ── Gating Logic ──────────────────────────────────────────
    #
    # Priority order matters: more specific/conservative rules first.
    # Like MoE, the "router" should be biased toward safety for mature skills.

    # Rule 1: Stable skill with protected regions → SkillOpt (don't touch core logic)
    if state.has_protected_regions and state.failure_count <= 3 and state.score_variance < 1.0:
        return RoutingDecision(
            primary=EvolutionExpert.SKILLOPT,
            confidence=0.9,
            reasoning=f"受保护区域已建立 + 低方差({state.score_variance:.1f}) + 失败少({state.failure_count}) → 有界精细调整，核心逻辑焊死不动",
        )

    # Rule 2: High variance + protected regions → EVOSKILL tournament + SKILLOPT gate
    if state.score_variance > 1.5 and state.has_protected_regions:
        return RoutingDecision(
            primary=EvolutionExpert.EVOSKILL,
            secondary=EvolutionExpert.SKILLOPT,
            mode="top2_vote",
            confidence=0.8,
            reasoning=f"高方差({state.score_variance:.1f}) + 已有受保护区域 → EvoSkill打擂探索, SkillOpt验证把关",
        )

    # Rule 3: Many traces + diverse failures, but skill is young → Trace2Skill discovery
    if state.trace_count >= 8 and state.failure_diversity >= 3 and state.days_since_creation < 7:
        if state.score_variance > 1.5:
            return RoutingDecision(
                primary=EvolutionExpert.TRACE2SKILL,
                secondary=EvolutionExpert.EVOSKILL,
                mode="top2_vote",
                confidence=0.85,
                reasoning=f"新技能 + 批量轨迹({state.trace_count}条) + 多样化失败({state.failure_diversity}类) → Trace2Skill主诊, EvoSkill打擂验证",
            )
        return RoutingDecision(
            primary=EvolutionExpert.TRACE2SKILL,
            confidence=0.8,
            reasoning=f"新技能 + 批量轨迹({state.trace_count}条) + 多样化失败({state.failure_diversity}类) → 批量集体诊断最有效",
        )

    # Rule 4: Mature skill (>2 weeks) with accumulating issues → conservative ensemble
    if state.days_since_creation > 14 and state.failure_count >= 3:
        return RoutingDecision(
            primary=EvolutionExpert.SKILLOPT,
            secondary=EvolutionExpert.EVOSKILL,
            mode="top2_vote",
            confidence=0.75,
            reasoning=f"成熟技能({state.days_since_creation:.0f}天) + 累积失败({state.failure_count}) → 保守为主(SkillOpt), 打擂为辅(EvoSkill)",
        )

    # Rule 5: High variance without protected regions → EVOSKILL explore
    if state.score_variance > 1.5:
        return RoutingDecision(
            primary=EvolutionExpert.EVOSKILL,
            confidence=0.7,
            reasoning=f"得分波动大({state.score_variance:.1f}) + 无受保护区域 → 精英池淘汰赛筛选稳定版本",
        )

    # Rule 6: Many traces, diverse failures (older skill without protection) → Trace2Skill
    if state.trace_count >= 8 and state.failure_diversity >= 3:
        return RoutingDecision(
            primary=EvolutionExpert.TRACE2SKILL,
            confidence=0.75,
            reasoning=f"批量轨迹({state.trace_count}条) + 多样化失败({state.failure_diversity}类) → 批量集体诊断",
        )

    # Rule 7: New skill / few traces → collect more first
    if state.trace_count < 5:
        return RoutingDecision(
            primary=EvolutionExpert.TRACE2SKILL,
            confidence=0.6,
            reasoning=f"轨迹不足({state.trace_count}条) → 先攒料，批量诊断，不急于单条改",
        )

    # Default: SkillOpt — safest baseline
    return RoutingDecision(
        primary=EvolutionExpert.SKILLOPT,
        confidence=0.5,
        reasoning="默认路由 → 有界编辑是最安全的基线",
    )


def build_expert_prompt(
    decision: RoutingDecision,
    session: OptimizationSession,
    elite_pool: ElitePool | None,
    llm_args: tuple,
) -> str:
    """Build the optimizer prompt tailored to the selected expert(s).

    Each expert sees different context and has different instructions:
    - Trace2Skill: batch traces, collective patterns, ignore single anomalies
    - EvoSkill: tournament history, version competition, elimination feedback
    - SkillOpt: protected regions, bounded edits, strict gate, learning rate
    """
    if decision.primary == EvolutionExpert.TRACE2SKILL:
        return _build_trace2skill_prompt(session, elite_pool, llm_args)
    elif decision.primary == EvolutionExpert.EVOSKILL:
        return _build_evoskill_prompt(session, elite_pool, llm_args)
    else:
        return _build_skillopt_prompt(session, elite_pool, llm_args)


def _build_trace2skill_prompt(
    session: OptimizationSession,
    elite_pool: ElitePool | None,
    llm_args: tuple,
) -> str:
    """Trace2Skill expert: batch discovery mode.

    Key message: "先看够多，再一次写成。别急着改，先找模式。"
    """
    traces = collect_traces(session.skill_name)
    batch_report = batch_diagnose(
        session.skill_name, session.current_content, traces, llm_args,
        min_pattern_occurrence=2,
    )

    prompt = f"""你是 Trace2Skill 专家——批量轨迹集体诊断器。

## 核心方法论
你的工作是**从批量轨迹中归纳通用模式**，不是修复单个badcase。

原则：
1. 只有出现在 ≥2 条独立轨迹中的模式，才值得写入 Skill
2. 单次出现的个例 → 标记为噪声，**不要为此修改 Skill**
3. 成功轨迹中的做法 → 受保护，不要动
4. 被多个失败轨迹反复验证的改进 → 才写入

## 当前技能
```
{session.current_content[:1500]}
```

{batch_report if batch_report else '（轨迹不足，无法进行批量诊断）'}

## 输出
用 ```skill_doc ... ``` 围栏输出更新后的技能文档。
只改批量诊断中标记为"信号"的部分。不改"噪声"和"受保护区域"。"""

    return prompt


def _build_evoskill_prompt(
    session: OptimizationSession,
    elite_pool: ElitePool | None,
    llm_args: tuple,
) -> str:
    """EvoSkill expert: tournament selection mode.

    Key message: "生成候选版本，让它打擂。赢了才能活下来。"
    """
    elim_feedback = elite_pool.get_elimination_feedback() if elite_pool else ""
    champion_preview = ""
    if elite_pool and elite_pool.champion:
        c = elite_pool.champion
        champion_preview = f"\n## 🏆 当前冠军版本 v{c['version']}\n得分: {c['score']:.1f}\n内容预览: {c['content'][:300]}..."

    prompt = f"""你是 EvoSkill 专家——技能进化擂台赛裁判兼提案者。

## 核心方法论
你生成一个候选版本的 Skill，它必须在验证集上**打赢当前精英池中最弱的版本**。
被淘汰的历史版本和它们的失败原因会喂给你当反面教材。

原则：
1. 参考冠军版本的长处，避免淘汰版本犯过的错误
2. 生成的候选版本不需要是最终版——它可以大胆尝试新结构，打擂输了会被自然淘汰
3. 专注解决高频失败模式，不为个例优化

{champion_preview}
{elim_feedback}

## 当前技能（待改进版本）
```
{session.current_content[:1500]}
```

## 输出
用 ```skill_doc ... ``` 围栏输出候选版本的完整技能文档。
候选版本将进入精英池淘汰赛。只有得分高于池底才能存活。"""

    return prompt


def _build_skillopt_prompt(
    session: OptimizationSession,
    elite_pool: ElitePool | None,
    llm_args: tuple,
) -> str:
    """SkillOpt expert: bounded fine-tuning mode.

    Key message: "小步编辑，验证门控，受保护区域一字符都不许动。"
    """
    # Use the existing enhanced prompt which already has protected regions + batch diagnosis
    return build_enhanced_optimizer_prompt(
        session,
        elite_pool=elite_pool,
        llm_args=llm_args,
    )


# ═══════════════════════════════════════════════════════════════
# Top-level API: one call to rule them all
# ═══════════════════════════════════════════════════════════════

def evolve_with_moe(
    skill_name: str,
    skill_content: str,
    llm_args: tuple,
    *,
    mode: str = "auto",
    elite_pool: ElitePool | None = None,
    user_feedback: str = "",
) -> dict:
    """The single entry point for skill evolution — MoE routing + execution.

    1. Compute skill state (features for gating)
    2. Route to the right expert(s) via MoE gating network
    3. Execute the expert's optimization strategy
    4. If top2_vote or all3_ensemble mode, run multiple experts and pick best

    Returns:
        {
            "skill_name": str,
            "routing": RoutingDecision,
            "state": SkillState,
            "result": OptimizationRound or dict with ensemble results,
            "elapsed_s": float,
        }
    """
    t_start = time.time()

    # 1. Compute state
    state = compute_skill_state(skill_name, skill_content)

    # 2. Route
    decision = route(state, mode)

    # 3. Create session
    session = OptimizationSession(
        skill_name=skill_name,
        original_content=skill_content,
        current_content=skill_content,
    )

    # Initialize elite pool if not provided
    if elite_pool is None:
        elite_pool = ElitePool(skill_name=skill_name)

    # 4. Execute
    if decision.mode == "top2_vote" and decision.secondary:
        # Run primary and secondary, pick the one with higher validation score
        primary_result = run_optimization_round(session, llm_args, user_feedback)
        secondary_session = OptimizationSession(
            skill_name=skill_name,
            original_content=skill_content,
            current_content=skill_content,
        )
        secondary_result = _run_expert_round(
            decision.secondary, secondary_session, elite_pool, llm_args, user_feedback
        )

        primary_score = primary_result.get("new_score", 0)
        secondary_score = secondary_result.get("new_score", 0)

        winner = "primary" if primary_score >= secondary_score else "secondary"
        winner_result = primary_result if winner == "primary" else secondary_result

        return {
            "skill_name": skill_name,
            "routing": decision,
            "state": state,
            "mode": "top2_vote",
            "winner": f"{winner} ({decision.primary.name if winner == 'primary' else decision.secondary.name})",
            "primary_score": primary_score,
            "secondary_score": secondary_score,
            "result": winner_result,
            "elapsed_s": round(time.time() - t_start, 1),
        }

    # Single expert
    result = _run_expert_round(
        decision.primary, session, elite_pool, llm_args, user_feedback,
    )

    return {
        "skill_name": skill_name,
        "routing": decision,
        "state": state,
        "mode": decision.mode,
        "result": result,
        "elapsed_s": round(time.time() - t_start, 1),
    }


def _run_expert_round(
    expert: EvolutionExpert,
    session: OptimizationSession,
    elite_pool: ElitePool,
    llm_args: tuple,
    user_feedback: str = "",
) -> dict:
    """Run one optimization round with a specific expert."""
    if expert == EvolutionExpert.TRACE2SKILL:
        prompt = _build_trace2skill_prompt(session, elite_pool, llm_args)
    elif expert == EvolutionExpert.EVOSKILL:
        prompt = _build_evoskill_prompt(session, elite_pool, llm_args)
    else:
        prompt = _build_skillopt_prompt(session, elite_pool, llm_args)

    # Generate improved version
    api_key, base_url, model, chat_kwargs = llm_args
    try:
        from skillos.llm_client import call
        raw = call(prompt, model=model, max_tokens=2000, temperature=0.3)
    except Exception as e:
        return {"error": str(e), "expert": expert.name}

    m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    new_content = m.group(1).strip() if m else raw.strip()

    # Validate
    old_score = _get_best_score(session.skill_name)
    new_score, cross_scores = validate_skill(
        session.skill_name, new_content, [], llm_args,
        cross_model=session.config.cross_model_enabled,
        fast_model=session.config.fast_model,
    )

    # Elite pool nomination (for EvoSkill and top2_vote modes)
    version = session.round_num + 1
    entered, reason = elite_pool.nominate(new_content, new_score, version)

    return {
        "expert": expert.name,
        "old_score": old_score,
        "new_score": new_score,
        "cross_model_scores": cross_scores,
        "improved": new_score > old_score,
        "elite_pool_entered": entered,
        "elite_pool_reason": reason,
        "content": new_content if new_score > old_score else session.current_content,
    }
