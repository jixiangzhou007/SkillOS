"""SkillOpt — Optimize skill documents through bounded edits, trajectory analysis,
cross-model validation, and meta-learning.

Inspired by Microsoft SkillOpt (arXiv:2605.23904).
Key insight: treat skill.md as trainable external state — target model frozen,
optimizer model proposes small, verifiable edits with a validation gate.
"""


import json
import logging
import re
import time
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)


@dataclass
class OptConfig:
    """SkillOpt optimization configuration."""

    # Edit budget: starts at 4, decays by 1 per round, min 1
    initial_edit_budget: int = 4
    min_edit_budget: int = 1

    # Validation
    validation_split_ratio: float = 0.3  # oldest 30% traces as held-out
    min_traces_for_split: int = 3         # need at least this many traces to split
    strict_gate: bool = True              # require strict score improvement

    # Cross-model validation
    cross_model_enabled: bool = True
    fast_model: str = "deepseek-v4-flash"  # cheaper model for quick validation

    # Meta-learning
    meta_enabled: bool = True
    meta_skill_max_len: int = 600  # keep meta-skill compact

    # Rollout
    max_rollout_tasks: int = 5  # max tasks to run per optimization round
    rollout_timeout: int = 120  # seconds per rollout task


@dataclass
class EditProposal:
    """A single proposed edit to a skill document."""

    edit_type: str   # "add", "delete", "replace"
    target: str      # what section/line to edit
    old_text: str = ""
    new_text: str = ""
    reason: str = ""  # why this edit (traceable to a failure)

    def to_markdown(self) -> str:
        markers = {"add": "+", "delete": "-", "replace": "~"}
        m = markers.get(self.edit_type, "?")
        if self.edit_type == "add":
            return f"{m} add [{self.target}]: {self.new_text[:120]}\n  原因: {self.reason[:100]}"
        elif self.edit_type == "delete":
            return f"{m} delete [{self.target}]: {self.old_text[:120]}\n  原因: {self.reason[:100]}"
        else:
            return f"{m} replace [{self.target}]: {self.old_text[:60]} → {self.new_text[:60]}\n  原因: {self.reason[:100]}"


@dataclass
class OptimizationRound:
    """One round of optimization."""

    round_num: int
    edit_budget: int
    proposals: list[EditProposal] = field(default_factory=list)
    accepted: list[EditProposal] = field(default_factory=list)
    rejected: list[EditProposal] = field(default_factory=list)
    old_score: float = 0.0
    new_score: float = 0.0
    gate_result: str = ""  # "accepted", "rejected", "skipped"
    cross_model_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class OptimizationSession:
    """Tracks multi-round optimization state across a conversation."""

    skill_name: str
    original_content: str
    current_content: str
    rounds: list[OptimizationRound] = field(default_factory=list)
    rejection_buffer: list[str] = field(default_factory=list)  # failed edit patterns
    meta_skill: str = ""  # cross-round stable patterns
    config: OptConfig = field(default_factory=OptConfig)

    @property
    def round_num(self) -> int:
        return len(self.rounds)

    def edit_budget_for_round(self) -> int:
        """Decaying edit budget: starts at 4, decays per round."""
        next_round = len(self.rounds) + 1
        budget = self.config.initial_edit_budget - (next_round - 1)
        return max(self.config.min_edit_budget, budget)


# ═══════════════════════════════════════════════════════════════
# Rollout Engine
# ═══════════════════════════════════════════════════════════════

def collect_traces(skill_name: str) -> list[dict]:
    """Collect recent execution traces for a skill."""
    try:
        from skillos.evolution.evolver import get_recent_traces
        traces = get_recent_traces(skill_name, 20)
        return [t for t in traces if t.get("score", 0) > 0]
    except Exception as e:
        _log.warning("Non-critical in skillopt.py: %s", e)
        return []


def split_traces(
    traces: list[dict],
    config: OptConfig,
) -> tuple[list[dict], list[dict]]:
    """Split traces into train (recent) and validation (older).

    Train: newest 70% — used for failure analysis
    Validation: oldest 30% — held-out for validation gate
    """
    if len(traces) < config.min_traces_for_split:
        return traces, []  # not enough data to split

    split_idx = max(1, int(len(traces) * (1 - config.validation_split_ratio)))
    train = traces[:split_idx]   # newer traces for training
    val = traces[split_idx:]     # older traces for validation
    return train, val


def analyze_traces(
    traces: list[dict],
) -> str:
    """Build a human-readable analysis of traces for the optimizer.

    Returns a markdown string suitable for inclusion in the optimizer prompt.
    """
    if not traces:
        return "（无可用轨迹数据）"

    successes = [t for t in traces if t.get("score", 0) >= 4]
    failures = [t for t in traces if t.get("score", 0) < 3]
    neutral = [t for t in traces if 3 <= t.get("score", 0) < 4]

    lines = [f"## 📊 执行轨迹 ({len(traces)} 条)"]

    if successes:
        lines.append(f"\n### ✅ 成功 ({len(successes)} 条，得分 ≥ 4)")
        for t in successes[:2]:
            task = t.get("task", "")[:100]
            score = t.get("score", "?")
            lines.append(f"- [{score}/5] {task}")

    if failures:
        lines.append(f"\n### ❌ 失败 ({len(failures)} 条，得分 < 3) — 从这里找改进方向")
        for t in failures[:4]:
            task = t.get("task", "")[:100]
            score = t.get("score", "?")
            fb = t.get("feedback", "")[:200]
            rc = t.get("failure_root_cause", "")[:150]
            lines.append(f"- [{score}/5] **{task}**")
            if rc:
                lines.append(f"  根因: *{rc}*")
            if fb:
                lines.append(f"  反馈: {fb}")

    if neutral:
        lines.append(f"\n### ⚪ 中等 ({len(neutral)} 条，3 ≤ 得分 < 4)")

    # Extract recurring failure keywords
    if failures:
        all_fb = " ".join(t.get("feedback", "") + " " + t.get("failure_root_cause", "")
                          for t in failures)
        lines.append("\n### 🔍 高频失败模式")
        patterns = _extract_patterns(all_fb)
        for p in patterns[:5]:
            lines.append(f"- {p}")

    return "\n".join(lines)


def _extract_patterns(text: str) -> list[str]:
    """Extract recurring keywords/phrases from failure feedback."""
    import re
    # Remove common stopwords, find 2-4 char Chinese phrases that repeat
    phrases = re.findall(r'[一-鿿]{2,4}', text)
    from collections import Counter
    counts = Counter(phrases)
    # Filter to repeated phrases
    repeated = [(p, c) for p, c in counts.most_common(20) if c >= 2]
    return [f"「{p}」(出现 {c} 次)" for p, c in repeated]


# ═══════════════════════════════════════════════════════════════
# Validation Gate
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# Meta-Skill (Slow Updates)
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# Optimizer Prompt Builder
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# Full Optimization Pipeline
# ═══════════════════════════════════════════════════════════════

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
        import re as _re
        terms = set(_re.findall(r'[\w一-鿿]{3,}', sec_text))

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
    current_lines = []

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


# ═══════════════════════════════════════════════════════════════
# Elite Pool Tournament (EvoSkill §Verification — "打擂台")
# ═══════════════════════════════════════════════════════════════

@dataclass
class ElitePool:
    """Fixed-capacity pool of top-K competing skill versions.

    Each candidate must beat the weakest member to enter.
    Eliminated candidates are archived with failure reasons for proposer feedback.
    """

    skill_name: str
    max_size: int = 3
    members: list[dict] = field(default_factory=list)  # [{content, score, version, entered_at}]
    eliminated: list[dict] = field(default_factory=list)  # [{content_preview, score, eliminated_reason}]

    @property
    def champion(self) -> dict | None:
        return self.members[0] if self.members else None

    @property
    def weakest(self) -> dict | None:
        return self.members[-1] if self.members else None

    @property
    def median_score(self) -> float:
        if not self.members:
            return 0.0
        scores = sorted([m["score"] for m in self.members])
        mid = len(scores) // 2
        return scores[mid]

    def nominate(self, candidate_content: str, candidate_score: float, version: int) -> tuple[bool, str]:
        """Nominate a candidate for the elite pool.

        Pool fills freely until max_size. After that, tournament mode:
        candidate must beat the weakest member to enter.

        Returns (accepted, reason).
        """
        # Pool not full yet — auto-admit
        if len(self.members) < self.max_size:
            self.members.append({
                "content": candidate_content, "score": candidate_score,
                "version": version, "entered_at": time.time(),
            })
            self.members.sort(key=lambda m: m["score"], reverse=True)
            return True, f"入池（{len(self.members)}/{self.max_size}，未满免赛）"

        # Tournament: pool full, must beat the weakest
        weakest = self.weakest
        if candidate_score > weakest["score"]:
            eliminated = self.members.pop()  # Remove weakest
            self.eliminated.append({
                "content_preview": eliminated["content"][:200],
                "score": eliminated["score"],
                "eliminated_by_score": candidate_score,
                "eliminated_at": time.time(),
            })
            self.members.append({
                "content": candidate_content, "score": candidate_score,
                "version": version, "entered_at": time.time(),
            })
            self.members.sort(key=lambda m: m["score"], reverse=True)
            return True, f"胜出：{candidate_score:.1f} > {weakest['score']:.1f}（淘汰池底版本 v{eliminated['version']}）"

        # Lost the tournament
        self.eliminated.append({
            "content_preview": candidate_content[:200],
            "score": candidate_score,
            "eliminated_reason": f"得分 {candidate_score:.1f} ≤ 池底 {weakest['score']:.1f}",
            "eliminated_at": time.time(),
        })
        return False, f"未入池：{candidate_score:.1f} ≤ {weakest['score']:.1f}（未击败池底版本 v{weakest['version']}）"

    def get_elimination_feedback(self) -> str:
        """Build proposer feedback from eliminated candidates."""
        if not self.eliminated:
            return ""
        lines = ["\n## 🏆 精英池淘汰记录（给提案者的反面教材）\n"]
        for e in self.eliminated[-5:]:
            lines.append(f"- ❌ 得分 {e['score']:.1f}: {e.get('eliminated_reason', e.get('eliminated_by_score', '淘汰'))}")
            lines.append(f"  内容预览: {e['content_preview'][:100]}...")
        return "\n".join(lines)


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


# ═══════════════════════════════════════════════════════════════
# SkillEvolver-inspired: Independent Auditor
# ═══════════════════════════════════════════════════════════════
#
# SkillEvolver's key insight: skill quality can't be judged by the
# author agent alone. A clean-context Auditor checks deployment hazards
# that the author is blind to: hardcoded constants, missing entry points,
# silent-bypass patterns, overfitting to training examples.

@dataclass
class AuditReport:
    """Independent audit of a skill document."""

    passed: bool = False
    score: int = 0            # 0-100
    checks: list[dict] = field(default_factory=list)
    # Each check: {check_name, passed, severity, detail, suggestion}
    summary: str = ""


def audit_skill(
    skill_content: str,
    skill_name: str,
    llm_args: tuple,
    *,
    training_examples: list[str] | None = None,
) -> AuditReport:
    """Independent Auditor — checks a skill for deployment hazards.

    The Auditor sees ONLY the skill document and task description.
    It does NOT see the author agent's private reasoning, exploration
    strategies, or the training data labels. This is the "fresh eyes" check.

    Detects:
    1. Hardcoded constants — values that should be parameters
    2. Missing entry point — main action not prominent enough
    3. Silent-bypass — agent could skip the skill without noticing
    4. Overfitting — training-specific patterns that won't generalize
    5. Self-contained — can the skill work without external context?
    6. Abstraction — are key axes parameterized or hardcoded?
    """
    from skillos.llm_client import call

    examples_hint = ""
    if training_examples:
        examples_hint = "\n## 训练时见过的任务样例\n" + "\n".join(
            f"- {ex[:120]}" for ex in training_examples[:3]
        )
        examples_hint += "\n\n⚠️ 检查技能文档中是否残留了只适用于这些样例的硬编码常量或假设。"

    prompt = f"""你是技能部署审计员。你只看到候选技能文档，看不到作者 Agent 的私有推理。

## 候选技能文档
```
{skill_content[:2000]}
```

## 技能名称
{skill_name}
{examples_hint}

## 审计维度（每个维度独立打分：PASS / WARN / FAIL）

### 1. 自包含性 (Self-contained)
- 一个全新 Agent 拿到这份技能，能不能独立执行，不需要额外上下文？
- 技能是否引用了不存在的文件、工具或外部资源？

### 2. 主入口可见性 (Entry Point Visibility)
- 技能的主入口（最核心的那个操作）是否在最显眼的位置？
- 一个 fresh agent 能不能在 5 秒内找到"我该调用什么"？
- 检查：S_trigger 的描述是否足够具体，能让 dispatcher 正确路由？

### 3. 硬编码检测 (Hardcoded Constants)
- 技能中是否包含只适用于训练样例的常量（文件名、路径、特定数值）？
- 这些常量是否应该被抽象为 S_params？

### 4. Silent-Bypass 风险
- 是否存在"Agent 跳过了关键步骤但技能没报错"的路径？
- S_body 的每个步骤是否有明确的成功/失败判定？
- if-then 分支是否遗漏了"异常情况"的处理？

### 5. 过拟合检测 (Overfitting)
- 技能中的规则是否过度特化到训练样例？
- 换成同类但不同名的文件、不同的数值范围，技能还能用吗？

### 6. 参数抽象 (Parameter Abstraction)
- 关键决策轴（阈值、文件类型、API 端点等）是否在 S_params 中暴露？
- 还是写死在 S_body 的步骤描述里？

### 7. 描述质量 (Description Quality)
- S_trigger 中的 description/keywords 是否足够具体？
- 有没有列出**具体的触发词**（不是"帮助用户"这种泛词）？
- 有没有写清楚**不应该触发的边界**？
- 对照标准：❌ "帮助处理视频" → ✅ "短视频口播稿撰写和分镜拆解。触发词：写脚本、改文案、短视频结构。不触发：纯娱乐搞笑视频。"

### 8. 决策表完整性 (Decision Table)

### 9. 跨平台可移植性 (Cross-Platform Portability)

### 10. 简洁度 (Brevity — "LLM越强，Skill越短")
- 模型能力越强，Skill 应该越精简。强模型只需方向指引，不需要逐字步骤。
- SKILL.md 是否超过 500 字？如果是，检查是否过度解释或重复约定。
- S_body 的每个步骤是否是"单一可验证动作"，而非"解释+动作+示例"的复合体？
- 如果目标模型是 Claude 4.x / GPT-5 / DeepSeek V4 级别：Skill 应 < 400 字。
- 如果目标模型是 Qwen 3B 级别：Skill 可以适当增加到 < 800 字。

- Skill 是否使用了特定平台的专用语法（如 Claude-only tool names）？
- S_trigger 中的关键词是否足够通用，能在不同调度器（Claude/Codex/Hermes）中正确触发？
- S_route 文件路径引用是否跨平台兼容（Windows/Linux/macOS）？
- MCP tool 参数是否使用标准 JSON Schema，无平台特定字段？

- 是否有 S_route 决策表？
- 决策表是否覆盖了 S_body 中提到的所有分支场景？
- 每个路由是否指向了实际存在的 references/ 文件路径？
- 如果 S_body 有多个分支但 S_route 只有一行 → WARN

## 输出格式
```json
{{
  "checks": [
    {{"check": "self_contained", "passed": true, "severity": "PASS|WARN|FAIL", "detail": "具体发现", "suggestion": "修改建议"}},
    {{"check": "entry_visibility", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "hardcoded_constants", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "silent_bypass", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "overfitting", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "param_abstraction", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "description_quality", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "decision_table", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "portability", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "brevity", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}}}}
  ],
  "overall_score": 85,
  "summary": "一句话总结审计结果"
}}
```

只输出 JSON。"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=1500, temperature=0.1)
    except Exception as e:
        _log.warning("Auditor LLM call failed: %s", e)
        return AuditReport(passed=True, score=100,
                          checks=[{"check": "auditor_error", "passed": True,
                                   "severity": "WARN", "detail": str(e)}],
                          summary="审计器调用失败，放行")

    # Parse — multiple fallback strategies for robustness
    data = None
    # Strategy 1: JSON in markdown code block
    m = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', raw, re.DOTALL)
    json_candidate = m.group(1).strip() if m else ""
    if json_candidate:
        try:
            data = json.loads(json_candidate)
        except json.JSONDecodeError:
            pass
    # Strategy 2: Raw text is pure JSON
    if data is None and raw.strip().startswith('{'):
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            pass
    # Strategy 3: Find JSON object in raw text via brace matching
    if data is None:
        brace_start = raw.find('{')
        brace_end = raw.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            try:
                data = json.loads(raw[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
    # Strategy 4: Fix common LLM JSON errors (trailing commas, unquoted keys)
    if data is None:
        cleaned = raw.strip()
        # Remove text before first { and after last }
        brace_start = cleaned.find('{')
        brace_end = cleaned.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            cleaned = cleaned[brace_start:brace_end + 1]
        # Fix trailing commas before closing } or ]
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    if data is None:
        _log.warning("Auditor JSON parse failed — raw[:300]: %s", raw[:300])
        return AuditReport(passed=True, score=60,
                          checks=[{"check": "parse_error", "passed": True,
                                   "severity": "WARN", "detail": "审计结果解析失败"}],
                          summary="审计解析失败，降级放行")

    checks = data.get("checks", [])
    score = data.get("overall_score", 50)
    failures = [c for c in checks if c.get("severity") == "FAIL"]
    warnings = [c for c in checks if c.get("severity") == "WARN"]

    report = AuditReport(
        passed=len(failures) == 0,
        score=score,
        checks=checks,
        summary=data.get("summary", ""),
    )

    _log.info("Audit: skill=%s score=%d passed=%s failures=%d warnings=%d",
              skill_name, score, report.passed, len(failures), len(warnings))

    return report


def build_audit_context(report: AuditReport) -> str:
    """Build the audit report context for the optimizer prompt."""
    if report.score >= 90:
        return ""

    lines = ["\n## 🔍 独立审计报告 (SkillEvolver Auditor)\n"]
    lines.append(f"总分: {report.score}/100 | {'✅ 通过' if report.passed else '❌ 未通过'}\n")

    failures = [c for c in report.checks if c.get("severity") == "FAIL"]
    warnings = [c for c in report.checks if c.get("severity") == "WARN"]

    if failures:
        lines.append("### ❌ 必须修复")
        for c in failures:
            lines.append(f"- **{c['check']}**: {c.get('detail', '')}")
            if c.get("suggestion"):
                lines.append(f"  💡 {c['suggestion']}")

    if warnings:
        lines.append("\n### ⚠️ 建议修复")
        for c in warnings:
            lines.append(f"- **{c['check']}**: {c.get('detail', '')}")

    lines.append(f"\n📝 {report.summary}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# SkillEvolver-inspired: Fresh-Agent Deployment Test
# ═══════════════════════════════════════════════════════════════
#
# "Skill quality can't be judged by the author agent alone."
# A clean agent loads the skill and tries to use it. Failures here
# reveal deployment hazards the author was blind to.

def fresh_agent_deploy_test(
    skill_content: str,
    skill_name: str,
    test_task: str,
    llm_args: tuple,
) -> dict:
    """Deploy the skill to a fresh agent and observe what happens.

    The fresh agent has NO context about how the skill was created.
    It only gets: the skill document + the test task.

    Returns {task, invoked_skill, result_preview, errors, score}
    """
    from skillos.skills import agent_factory

    try:
        agent = agent_factory.create_agent(skill_content, test_task)
        result = agent_factory.run_agent(agent, test_task)

        # Heuristic checks on the result
        invoked = _check_skill_invocation(test_task, result, skill_content)
        errors = _detect_deployment_errors(result)

        from skillos.evolution.evolver import record_trace
        trace = record_trace(
            skill_name, test_task, result, 0, llm_args
        )

        return {
            "task": test_task[:150],
            "invoked_skill": invoked,
            "result_preview": result[:300],
            "errors": errors,
            "score": trace.judge_score,
        }
    except Exception as e:
        return {
            "task": test_task[:150],
            "invoked_skill": False,
            "result_preview": "",
            "errors": [str(e)],
            "score": 0,
        }


def _check_skill_invocation(task: str, result: str, skill_content: str) -> bool:
    """Check if the fresh agent actually used the skill.

    Heuristic: does the result reference concepts/terms/step names
    that are unique to this skill document?
    """
    # Extract distinctive terms from skill
    terms = set()
    for line in skill_content.split("\n"):
        line = line.strip()
        if line.startswith("## ") or line.startswith("### "):
            terms.add(line.replace("#", "").strip()[:30])
        # Extract step numbers
        if line.startswith(("1.", "2.", "3.", "4.", "5.")):
            terms.add(line[:60])

    # Check if any distinctive term appears in result
    matches = 0
    for term in terms:
        if len(term) > 10 and term in result:
            matches += 1

    return matches >= 1


def _detect_deployment_errors(result: str) -> list[str]:
    """Detect common deployment failure patterns in the agent's output."""
    errors = []

    # Silent bypass: agent says "I don't know how to..." or "I cannot..."
    if re.search(r'(I don\'t know how|I cannot|Unable to|无法|不能|不知道如何)', result, re.IGNORECASE):
        errors.append("silent_bypass: agent couldn't use the skill")

    # Missing dependency: "file not found", "module not found"
    if re.search(r'(file not found|module not found|No such file|找不到文件)', result, re.IGNORECASE):
        errors.append("missing_dependency: skill references unavailable resource")

    # Hallucinated action: result contains made-up API calls
    if re.search(r'(I will|let me|I\'ll try)', result, re.IGNORECASE) and len(result) < 100:
        errors.append("no_execution: agent talked about doing but didn't execute")

    return errors


def run_fresh_agent_battery(
    skill_content: str,
    skill_name: str,
    test_tasks: list[str],
    llm_args: tuple,
) -> dict:
    """Run a battery of fresh-agent deployment tests.

    Returns summary: {tasks_tested, invocation_rate, avg_score, failures}
    """
    results = []
    for task in test_tasks[:3]:  # max 3 tasks
        r = fresh_agent_deploy_test(skill_content, skill_name, task, llm_args)
        results.append(r)

    invoked_count = sum(1 for r in results if r["invoked_skill"])
    scores = [r["score"] for r in results if r["score"] > 0]
    avg_score = sum(scores) / len(scores) if scores else 0
    all_errors = []
    for r in results:
        all_errors.extend(r.get("errors", []))

    return {
        "tasks_tested": len(results),
        "invocation_rate": round(invoked_count / len(results), 2) if results else 0,
        "avg_score": round(avg_score, 1),
        "failures": all_errors,
        "detail": [
            {"task": r["task"][:80], "invoked": r["invoked_skill"],
             "score": r["score"], "errors": r["errors"]}
            for r in results
        ],
    }


# ═══════════════════════════════════════════════════════════════
# MoE Router — Mixture of Experts for Skill Evolution
# ═══════════════════════════════════════════════════════════════
#
# Three experts, one gating network:
#
#   Expert A — Trace2Skill (Batch Discovery)
#     Best when: many traces, diverse failure patterns, new skill
#     Method: collect all traces → collective diagnosis → merge patterns
#
#   Expert B — EvoSkill (Tournament Selection)
#     Best when: high score variance, competing approaches, quality filtering
#     Method: maintain elite pool → candidates fight to enter → best survive
#
#   Expert C — SkillOpt (Bounded Fine-tuning)
#     Best when: stable skill, specific known issues, low variance
#     Method: bounded edits → strict gate → protected regions
#
# Gating factors:
#   - trace_count: how many execution traces exist
#   - score_variance: how much scores fluctuate (high variance = instability)
#   - skill_maturity: total runs / time since creation
#   - failure_diversity: how many distinct failure root causes
#   - has_protected_regions: whether core logic has been identified as stable
#
# Routing modes:
#   - "auto": gating network decides (default)
#   - "top2_vote": run top-2 experts, take the version with higher validation score
#   - "all3_ensemble": run all three, majority vote on each proposed edit
#   - "force_<expert>": force a specific expert for debugging

from enum import Enum, auto


class EvolutionExpert(Enum):
    TRACE2SKILL = auto()   # Batch collective discovery
    EVOSKILL = auto()      # Tournament selection
    SKILLOPT = auto()      # Bounded fine-tuning


@dataclass
class SkillState:
    """Features that the gating network uses to route."""
    skill_name: str
    trace_count: int = 0
    score_mean: float = 0.0
    score_variance: float = 0.0
    failure_count: int = 0
    failure_diversity: int = 0       # number of distinct root cause categories
    total_runs: int = 0
    days_since_creation: float = 0.0
    has_protected_regions: bool = False
    elite_pool_size: int = 0


@dataclass
class RoutingDecision:
    """Which expert(s) to use and why."""
    primary: EvolutionExpert
    secondary: EvolutionExpert | None = None
    mode: str = "auto"           # auto | top2_vote | all3_ensemble | force_<expert>
    confidence: float = 0.5      # how confident the router is in this decision
    reasoning: str = ""


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
