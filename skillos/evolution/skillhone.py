"""SkillHone — Persistent Decision History + Targeted Rollback + Role Isolation.

Inspired by Tencent's SkillHone (arXiv:2606.08671) and SGDR (arXiv:2606.04391).

Four enhancements:
  1. Decision History — WHY chain, not just WHAT changed
  2. Targeted Rollback — fix only regressed sections, keep good edits
  3. Role Isolation — structural separation between optimizer and evaluator
  4. State-Grounded Retrieval — dual-signal knowledge search
"""


import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 1. Persistent Decision History
# ═══════════════════════════════════════════════════════════════

@dataclass
class DecisionRecord:
    """A single decision in the skill's evolution history.

    SkillHone's 4-tuple: (diagnosis, candidate_revisions, evaluation_evidence, outcome)
    This is NOT a version diff — it records WHY the change was made.
    """

    record_id: str = ""              # unique id: dec_<timestamp>_<hash>
    skill_name: str = ""
    version_from: int = 0
    version_to: int = 0
    round_num: int = 0

    # The 4-tuple
    diagnosis: str = ""              # what problem was identified?
    candidate_revisions: list[dict] = field(default_factory=list)
    # [{type: add|delete|replace, target: section, old: ..., new: ..., reason: ...}]
    evaluation_evidence: dict = field(default_factory=dict)
    # {execution_score, audit_score, cross_model_scores, dimension_deltas}
    outcome: str = ""                # accepted | rejected | partially_accepted
    outcome_detail: str = ""         # why this outcome?

    # Rejected alternatives (important for future agents)
    rejected_alternatives: list[str] = field(default_factory=list)
    # ["tried increasing threshold but it broke edge cases", ...]

    # Environmental context (why this decision might not apply later)
    context: dict = field(default_factory=dict)
    # {model_used, timestamp, test_tasks_count, protected_regions}

    created_at: float = 0.0


def _decisions_path(skill_name: str) -> Path:
    from skillos.skills import skill_store
    safe = re.sub(r'[<>:"/\\|?*]', '_', skill_name)[:64]
    return Path(skill_store.SKILLS_DIR) / safe / "decisions.jsonl"


def record_decision(record: DecisionRecord) -> str:
    """Persist a decision record to the skill's decision history."""
    if not record.record_id:
        record.record_id = f"dec_{int(time.time())}_{hash(record.diagnosis[:50]) % 10000:04d}"
    if not record.created_at:
        record.created_at = time.time()

    path = _decisions_path(record.skill_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "record_id": record.record_id,
        "skill_name": record.skill_name,
        "version_from": record.version_from,
        "version_to": record.version_to,
        "round_num": record.round_num,
        "diagnosis": record.diagnosis,
        "candidate_revisions": record.candidate_revisions,
        "evaluation_evidence": record.evaluation_evidence,
        "outcome": record.outcome,
        "outcome_detail": record.outcome_detail,
        "rejected_alternatives": record.rejected_alternatives,
        "context": record.context,
        "created_at": record.created_at,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    _log.info("Decision recorded: %s v%d→v%d outcome=%s",
              record.skill_name, record.version_from, record.version_to, record.outcome)
    return record.record_id


def load_decisions(skill_name: str, limit: int = 20) -> list[dict]:
    """Load decision history for a skill."""
    path = _decisions_path(skill_name)
    if not path.exists():
        return []

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records[-limit:]


def build_decision_context(skill_name: str, max_records: int = 5) -> str:
    """Build a context string from recent decisions for the optimizer.

    This is the "memory" that prevents repeating past mistakes.
    Future optimization agents can read this to understand:
    - What was tried before
    - What worked and what didn't
    - Why certain alternatives were rejected
    """
    records = load_decisions(skill_name, max_records)
    if not records:
        return ""

    lines = ["\n## 🧠 决策历史 (SkillHone Persistent Decision History)\n"]
    lines.append("以下是此技能的历史修改决策。阅读后再提案，避免重复试错。\n")

    for r in reversed(records):
        outcome_icon = {"accepted": "✅", "rejected": "❌", "partially_accepted": "⚠️"}.get(
            r.get("outcome", ""), "❓"
        )
        lines.append(f"### {outcome_icon} Round {r['round_num']} — v{r['version_from']}→v{r['version_to']}")
        lines.append(f"**诊断**: {r.get('diagnosis', '')[:200]}")
        lines.append(f"**结果**: {r.get('outcome_detail', '')[:150]}")

        revisions = r.get("candidate_revisions", [])
        if revisions:
            lines.append(f"**修改 ({len(revisions)} 处)**:")
            for rev in revisions[:3]:
                lines.append(f"  - {rev.get('type', '?')} [{rev.get('target', '?')}]: {rev.get('reason', '')[:120]}")

        rejected = r.get("rejected_alternatives", [])
        if rejected:
            lines.append("**被拒绝的方案**:")
            for alt in rejected[:3]:
                lines.append(f"  - ❌ {alt[:150]}")

        evaluation = r.get("evaluation_evidence", {})
        if evaluation:
            exec_s = evaluation.get("execution_score", "?")
            audit_s = evaluation.get("audit_score", "?")
            lines.append(f"**评估**: 执行分={exec_s}, 审计分={audit_s}")

        lines.append("")

    return "\n".join(lines)


def query_decision_history(
    skill_name: str,
    question: str,
    llm_args: tuple,
) -> str:
    """Query the decision history with a natural language question.

    Example: "Has anyone tried increasing the threshold before?"
    The LLM reads the decision history and answers based on it.
    """
    records = load_decisions(skill_name, 20)
    if not records:
        return "（无决策历史记录）"

    history_text = json.dumps(records, ensure_ascii=False, indent=2)
    from skillos.llm_client import call

    prompt = f"""你是技能决策历史的查询助手。基于以下历史记录回答问题。

## 决策历史
```
{history_text[:3000]}
```

## 问题
{question}

## 要求
- 如果历史记录中有相关信息，引用具体的 round 号和决策
- 如果没有相关信息，明确说"历史记录中未找到相关信息"
- 回答简洁，不超过 3 句话"""

    try:
        return call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=300, temperature=0.1)
    except Exception:
        return "查询决策历史失败"


# ═══════════════════════════════════════════════════════════════
# 2. Targeted Rollback
# ═══════════════════════════════════════════════════════════════

@dataclass
class SectionDiff:
    """Per-section diff between two skill versions."""
    section: str          # S_trigger, S_body.步骤1, S_params, etc.
    status: str           # added | removed | modified | unchanged
    old_text: str = ""
    new_text: str = ""
    dimension_impact: list[str] = field(default_factory=list)
    # Which evaluation dimensions does this section affect?
    # e.g., ["trigger_coverage"], ["step_completeness", "param_clarity"]


def compute_section_diff(old_content: str, new_content: str) -> list[SectionDiff]:
    """Compute per-section diff between two skill versions."""
    old_sections = _parse_sections(old_content)
    new_sections = _parse_sections(new_content)

    all_section_names = sorted(set(list(old_sections.keys()) + list(new_sections.keys())))
    diffs = []

    for name in all_section_names:
        old_text = old_sections.get(name, "")
        new_text = new_sections.get(name, "")

        if not old_text and new_text:
            diffs.append(SectionDiff(section=name, status="added", new_text=new_text,
                                     dimension_impact=_section_dimensions(name)))
        elif old_text and not new_text:
            diffs.append(SectionDiff(section=name, status="removed", old_text=old_text,
                                     dimension_impact=_section_dimensions(name)))
        elif old_text != new_text:
            diffs.append(SectionDiff(section=name, status="modified",
                                     old_text=old_text, new_text=new_text,
                                     dimension_impact=_section_dimensions(name)))
        else:
            diffs.append(SectionDiff(section=name, status="unchanged"))

    return diffs


def _parse_sections(content: str) -> dict[str, str]:
    """Parse skill content into named sections."""
    sections = {}
    current_name = "header"
    current_lines = []

    for line in content.split("\n"):
        if re.match(r'^##\s+\S', line):
            if current_lines:
                sections[current_name] = "\n".join(current_lines).strip()
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_name] = "\n".join(current_lines).strip()

    return sections


def _section_dimensions(section_name: str) -> list[str]:
    """Map section names to evaluation dimensions they affect."""
    mapping = {
        "S_trigger": ["trigger_coverage", "entry_visibility", "description_quality"],
        "S_route": ["entry_visibility", "decision_table"],
        "S_body": ["step_completeness", "silent_bypass", "overfitting"],
        "S_params": ["param_abstraction", "hardcoded_constants"],
        "S_appendix": ["self_contained"],
    }
    for key, dims in mapping.items():
        if key in section_name:
            return dims
    return ["step_completeness"]  # default


def targeted_rollback(
    current_content: str,
    previous_content: str,
    regressed_dimensions: list[str],
) -> str:
    """Selectively revert only sections that caused regression.

    Instead of rejecting the entire new version (whole-accept/reject),
    keep the sections whose dimensions improved and revert only those
    whose dimensions regressed.

    Returns the rolled-back content.
    """
    diffs = compute_section_diff(previous_content, current_content)
    old_sections = _parse_sections(previous_content)
    new_sections = _parse_sections(current_content)

    # Build result: start from new content, revert only regressed sections
    result_sections = dict(new_sections)  # copy

    reverted = []
    kept = []

    for diff in diffs:
        if diff.status == "unchanged" or diff.status == "removed":
            continue

        # Check if any of this section's dimensions regressed
        section_regressed = any(d in regressed_dimensions for d in diff.dimension_impact)

        if section_regressed and diff.status in ("modified", "added"):
            # Revert this section to old version
            if diff.section in old_sections:
                result_sections[diff.section] = old_sections[diff.section]
                reverted.append(diff.section)
            elif diff.status == "added":
                # Remove the newly added section entirely
                result_sections.pop(diff.section, None)
                reverted.append(diff.section)
        else:
            kept.append(diff.section)

    _log.info("Targeted rollback: reverted=%s, kept=%s", reverted, kept)

    # Rebuild content in original section order
    section_order = list(new_sections.keys())
    lines = []
    for name in section_order:
        if name in result_sections and result_sections[name]:
            lines.append(f"## {name}")
            lines.append(result_sections[name])
            lines.append("")

    return "\n".join(lines).strip()


# ═══════════════════════════════════════════════════════════════
# 3. Role Isolation
# ═══════════════════════════════════════════════════════════════

def isolated_optimize(
    skill_name: str,
    skill_content: str,
    trace_analysis: str,          # sanitized — no raw test data, no scores
    llm_args: tuple,
    *,
    edit_budget: int = 3,
    decision_context: str = "",
    protected_context: str = "",
) -> tuple[str, list[dict]]:
    """Role: OPTIMIZER — proposes edits based on sanitized analysis.

    The optimizer CANNOT see:
    - Raw test tasks or their answers
    - The exact scoring function
    - The evaluator's internal reasoning

    It CAN see:
    - Sanitized trace analysis (aggregated patterns, no individual scores)
    - Decision history (past WHAT and WHY)
    - Protected regions (what NOT to touch)
    """
    from skillos.llm_client import call

    prompt = f"""你是技能优化器（OPTIMIZER 角色）。你的职责是**提出编辑方案**，不是评估。

## 权限边界
- ✅ 你可以看到：故障模式摘要、决策历史、受保护区域、当前技能文档
- ❌ 你不能看到：具体测试题、评分器、评估端的私有推理
- ⚠️ 你的输出会被独立的评估器（EVALUATOR）验证，不要试图"猜答案"

## 当前技能
```
{skill_content[:1500]}
```

{decision_context}
{protected_context}

## 故障分析（脱敏报告 — 只有聚合模式，无单独得分）
{trace_analysis}

## 约束
- 编辑预算: ≤ {edit_budget} 处修改
- 不改受保护区域
- 每条编辑标注原因，引用具体故障模式
- 如果决策历史显示某个方案已被否决，不要重复尝试

## 输出格式
用 ```skill_doc ... ``` 围栏输出改进后的完整技能文档。
文档末尾用 HTML 注释标注编辑清单:
<!-- edits:
+ add [区域]: 原因
~ modify [区域]: 原因
- delete [区域]: 原因
-->"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=2000, temperature=0.2)
    except Exception as e:
        _log.error("Optimizer LLM call failed: %s", e)
        return skill_content, []

    # Extract skill doc
    m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    new_content = m.group(1).strip() if m else raw.strip()

    # Extract edit list
    edits = []
    edit_m = re.search(r'<!--\s*edits:\s*\n(.*?)\n\s*-->', raw, re.DOTALL | re.IGNORECASE)
    if edit_m:
        for line in edit_m.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith(("+", "~", "-")):
                parts = line.split(":", 1)
                edits.append({"raw": line, "type": line[0], "detail": parts[1].strip() if len(parts) > 1 else ""})

    return new_content, edits


def isolated_evaluate(
    skill_content: str,
    skill_name: str,
    test_tasks: list[str],
    llm_args: tuple,
) -> dict:
    """Role: EVALUATOR — runs tests and scores, cannot modify the skill.

    The evaluator CANNOT see:
    - The optimizer's reasoning or edit proposals
    - Decision history (to avoid bias)
    - Previous versions (evaluates the current version in isolation)

    It CAN see:
    - The skill document
    - Test tasks (with answers if available)
    - The scoring rubric
    """
    from skillos.evolution.skillopt import audit_skill, run_fresh_agent_battery

    # Fresh-agent execution test
    exec_result = run_fresh_agent_battery(skill_content, skill_name, test_tasks, llm_args)
    invocation_rate = exec_result.get("invocation_rate", 0)
    avg_exec_score = exec_result.get("avg_score", 0)
    execution_score = round(invocation_rate * 30 + (avg_exec_score / 5.0) * 70, 1)

    # Auditor check
    audit_report = audit_skill(skill_content, skill_name, llm_args)
    audit_score = float(audit_report.score)

    overall = round(execution_score * 0.6 + audit_score * 0.4, 1)

    # Dimension-level deltas (for targeted rollback)
    dimension_scores = {}
    for check in audit_report.checks:
        dim_name = check.get("check", "unknown")
        severity = check.get("severity", "PASS")
        dimension_scores[dim_name] = {"PASS": 100, "WARN": 60, "FAIL": 20}.get(severity, 50)

    return {
        "overall": overall,
        "execution_score": execution_score,
        "audit_score": audit_score,
        "dimension_scores": dimension_scores,
        "execution_detail": exec_result,
        "audit_checks": [{"check": c["check"], "severity": c.get("severity", "PASS"),
                         "detail": c.get("detail", "")[:120]} for c in audit_report.checks],
        "gate": "approved" if overall >= 70 else "pending" if overall >= 50 else "rejected",
    }


def run_isolated_optimization_round(
    skill_name: str,
    current_content: str,
    previous_content: str,
    current_version: int,
    trace_analysis: str,
    test_tasks: list[str],
    llm_args: tuple,
    *,
    edit_budget: int = 3,
) -> dict:
    """Full isolated optimization round: Optimizer → Evaluator → Gate → Decision Record.

    1. OPTIMIZER proposes edits (isolated from test data)
    2. EVALUATOR scores the new version (isolated from optimizer reasoning)
    3. GATE: accept, reject, or targeted rollback
    4. Decision record is written regardless of outcome
    """
    from skillos.evolution import skillopt as opt

    t_start = time.time()

    # Build contexts for optimizer
    decision_context = build_decision_context(skill_name)
    traces = opt.collect_traces(skill_name)
    protected = opt.identify_protected_regions(current_content, traces)
    protected_context = opt.build_protection_context(protected) if protected else ""

    # 1. OPTIMIZER: propose edits
    new_content, edits = isolated_optimize(
        skill_name, current_content, trace_analysis, llm_args,
        edit_budget=edit_budget, decision_context=decision_context,
        protected_context=protected_context,
    )

    if new_content == current_content:
        return {"accepted": False, "reason": "Optimizer produced no changes", "round": 0}

    # 2. EVALUATOR: score both old and new
    old_eval = isolated_evaluate(current_content, skill_name, test_tasks, llm_args)
    new_eval = isolated_evaluate(new_content, skill_name, test_tasks, llm_args)

    old_overall = old_eval["overall"]
    new_overall = new_eval["overall"]

    # 3. GATE
    if new_overall > old_overall:
        # Full accept
        gate = "accepted"
        final_content = new_content
        detail = f"综合分提升: {old_overall:.1f} → {new_overall:.1f}"
    elif new_overall == old_overall:
        gate = "rejected"
        final_content = current_content
        detail = f"综合分持平 ({old_overall:.1f})，拒绝修改"
    else:
        # Check if targeted rollback can salvage
        regressed_dims = [
            dim for dim in old_eval.get("dimension_scores", {})
            if old_eval["dimension_scores"].get(dim, 0) > new_eval["dimension_scores"].get(dim, 0)
        ]
        if regressed_dims:
            rolled_back = targeted_rollback(new_content, current_content, regressed_dims)
            if rolled_back != new_content:
                # Re-evaluate rolled back version
                rb_eval = isolated_evaluate(rolled_back, skill_name, test_tasks, llm_args)
                if rb_eval["overall"] > old_overall:
                    gate = "partially_accepted"
                    final_content = rolled_back
                    detail = f"定向回滚后提升: {old_overall:.1f} → {rb_eval['overall']:.1f} (回滚维度: {', '.join(regressed_dims[:3])})"
                else:
                    gate = "rejected"
                    final_content = current_content
                    detail = f"回滚后仍无提升 ({old_overall:.1f} → {rb_eval['overall']:.1f})"
            else:
                gate = "rejected"
                final_content = current_content
                detail = f"综合分下降 ({old_overall:.1f} → {new_overall:.1f})，无可回滚的独立区域"
        else:
            gate = "rejected"
            final_content = current_content
            detail = f"综合分下降 ({old_overall:.1f} → {new_overall:.1f})"

    # 4. Record decision
    record = DecisionRecord(
        skill_name=skill_name,
        version_from=current_version,
        version_to=current_version + 1 if gate != "rejected" else current_version,
        round_num=current_version,
        diagnosis=trace_analysis[:500],
        candidate_revisions=[{"type": e["type"], "detail": e["detail"]} for e in edits],
        evaluation_evidence={
            "old_score": old_overall, "new_score": new_overall,
            "old_execution": old_eval["execution_score"], "new_execution": new_eval["execution_score"],
            "old_audit": old_eval["audit_score"], "new_audit": new_eval["audit_score"],
            "dimension_deltas": {
                dim: f"{old_eval['dimension_scores'].get(dim, 0)} → {new_eval['dimension_scores'].get(dim, 0)}"
                for dim in set(list(old_eval.get("dimension_scores", {}).keys()) +
                              list(new_eval.get("dimension_scores", {}).keys()))
            },
        },
        outcome=gate,
        outcome_detail=detail,
        context={"model": llm_args[2] if len(llm_args) > 2 else "",
                 "test_tasks_count": len(test_tasks),
                 "edit_budget": edit_budget},
    )
    record_decision(record)

    return {
        "accepted": gate != "rejected",
        "gate": gate,
        "old_score": old_overall,
        "new_score": new_eval["overall"],
        "final_score": old_eval["overall"] if gate == "rejected" else (
            new_eval["overall"] if gate == "accepted" else new_eval["overall"]
        ),
        "detail": detail,
        "decision_id": record.record_id,
        "execution_detail": new_eval.get("execution_detail", {}),
        "audit_checks": new_eval.get("audit_checks", []),
        "content": final_content,
        "elapsed_s": round(time.time() - t_start, 1),
    }
