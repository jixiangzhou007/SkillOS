"""Trace collection and analysis for SkillOpt.

Functions for collecting, splitting, and analyzing execution traces
to drive data-informed skill optimization.
"""

import logging
import re
from collections import Counter

from .skillopt_types import OptConfig

_log = logging.getLogger(__name__)


def collect_traces(skill_name: str) -> list[dict]:
    """Collect recent execution traces for a skill."""
    try:
        from skillos.evolution.evolver import get_recent_traces
        traces = get_recent_traces(skill_name, 20)
        return [t for t in traces if t.get("score", 0) > 0]
    except Exception as e:
        _log.warning("Non-critical in skillopt_traces.py: %s", e)
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
    # Remove common stopwords, find 2-4 char Chinese phrases that repeat
    phrases = re.findall(r'[一-鿿]{2,4}', text)
    counts = Counter(phrases)
    # Filter to repeated phrases
    repeated = [(p, c) for p, c in counts.most_common(20) if c >= 2]
    return [f"「{p}」(出现 {c} 次)" for p, c in repeated]
