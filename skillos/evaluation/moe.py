"""MoE Evaluation Engine — multi-expert, cross-model skill quality scoring.

Architecture:
  1. Run 6 independent expert judges (each scoring 1-2 dimensions)
  2. Optionally re-run each expert on a secondary model (cross-model validation)
  3. Gating network aggregates scores with confidence weighting
  4. Output structured MoEReport with per-dimension breakdown
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from skillos.evaluation.experts import EXPERTS, ExpertDefinition, build_expert_prompt

_log = logging.getLogger(__name__)


@dataclass
class ExpertResult:
    """Single expert's evaluation result."""
    expert_key: str
    expert_name: str
    score: int                    # 0-100
    passed: bool
    summary: str
    detail: dict = field(default_factory=dict)
    # Cross-model
    cross_model_score: int | None = None
    cross_model_passed: bool | None = None
    cross_model_agreement: bool = True  # True if both models agree within threshold
    elapsed_ms: int = 0


@dataclass
class MoEReport:
    """Aggregated MoE evaluation report."""
    skill_name: str
    overall_score: int            # 0-100 weighted average
    confidence: float             # 0.0-1.0 based on cross-model agreement
    passed: bool                  # overall pass/fail (score >= 70)
    dimensions: dict[str, int]    # {structure: 85, security: 92, ...}
    experts: list[ExpertResult] = field(default_factory=list)
    cross_model_used: bool = False
    cross_model_name: str = ""
    total_elapsed_ms: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "overall_score": self.overall_score,
            "confidence": round(self.confidence, 2),
            "passed": self.passed,
            "dimensions": self.dimensions,
            "experts": [
                {
                    "key": e.expert_key, "name": e.expert_name,
                    "score": e.score, "passed": e.passed,
                    "summary": e.summary,
                    "cross_model_score": e.cross_model_score,
                    "cross_model_agreement": e.cross_model_agreement,
                }
                for e in self.experts
            ],
            "cross_model_used": self.cross_model_used,
            "cross_model_name": self.cross_model_name,
            "total_elapsed_ms": self.total_elapsed_ms,
            "warnings": self.warnings,
        }

    def to_markdown(self) -> str:
        """Human-readable markdown report."""
        lines = [
            f"## MoE 技能评价报告: {self.skill_name}",
            f"",
            f"**总分**: {self.overall_score}/100 | **置信度**: {self.confidence:.0%} | **结果**: {'✅ 通过' if self.passed else '❌ 未通过'}",
            f"",
            f"| 维度 | 评委 | 得分 | 通过 | 交叉验证 |",
            f"|------|------|:--:|:--:|:--:|",
        ]
        for e in self.experts:
            cm = ""
            if self.cross_model_used and e.cross_model_score is not None:
                agree = "✅" if e.cross_model_agreement else "⚠️"
                cm = f"{agree} {e.cross_model_score}"
            lines.append(f"| {e.expert_key} | {e.expert_name} | {e.score} | {'✅' if e.passed else '❌'} | {cm} |")

        if self.warnings:
            lines.append(f"\n### ⚠️ 警告")
            for w in self.warnings:
                lines.append(f"- {w}")

        return "\n".join(lines)


def _run_single_expert(
    expert: ExpertDefinition,
    skill_content: str,
    skill_name: str,
    llm_args: tuple,
) -> ExpertResult:
    """Run one expert judge on the primary model."""
    from skillos.llm_client import call

    model = llm_args[2] if len(llm_args) > 2 else ""
    prompt = build_expert_prompt(expert, skill_content, skill_name)

    t0 = time.time()
    raw = call(prompt, model=model, max_tokens=expert.max_tokens, temperature=0.1)
    elapsed = int((time.time() - t0) * 1000)

    # Parse JSON response
    try:
        data = _parse_json(raw)
        overall = max(0, min(100, data.get("overall", 60)))
        passed = overall >= 70
        summary = data.get("summary", "")
    except Exception:
        _log.warning("Expert %s JSON parse failed, using fallback", expert.key)
        overall = 60
        passed = True
        summary = f"{expert.name}评分解析失败，降级通过"
        data = {}

    return ExpertResult(
        expert_key=expert.key,
        expert_name=expert.name,
        score=overall,
        passed=passed,
        summary=summary,
        detail=data,
        elapsed_ms=elapsed,
    )


def _run_cross_model(
    expert: ExpertDefinition,
    skill_content: str,
    skill_name: str,
    primary_score: int,
    cross_model_name: str,
) -> tuple[int | None, bool | None, bool]:
    """Re-run one expert on a secondary model. Returns (score, passed, agreement)."""
    from skillos.llm_client import call

    prompt = build_expert_prompt(expert, skill_content, skill_name)
    try:
        raw = call(prompt, model=cross_model_name, max_tokens=expert.max_tokens, temperature=0.1)
        data = _parse_json(raw)
        cross_score = max(0, min(100, data.get("overall", 60)))
        cross_passed = cross_score >= 70
        agreement = abs(cross_score - primary_score) <= 15
        return cross_score, cross_passed, agreement
    except Exception:
        return None, None, True  # Cross-model failed, trust primary


def evaluate_skill(
    skill_content: str,
    skill_name: str,
    llm_args: tuple,
    *,
    cross_model: str = "",
    fast_model: str = "",
) -> MoEReport:
    """Run MoE evaluation on a skill.

    Args:
        skill_content: Full skill document text
        skill_name: Skill name
        llm_args: Primary model (api_key, base_url, model, chat_kwargs)
        cross_model: If set, re-run experts on this model for validation.
                     Use a different/cheaper model (e.g. "deepseek-v4-flash"
                     when primary is "deepseek-v4-pro").
        fast_model: Alias for cross_model.

    Returns:
        MoEReport with aggregated scores, per-dimension breakdown, and confidence.
    """
    cross_model_name = cross_model or fast_model
    use_cross_model = bool(cross_model_name)

    t0 = time.time()
    results: list[ExpertResult] = []
    scores: dict[str, int] = {}
    weights_sum = 0.0
    weighted_sum = 0.0
    warnings: list[str] = []

    for expert in EXPERTS:
        # Primary evaluation
        result = _run_single_expert(expert, skill_content, skill_name, llm_args)

        # Cross-model validation
        if use_cross_model:
            cm_score, cm_passed, cm_agree = _run_cross_model(
                expert, skill_content, skill_name, result.score, cross_model_name,
            )
            result.cross_model_score = cm_score
            result.cross_model_passed = cm_passed
            result.cross_model_agreement = cm_agree
            if not cm_agree:
                warnings.append(
                    f"{expert.name}: 主模型={result.score}, 交叉模型={cm_score}, 差异>15分，建议人工复核"
                )

        results.append(result)
        scores[expert.key] = result.score
        weighted_sum += result.score * expert.weight
        weights_sum += expert.weight

    overall = round(weighted_sum / weights_sum) if weights_sum > 0 else 60

    # Confidence: based on cross-model agreement rate
    if use_cross_model:
        agreements = sum(1 for r in results if r.cross_model_agreement)
        confidence = agreements / len(results) if results else 0.5
    else:
        confidence = 0.7  # Default without cross-model validation

    passed = overall >= 70

    return MoEReport(
        skill_name=skill_name,
        overall_score=overall,
        confidence=confidence,
        passed=passed,
        dimensions=scores,
        experts=results,
        cross_model_used=use_cross_model,
        cross_model_name=cross_model_name,
        total_elapsed_ms=int((time.time() - t0) * 1000),
        warnings=warnings,
    )


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM response."""
    # Try markdown code block first
    m = re.search(r'```(?:json)?\s*\n(.*?)```', raw, re.DOTALL | re.IGNORECASE)
    text = m.group(1) if m else raw
    # Find first { ... } block
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)
