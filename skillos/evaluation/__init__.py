"""SkillOS MoE Evaluation — multi-expert, cross-model skill quality scoring.

Six independent expert judges, each scoring 1-2 dimensions on a focused prompt.
Gating network aggregates scores with confidence weighting.
Cross-model validation: run experts on a secondary model and compare.

Usage:
    from skillos.evaluation import evaluate_skill

    report = evaluate_skill(skill_content, skill_name, llm_args)
    print(report.overall_score)   # 0-100
    print(report.confidence)      # 0.0-1.0
    print(report.dimensions)      # {"structure": 85, "security": 92, ...}
"""

from skillos.evaluation.moe import ExpertResult, MoEReport, evaluate_skill
from skillos.evaluation.quality import (
    MOE_PASS_THRESHOLD,
    OFFICIAL_LAYER,
    SCORE_LAYERS,
    build_quality_payload,
    draft_readiness_label,
    evaluate_heuristic,
    grade_from_score,
)

__all__ = [
    "evaluate_skill",
    "MoEReport",
    "ExpertResult",
    "SCORE_LAYERS",
    "OFFICIAL_LAYER",
    "MOE_PASS_THRESHOLD",
    "evaluate_heuristic",
    "build_quality_payload",
    "draft_readiness_label",
    "grade_from_score",
]
