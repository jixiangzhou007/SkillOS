"""Optimization engine for SkillOpt.

The core optimization pipeline: build prompts with context, execute rounds,
validate results, identify protected regions.
"""

import logging
import re
import time

from .skillopt_audit import audit_skill
from .skillopt_gate import rejection_buffer_update, update_meta_skill, validate_skill
from .skillopt_traces import analyze_traces, collect_traces, split_traces
from .skillopt_types import *

_log = logging.getLogger(__name__)


def build_optimizer_prompt(
    session: OptimizationSession,
    user_feedback: str = "",
) -> str:
    """Build the optimizer prompt for the current optimization round.

    Incorporates: trajectory analysis, rejection buffer, meta-skill,
    edit budget with decay, and cross-model validation context.
    """
    config = session.config
    budget = session.edit_budget_for_round()

    # Collect and analyze traces
    traces = collect_traces(session.skill_name)
    train_traces, val_traces = split_traces(traces, config)
    trace_analysis = analyze_traces(train_traces)

    # Rejection buffer context
    rej_ctx = ""
    if session.rejection_buffer:
        rej_ctx = "\n## ⛔ 之前被拒绝的编辑（不要重复尝试）\n"
        rej_ctx += "\n".join(f"- {r}" for r in session.rejection_buffer[-5:]) + "\n"

    # Meta-skill context
    meta_ctx = ""
    if session.meta_skill:
        meta_ctx = "\n## 🧠 元技能（跨轮稳定的优化模式，供参考）\n"
        meta_ctx += session.meta_skill[:config.meta_skill_max_len] + "\n"

    budget_hint = (
        f"当前是第 {session.round_num} 轮优化，编辑预算 = {budget}（上限）。"
        f"每多一轮，预算递减 1，迫使你聚焦最重要的改进。"
    )

    return f"""你是技能优化器。你需要对「{session.skill_name}」做小步、可验证、有界编辑。

## 📐 优化原则（SkillOpt 方法论）
1. 目标模型冻结不动 — 只改技能文档
2. 小步编辑 — 每轮编辑预算 ≤ {budget}，只改最有影响的几处
3. 轨迹驱动 — 基于实际执行反馈找改进点，不凭空猜测
4. 验证门 — 改了之后必须在测试任务上跑分，不提升就拒绝

{meta_ctx}
{rej_ctx}
{trace_analysis}

## ✂️ 当前技能文档
```
{session.current_content[:1200]}
```

## 📝 本轮约束
- {budget_hint}
- 编辑类型: + add（补充缺失）/ - delete（删除错误）/ ~ replace（修正不准确）
- 每条编辑标注原因，引用具体轨迹或用户反馈
- 不改已验证正确的内容（成功案例覆盖的部分）
{user_feedback}

## 输出
用 ```skill_doc ... ``` 围栏输出更新后的完整技能文档。在文档末尾用 `<!-- edits: ... -->` 标注本轮的编辑清单。"""


def run_optimization_round(
    session: OptimizationSession,
    llm_args: tuple,
    user_feedback: str = "",
) -> dict:
    """Execute one full round of SkillOpt optimization.

    1. Build optimizer prompt with full context
    2. Generate improved skill via LLM
    3. Validate on held-out traces
    4. Update meta-skill and rejection buffer
    5. Return results

    Returns a dict suitable for the API response.
    """
    t_start = time.time()
    round_num = session.round_num + 1
    budget = session.edit_budget_for_round()

    # 1. Generate improved skill
    prompt = build_optimizer_prompt(session, user_feedback)
    api_key, base_url, model, chat_kwargs = llm_args

    try:
        from skillos.llm_client import call
        raw = call(prompt, model=model, max_tokens=2000, temperature=0.3)
    except Exception as e:
        _log.error("Optimizer LLM call failed: %s", e)
        return {"error": str(e), "round": round_num}

    # Extract skill_doc
    m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    new_content = m.group(1).strip() if m else raw.strip()

    # 2. Validate on held-out traces
    traces = collect_traces(session.skill_name)
    _, val_traces = split_traces(traces, session.config)

    old_score = _get_best_score(session.skill_name)
    new_score, cross_scores = validate_skill(
        session.skill_name, new_content, val_traces, llm_args,
        cross_model=session.config.cross_model_enabled,
        fast_model=session.config.fast_model,
    )

    # 3. Independent Auditor (SkillEvolver-inspired)
    audit_report = audit_skill(new_content, session.skill_name, llm_args)

    # 4. Create round record
    opt_round = OptimizationRound(
        round_num=round_num,
        edit_budget=budget,
        old_score=old_score,
        new_score=new_score,
        cross_model_scores=cross_scores,
    )

    # 5. Validation gate + Auditor gate
    if session.config.strict_gate and old_score > 0:
        if new_score > old_score:
            # Validation passed — now check Auditor
            if audit_report.score < 50:
                opt_round.gate_result = "rejected"
                session.rounds.append(opt_round)
                rejection_buffer_update(session, [])
                return {
                    "accepted": False,
                    "round": round_num,
                    "old_score": old_score,
                    "new_score": new_score,
                    "budget": budget,
                    "cross_model_scores": cross_scores,
                    "audit": {"score": audit_report.score, "summary": audit_report.summary},
                    "reason": f"审计不通过 (得分 {audit_report.score}/100): {audit_report.summary}",
                    "elapsed_s": time.time() - t_start,
                }
            opt_round.gate_result = "accepted"
            session.current_content = new_content
            session.rounds.append(opt_round)
            update_meta_skill(session, [])
        else:
            opt_round.gate_result = "rejected"
            session.rounds.append(opt_round)
            rejection_buffer_update(session, [])
            return {
                "accepted": False,
                "round": round_num,
                "old_score": old_score,
                "new_score": new_score,
                "budget": budget,
                "cross_model_scores": cross_scores,
                "reason": f"验证门拒绝: {old_score:.1f} → {new_score:.1f}，未提升",
                "elapsed_s": time.time() - t_start,
            }
    else:
        # Auditor warning even when gate is skipped
        if audit_report.score < 70:
            _log.warning("Auditor warning (gate skipped): skill=%s score=%d",
                        session.skill_name, audit_report.score)
        opt_round.gate_result = "skipped"
        session.current_content = new_content
        session.rounds.append(opt_round)

    return {
        "accepted": opt_round.gate_result != "rejected",
        "round": round_num,
        "old_score": old_score,
        "new_score": new_score,
        "budget": budget,
        "cross_model_scores": cross_scores,
        "audit": {"score": audit_report.score, "passed": audit_report.passed,
                  "checks": [{"check": c["check"], "severity": c["severity"]}
                            for c in audit_report.checks]},
        "gate": opt_round.gate_result,
        "content": new_content if opt_round.gate_result != "rejected" else session.current_content,
        "elapsed_s": time.time() - t_start,
    }


def _get_best_score(skill_name: str) -> float:
    """Get the best historical score for a skill."""
    traces = collect_traces(skill_name)
    if not traces:
        return 0.0
    scores = [t.get("score", 0) for t in traces if t.get("score", 0) > 0]
    return max(scores) if scores else 0.0


# ═══════════════════════════════════════════════════════════════
# Protected Regions (SkillOpt §Momentum — "核心逻辑焊死")
# ═══════════════════════════════════════════════════════════════

def identify_protected_regions(
    skill_content: str,
    traces: list[dict],
    min_success_rate: float = 0.9,
) -> list[dict]:
    """Identify sections of the skill that have consistently produced good results.

    These sections should be PROTECTED from edits during optimization —
    they are the "core logic" that has been battle-tested.

    Strategy:
    1. Parse skill into sections (## S_trigger, ## S_body, ## S_params, etc.)
    2. For each section, check: across all SUCCESSFUL traces, was this section
       involved in the success? (heuristic: section keywords appear in successful task descriptions)
    3. Sections with high success association AND zero failure association are marked protected.

    Returns list of {section_name, protection_level, reason}.
    """
    sections = _parse_skill_sections(skill_content)
    if not sections:
        return []

    successes = [t for t in traces if t.get("score", 0) >= 4]
    failures = [t for t in traces if 0 < t.get("score", 0) < 3]

    if len(successes) < 2:
        return []  # Not enough data to identify stable regions

    protected = []
    for sec in sections:
        sec_name = sec["name"]
        sec_text = sec["content"][:200]

        # Heuristic: extract key terms from section
        terms = set(re.findall(r'[\w一-鿿]{3,}', sec_text))

        # Count how many successful traces involve this section's terms
        success_hits = 0
        for t in successes:
            task = t.get("task", "")
            if any(term in task for term in terms):
                success_hits += 1

        # Count how many failed traces involve this section's terms
        failure_hits = 0
        for t in failures:
            task = t.get("task", "")
            root_cause = t.get("failure_root_cause", "")
            combined = task + " " + root_cause
            if any(term in combined for term in terms):
                failure_hits += 1

        success_rate = success_hits / max(len(successes), 1)
        failure_rate = failure_hits / max(len(failures), 1) if failures else 0

        if success_rate >= min_success_rate and failure_rate == 0:
            protected.append({
                "section": sec_name,
                "protection": "high",
                "reason": f"成功率 {success_rate:.0%}，零关联失败 ({success_hits}/{len(successes)} 条成功轨迹涉及此区域)",
                "preview": sec_text[:120],
            })
        elif success_rate >= 0.7 and failure_rate < 0.2:
            protected.append({
                "section": sec_name,
                "protection": "medium",
                "reason": f"成功率 {success_rate:.0%}，低关联失败 ({failure_hits}/{len(failures)} 条)",
                "preview": sec_text[:120],
            })

    return protected


def _parse_skill_sections(content: str) -> list[dict]:
    """Parse a skill document into named sections."""
    sections = []
    current_name = "header"
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            if current_lines:
                sections.append({
                    "name": current_name,
                    "content": "\n".join(current_lines).strip(),
                })
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "name": current_name,
            "content": "\n".join(current_lines).strip(),
        })

    return sections


def build_protection_context(protected: list[dict]) -> str:
    """Build the protected regions context for the optimizer prompt."""
    if not protected:
        return ""

    high = [p for p in protected if p["protection"] == "high"]
    medium = [p for p in protected if p["protection"] == "medium"]

    lines = ["\n## 🛡️ 受保护区域（禁止修改）\n"]
    lines.append("以下区域经过大量成功轨迹验证，核心逻辑已经稳定。**严禁修改这些区域**——只改有问题的部分。\n")

    if high:
        lines.append("### 🔒 高保护（零失败关联）")
        for p in high:
            lines.append(f"- **{p['section']}**: {p['reason']}")
            lines.append(f"  > {p['preview'][:100]}...")
        lines.append("")

    if medium:
        lines.append("### 🔐 中保护（低失败关联）")
        for p in medium:
            lines.append(f"- **{p['section']}**: {p['reason']}")
        lines.append("")

    lines.append("⚠️ 违反保护规则的编辑将被自动拒绝。\n")
    return "\n".join(lines)
