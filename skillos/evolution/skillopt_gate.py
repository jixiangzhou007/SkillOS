"""Validation gating for SkillOpt.

SkillOpt's key defense against quality regression: validate proposed edits
on held-out traces before accepting them into the skill document.
"""

import logging

from .skillopt_types import EditProposal, OptimizationSession

_log = logging.getLogger(__name__)


def validate_skill(
    skill_name: str,
    skill_content: str,
    val_traces: list[dict],
    llm_args: tuple,
    *,
    cross_model: bool = False,
    fast_model: str = "",
) -> tuple[float, dict[str, float]]:
    """Run the skill on validation tasks and return scores.

    Args:
        skill_content: The skill document to test.
        val_traces: Held-out validation tasks (if empty, uses a default test).
        llm_args: (api_key, base_url, model, chat_kwargs) for the main model.
        cross_model: Whether to also test on a cheaper model.
        fast_model: The cheaper model name for cross-model validation.

    Returns:
        (main_score, {model_name: score, ...})
    """
    from skillos.evolution.evolver import record_trace
    from skillos.skills import agent_factory

    test_tasks = []
    if val_traces:
        test_tasks = [t.get("task", f"Execute {skill_name}") for t in val_traces[:3]]
    if not test_tasks:
        test_tasks = [f"请按照技能「{skill_name}」的要求执行任务"]

    scores: dict[str, float] = {}
    model_scores: dict[str, float] = {}

    for task in test_tasks[:2]:  # max 2 validation tasks
        try:
            agent = agent_factory.create_agent(skill_content, task)
            result = agent_factory.run_agent(agent, task)
            trace = record_trace(skill_name, task, result, 0, llm_args)
            scores[task[:40]] = trace.judge_score
        except Exception as e:
            _log.warning("Validation task failed: %s", e)
            scores[task[:40]] = 0

    main_score = sum(scores.values()) / len(scores) if scores else 0.0
    model_scores["main"] = main_score

    # Cross-model validation (SkillOpt §7: cross-model migration)
    if cross_model and fast_model and llm_args:
        api_key, base_url, _, chat_kwargs = llm_args
        fast_llm_args = (api_key, base_url, fast_model, chat_kwargs)
        for task in test_tasks[:1]:  # 1 task on fast model
            try:
                agent = agent_factory.create_agent(skill_content, task)
                result = agent_factory.run_agent(agent, task)
                trace = record_trace(
                    f"{skill_name}_fast", task, result, 0, fast_llm_args
                )
                model_scores[fast_model] = float(trace.judge_score)
            except Exception as e:
                _log.warning("Cross-model validation failed: %s", e)

    return main_score, model_scores


def update_meta_skill(
    session: OptimizationSession,
    accepted_edits: list[EditProposal],
) -> str:
    """Update the meta-skill with stable patterns from accepted edits.

    Meta-skill only sees the optimizer (not deployed with the final skill).
    It captures cross-round patterns: what kinds of edits consistently help.
    """
    if not session.config.meta_enabled:
        return ""

    # Extract patterns from accepted edits
    patterns = []
    for edit in accepted_edits:
        if edit.reason:
            patterns.append(f"- {edit.edit_type} [{edit.target}]: {edit.reason[:120]}")

    if not patterns:
        return session.meta_skill

    new_meta = f"## 第 {session.round_num} 轮稳定模式\n" + "\n".join(patterns)

    if session.meta_skill:
        # Append to existing meta, keeping it compact
        combined = session.meta_skill + "\n\n" + new_meta
        if len(combined) > session.config.meta_skill_max_len * 2:
            # Trim oldest rounds
            parts = combined.split("\n\n## 第 ")
            combined = parts[0] + "\n\n## 第 " + "\n\n## 第 ".join(parts[-(session.round_num):])
        session.meta_skill = combined[: session.config.meta_skill_max_len * 2]
    else:
        session.meta_skill = new_meta

    return session.meta_skill


def rejection_buffer_update(
    session: OptimizationSession,
    rejected_edits: list[EditProposal],
) -> str:
    """Update the rejection buffer with failed edit patterns.

    These become negative feedback for the next round.
    """
    for edit in rejected_edits[:3]:
        entry = f"❌ 拒绝: {edit.edit_type} [{edit.target}] — {edit.reason[:100]}"
        session.rejection_buffer.append(entry)

    # Keep buffer bounded
    if len(session.rejection_buffer) > 10:
        session.rejection_buffer = session.rejection_buffer[-8:]

    return "\n".join(session.rejection_buffer[-5:]) if session.rejection_buffer else ""
