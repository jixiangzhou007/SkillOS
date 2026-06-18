"""MoE-driven single-dimension skill boost when overall score < threshold (P2)."""

from __future__ import annotations

import logging
import re
from typing import Any

from skillos.evaluation.experts import EXPERTS, ExpertDefinition
from skillos.evaluation.moe import evaluate_skill, MoEReport, ExpertResult

_log = logging.getLogger(__name__)

MOE_PASS_THRESHOLD = 70
MOE_SOFT_THRESHOLD = 80
EXPERT_PASS_THRESHOLD = 70

_SECTION_BY_EXPERT: dict[str, str] = {
    "structure": "S_body",
    "security": "S_body",
    "params": "S_params",
    "routing": "S_route",
    "content": "S_body",
    "brevity": "S_body",
}


def _weakest_expert(report: MoEReport) -> ExpertResult | None:
    if not report.experts:
        return None
    return min(report.experts, key=lambda e: e.score)


def _build_boost_prompt(expert: ExpertDefinition, body: str, skill_name: str, summary: str) -> str:
    section = _SECTION_BY_EXPERT.get(expert.key, "Instructions")
    return f"""你是技能文档补强专家。只改进「{expert.name}」负责的维度，不要重写无关部分。

技能名: {skill_name}
最弱维度: {expert.key}（当前约 {summary}）
目标章节: ## {section}

## 当前技能正文
```
{body[:6000]}
```

请输出 **仅** 需要新增或替换的 `{section}` 章节 Markdown（以 `## {section}` 开头）。
要求：
- 保留原有正确内容，只补缺失项
- 中文为主，步骤具体可执行
- 不要输出 YAML frontmatter 或解释文字
"""


def _merge_section(body: str, section: str, new_block: str) -> str:
    new_block = new_block.strip()
    if not new_block.startswith("##"):
        new_block = f"## {section}\n{new_block}"

    pattern = rf"^##\s*{re.escape(section)}\s*\n.*?(?=^##\s|\Z)"
    if re.search(pattern, body, re.MULTILINE | re.DOTALL | re.IGNORECASE):
        return re.sub(
            pattern,
            new_block.rstrip() + "\n\n",
            body,
            count=1,
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )

    if "## S_body" in body:
        return body.replace("## S_body", new_block.rstrip() + "\n\n## S_body", 1)
    if "## Instructions" in body:
        return body.replace("## Instructions", new_block.rstrip() + "\n\n## Instructions", 1)
    return body.rstrip() + "\n\n" + new_block.rstrip() + "\n"


def boost_weakest_dimension(
    body: str,
    skill_name: str,
    llm_args: tuple,
    report: MoEReport,
) -> tuple[str, dict[str, Any]]:
    """Run one targeted LLM pass for the weakest MoE expert."""
    weakest = _weakest_expert(report)
    if weakest is None or weakest.score >= EXPERT_PASS_THRESHOLD:
        return body, {"boosted": False, "reason": "no_weak_expert"}

    expert_def = next((e for e in EXPERTS if e.key == weakest.expert_key), None)
    if expert_def is None:
        return body, {"boosted": False, "reason": "unknown_expert"}

    from skillos.llm_client import call

    model = llm_args[2] if len(llm_args) > 2 else ""
    prompt = _build_boost_prompt(expert_def, body, skill_name, weakest.summary)
    try:
        patch = call(prompt, model=model, max_tokens=1200, temperature=0.2)
    except Exception as exc:
        _log.warning("MoE boost LLM failed for %s: %s", skill_name, exc)
        return body, {"boosted": False, "reason": str(exc)}

    section = _SECTION_BY_EXPERT.get(weakest.expert_key, "Instructions")
    updated = _merge_section(body, section, patch.strip())
    return updated, {
        "boosted": updated != body,
        "expert_key": weakest.expert_key,
        "before_score": weakest.score,
        "section": section,
    }


def evaluate_and_boost(
    body: str,
    skill_name: str,
    llm_args: tuple,
    *,
    threshold: int = MOE_PASS_THRESHOLD,
    soft_threshold: int = MOE_SOFT_THRESHOLD,
    max_rounds: int = 2,
) -> tuple[str, MoEReport, list[dict[str, Any]]]:
    """Evaluate skill; boost if below soft_threshold.

    - score < threshold: up to max_rounds hard boosts
    - threshold <= score < soft_threshold: 1 soft boost round
    - score >= soft_threshold: no boost
    """
    report = evaluate_skill(body, skill_name, llm_args)
    current = body
    boosts: list[dict[str, Any]] = []

    if report.overall_score < threshold:
        rounds_left = max_rounds
    elif report.overall_score < soft_threshold:
        rounds_left = 1
    else:
        rounds_left = 0

    for _ in range(rounds_left):
        if report.overall_score >= soft_threshold:
            break
        current, meta = boost_weakest_dimension(current, skill_name, llm_args, report)
        meta["round"] = len(boosts) + 1
        meta["score_before"] = report.overall_score
        meta["soft_boost"] = report.overall_score >= threshold
        boosts.append(meta)
        if not meta.get("boosted"):
            break
        report = evaluate_skill(current, skill_name, llm_args)
        meta["score_after"] = report.overall_score

    return current, report, boosts
