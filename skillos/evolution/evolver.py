"""Skill Self-Evolution Engine — automatic improvement from execution feedback.

Pipeline:
  Execute skill → Record trace → Judge score (1-5) → Diagnose failure
  → Trigger evolution (N failures) → Generate improved skill → Version store
  → User approve/reject

Inspired by GEPA (genetic-pareto evolution), SkillOpt (controlled text edits),
and OpenAI's self-evolving agents cookbook.
"""


import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

# ── Thresholds for triggering evolution ──
AUTO_EVOLVE_FAILURES = 3     # trigger after N failed traces
AUTO_EVOLVE_TOTAL = 10       # or after M total traces
MIN_JUDGE_SCORE = 3           # scores below this = "failed"

# ═══════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════

@dataclass
class ExecutionTrace:
    skill_name: str
    task: str
    result: str
    duration: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    judge_score: int = 0
    judge_feedback: str = ""
    failure_root_cause: str = ""
    version: int = 1


@dataclass
class EvolutionResult:
    skill_name: str
    from_version: int
    to_version: int
    improved_doc: str
    changes_summary: str
    judged_improvement: str  # "significant" | "marginal" | "none"


# ═══════════════════════════════════════════════════════════════
# Trace recording
# ═══════════════════════════════════════════════════════════════

def record_trace(
    skill_name: str, task: str, result: str, duration: float,
    llm_args: tuple | None = None,
) -> ExecutionTrace:
    """Record an execution trace and auto-judge the result."""
    trace = ExecutionTrace(
        skill_name=skill_name,
        task=task,
        result=result,
        duration=duration,
        version=_current_version(skill_name),
    )

    # Auto-judge if LLM args provided
    if llm_args:
        score, feedback, root_cause = _judge(trace, llm_args)
        trace.judge_score = score
        trace.judge_feedback = feedback
        trace.failure_root_cause = root_cause

    _append_trace(trace)
    _log.info("Trace recorded: skill=%s score=%d task=%s",
              skill_name, trace.judge_score, task[:60])
    return trace


# ═══════════════════════════════════════════════════════════════
# Evolution trigger
# ═══════════════════════════════════════════════════════════════

def should_evolve(skill_name: str) -> tuple[bool, str]:
    """Check if the skill should be evolved. Returns (should, reason)."""
    traces = _load_traces(skill_name)
    if not traces:
        return False, "no traces yet"

    total = len(traces)
    recent = traces[-AUTO_EVOLVE_FAILURES:]
    failures = sum(1 for t in recent if t.judge_score < MIN_JUDGE_SCORE)

    if failures >= AUTO_EVOLVE_FAILURES:
        return True, f"{failures}/{len(recent)} recent traces failed (score < {MIN_JUDGE_SCORE})"
    if total >= AUTO_EVOLVE_TOTAL:
        return True, f"{total} total traces accumulated"
    return False, f"need {AUTO_EVOLVE_FAILURES - failures} more failures or {AUTO_EVOLVE_TOTAL - total} more traces"


# ═══════════════════════════════════════════════════════════════
# Evolution engine
# ═══════════════════════════════════════════════════════════════

def evolve(
    skill_name: str, llm_args: tuple, *, force: bool = False,
) -> Optional[EvolutionResult]:
    """Generate an improved version of the skill based on execution traces.

    Args:
        skill_name: Name of the skill to evolve
        llm_args: (api_key, base_url, model, chat_kwargs)
        force: If True, evolve even if trigger conditions not met

    Returns:
        EvolutionResult with improved doc, or None if not ready
    """
    if not force:
        ready, reason = should_evolve(skill_name)
        if not ready:
            _log.info("Evolution not triggered: %s", reason)
            return None

    traces = _load_traces(skill_name)
    current_doc = _load_skill_doc(skill_name)
    if not current_doc:
        _log.error("Cannot evolve: skill doc not found for [%s]", skill_name)
        return None

    current_version = _current_version(skill_name)
    _log.info("Evolving skill [%s] from v%d with %d traces",
              skill_name, current_version, len(traces))

    # Step 1: Generate improved skill doc via LLM
    improved_doc = _generate_improvement(skill_name, current_doc, traces, llm_args)

    # Step 2: Judge the improvement (is it actually better?)
    judgement = _judge_improvement(skill_name, current_doc, improved_doc, traces, llm_args)

    # Step 3: Save new version
    new_version = current_version + 1
    _save_version(skill_name, new_version, improved_doc)

    result = EvolutionResult(
        skill_name=skill_name,
        from_version=current_version,
        to_version=new_version,
        improved_doc=improved_doc,
        changes_summary=_summarize_changes(current_doc, improved_doc),
        judged_improvement=judgement,
    )

    _log.info("Evolution result: v%d→v%d, improvement=%s",
              current_version, new_version, judgement)
    return result


def approve_evolution(skill_name: str, version: int) -> None:
    """Promote a version to be the active skill doc."""
    import shutil
    src = _version_path(skill_name, version)
    dst = _skill_path(skill_name)
    shutil.copy(src, dst)
    _log.info("Skill [%s] promoted to v%d", skill_name, version)


# ═══════════════════════════════════════════════════════════════
# Recent traces for UI display
# ═══════════════════════════════════════════════════════════════

def get_recent_traces(skill_name: str, limit: int = 20) -> list[dict]:
    """Return recent traces as dicts for UI display."""
    traces = _load_traces(skill_name)
    recent = traces[-limit:]
    return [
        {
            "task": t.task[:100],
            "result": t.result[:200],
            "score": t.judge_score,
            "feedback": t.judge_feedback[:200],
            "timestamp": t.timestamp[:19],
        }
        for t in reversed(recent)
    ]


def get_skill_stats(skill_name: str) -> dict:
    """Get evolution stats for a skill."""
    traces = _load_traces(skill_name)
    if not traces:
        return {"total": 0, "avg_score": 0, "failure_rate": 0, "version": 1}
    scores = [t.judge_score for t in traces if t.judge_score > 0]
    failures = sum(1 for t in traces if 0 < t.judge_score < MIN_JUDGE_SCORE)
    return {
        "total": len(traces),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "failure_rate": round(failures / len(traces) * 100, 1) if traces else 0,
        "version": _current_version(skill_name),
    }


# ═══════════════════════════════════════════════════════════════
# Internal: LLM calls
# ═══════════════════════════════════════════════════════════════

JUDGE_PROMPT = """你是一个技能执行质量评估器。根据以下信息对技能执行结果评分。

## 用户任务
{task}

## 执行结果
{result}

## 评分标准（1-5分）
5 = 完美：完全满足任务要求，结果准确、完整、可直接使用
4 = 良好：基本满足要求，有小瑕疵但不影响使用
3 = 及格：部分满足要求，有缺失或需修改才能用
2 = 较差：多处错误或不完整，需要大幅改进
1 = 失败：完全未满足要求或产生错误结果

## 输出要求
返回 JSON（不要 markdown）：
{{"score": <1-5>, "feedback": "<一句话评价>", "root_cause": "<S_body流程缺失/参数错误/触发条件不对/知识库不足/其他>"}}"""


def _judge(trace: ExecutionTrace, llm_args: tuple) -> tuple[int, str, str]:
    """LLM judges an execution trace."""
    try:
        prompt = JUDGE_PROMPT.format(task=trace.task, result=trace.result[:2000])
        output = _call_llm(prompt, llm_args, max_tokens=300)
        data = _parse_json(output)
        score = int(data.get("score", 3))
        feedback = str(data.get("feedback", ""))
        root_cause = str(data.get("root_cause", ""))
        return score, feedback, root_cause
    except Exception as exc:
        _log.warning("Judge failed: %s", exc)
        return 0, f"Judge error: {exc}", "judge_failed"


EVOLVE_PROMPT = """你是一个技能文档优化器。根据技能的执行反馈改进技能文档。

## 当前技能文档
{current_doc}

## 近期执行记录（含评分和诊断）
{traces_summary}

## 改进要求
1. 只修改有问题的章节（S_body/S_trigger/S_params/S_appendix），保持好的部分不变
2. 针对失败根因做精细调整，不要大幅重写
3. 补充缺失的步骤、修正错误的参数、完善触发条件
4. 在文档末尾添加 S_changelog，说明本次改进了什么

## 输出
用 ```skill_doc ... ``` 围栏输出完整的改进后文档。"""


def _generate_improvement(
    skill_name: str, current_doc: str, traces: list[ExecutionTrace], llm_args: tuple,
) -> str:
    """Generate improved skill doc based on failure traces."""
    # Summarize recent traces
    lines = []
    for t in traces[-10:]:
        score_emoji = "✅" if t.judge_score >= 4 else "⚠️" if t.judge_score >= 3 else "❌"
        lines.append(
            f"{score_emoji} 评分{t.judge_score} | 任务: {t.task[:80]} | "
            f"根因: {t.failure_root_cause or '无'} | 反馈: {t.judge_feedback[:100]}"
        )
    traces_summary = "\n".join(lines) if lines else "（无执行记录）"

    prompt = EVOLVE_PROMPT.format(current_doc=current_doc, traces_summary=traces_summary)
    try:
        output = _call_llm(prompt, llm_args, max_tokens=2000)
    except Exception as exc:
        _log.error("Evolution LLM failed: %s", exc)
        return current_doc  # fallback: no change

    # Extract skill_doc fence
    import re
    match = re.search(r"```skill_doc\s*\n(.*?)```", output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # If no fence, return cleaned output
    cleaned = re.sub(r"```\w*\n?", "", output).replace("```", "").strip()
    return cleaned if cleaned else current_doc


JUDGE_IMPROVEMENT_PROMPT = """判断以下技能文档的改进是否有实质提升。

## 原文档
{original[:800]}

## 改进后文档
{improved[:800]}

## 近期失败记录
{traces_summary}

输出 JSON：{{"judgement": "significant|marginal|none", "reason": "<一句话>"}}"""


def _judge_improvement(
    skill_name: str, original: str, improved: str,
    traces: list[ExecutionTrace], llm_args: tuple,
) -> str:
    """Judge whether the improvement is real."""
    failures = [t for t in traces[-10:] if t.judge_score < MIN_JUDGE_SCORE]
    summary = "\n".join(
        f"- 评分{t.judge_score}: {t.failure_root_cause}" for t in failures
    ) if failures else "（无失败记录）"

    prompt = JUDGE_IMPROVEMENT_PROMPT.format(
        original=original, improved=improved, traces_summary=summary,
    )
    try:
        output = _call_llm(prompt, llm_args, max_tokens=200)
        data = _parse_json(output)
        return str(data.get("judgement", "marginal"))
    except Exception:
        return "marginal"


# ═══════════════════════════════════════════════════════════════
# Internal: file I/O
# ═══════════════════════════════════════════════════════════════

def _skill_dir(skill_name: str) -> Path:
    import re
    safe = re.sub(r'[<>:"/\\|?*]', '_', skill_name)[:64]
    return SKILLS_DIR / safe


def _skill_path(skill_name: str) -> Path:
    return _skill_dir(skill_name) / f"{skill_name}.md"


def _version_path(skill_name: str, version: int) -> Path:
    d = _skill_dir(skill_name) / "versions"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"v{version:03d}_{skill_name}.md"


def _traces_path(skill_name: str) -> Path:
    return _skill_dir(skill_name) / "traces.jsonl"


def _current_version(skill_name: str) -> int:
    d = _skill_dir(skill_name) / "versions"
    if not d.exists():
        return 1
    files = sorted(d.glob("v*_*.md"))
    return len(files) + 1 if files else 1


def _load_skill_doc(skill_name: str) -> Optional[str]:
    path = _skill_path(skill_name)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _save_version(skill_name: str, version: int, doc: str) -> None:
    path = _version_path(skill_name, version)
    path.write_text(doc, encoding="utf-8")
    _log.info("Version saved: %s", path)


def _append_trace(trace: ExecutionTrace) -> None:
    path = _traces_path(trace.skill_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task": trace.task, "result": trace.result[:500],
        "duration": trace.duration, "timestamp": trace.timestamp,
        "judge_score": trace.judge_score, "judge_feedback": trace.judge_feedback,
        "failure_root_cause": trace.failure_root_cause, "version": trace.version,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_traces(skill_name: str) -> list[ExecutionTrace]:
    path = _traces_path(skill_name)
    if not path.exists():
        return []
    traces = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                traces.append(ExecutionTrace(
                    skill_name=skill_name,
                    task=d.get("task", ""),
                    result=d.get("result", ""),
                    duration=d.get("duration", 0),
                    timestamp=d.get("timestamp", ""),
                    judge_score=d.get("judge_score", 0),
                    judge_feedback=d.get("judge_feedback", ""),
                    failure_root_cause=d.get("failure_root_cause", ""),
                    version=d.get("version", 1),
                ))
            except (json.JSONDecodeError, KeyError):
                continue
    return traces


def _summarize_changes(original: str, improved: str) -> str:
    """Simple diff summary."""
    if original == improved:
        return "（无变化）"
    orig_lines = set(original.split("\n"))
    new_lines = set(improved.split("\n"))
    added = new_lines - orig_lines
    removed = orig_lines - new_lines
    parts = []
    if added:
        parts.append(f"+{len(added)} 行新增")
    if removed:
        parts.append(f"-{len(removed)} 行删除")
    return ", ".join(parts) if parts else "内容有调整"


# ═══════════════════════════════════════════════════════════════
# Internal: helpers
# ═══════════════════════════════════════════════════════════════

def _call_llm(prompt: str, llm_args: tuple, max_tokens: int = 600) -> str:
    api_key, base_url, model, chat_kwargs = llm_args
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model, max_tokens=max_tokens, temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
        **chat_kwargs,
    )
    return (resp.choices[0].message.content or "").strip()


def _parse_json(text: str) -> dict:
    import re
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return {}
