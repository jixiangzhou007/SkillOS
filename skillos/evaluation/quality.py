"""Unified skill quality scoring — three layers, one vocabulary.

| Layer            | Scale   | When                    | Official? |
|------------------|---------|-------------------------|-----------|
| draft_readiness  | 1–5     | Socratic extraction     | No        |
| heuristic        | 0–100   | CI / acceptance scripts | No        |
| moe              | 0–100   | Final SKILL.md          | Yes       |

The **official** product quality score is MoE `overall_score` (≥70 pass).
Heuristic is a fast structural proxy for regression gates.
Draft 1–5 scores are conversational readiness hints only — never compare to MoE.
"""


import re
from typing import Any

SCORE_LAYERS: dict[str, str] = {
    "draft_readiness": "对话萃取阶段各维度就绪度（1–5），仅供追问引导，非终稿分",
    "heuristic": "规则启发式结构分（0–100），用于 CI/验收脚本，无 LLM",
    "moe": "MoE 多专家终稿质量分（0–100），产品官方质量分，需 LLM",
}

OFFICIAL_LAYER = "moe"
MOE_PASS_THRESHOLD = 70


def grade_from_score(total: int, *, max_score: int = 100) -> str:
    """Map 0–100 (or scaled) total to letter grade."""
    if max_score != 100:
        total = int(100 * total / max_score) if max_score else 0
    if total >= 85:
        return "A"
    if total >= 70:
        return "B"
    if total >= 55:
        return "C"
    if total >= 40:
        return "D"
    return "F"


def draft_readiness_label(score_1_to_5: int) -> str:
    """Human label for in-conversation draft dimension scores."""
    score_1_to_5 = max(1, min(5, score_1_to_5))
    labels = {
        1: "空白/缺失",
        2: "骨架",
        3: "可用草稿",
        4: "接近 v1.0",
        5: "就绪可生成",
    }
    return labels[score_1_to_5]


def evaluate_heuristic(
    text: str,
    skill_name: str = "",
    *,
    expected_topics: list[str] | None = None,
) -> dict[str, Any]:
    """Rule-based 0–100 score for CI and acceptance scripts (no LLM)."""
    scores: dict[str, tuple[int, int, str]] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        yaml_part = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) > 2 else text
    else:
        yaml_part = ""

    struct_pts = 0
    struct_notes: list[str] = []
    if "name:" in yaml_part or "description:" in yaml_part:
        struct_pts += 8
    else:
        struct_notes.append("缺少 YAML name/description")
    for sec in ("S_body", "Instructions", "S_route", "Decision routes", "S_trigger", "When to use"):
        if sec in body:
            struct_pts += 3
            break
    sec_hits = sum(
        1 for s in ("S_body", "Instructions", "S_route", "S_trigger", "S_params", "Inputs") if s in body
    )
    struct_pts += min(10, sec_hits * 2)
    if re.search(r"^\d+\.", body, re.MULTILINE):
        struct_pts += 4
    scores["structure"] = (min(25, struct_pts), 25, "; ".join(struct_notes) or "结构完整")

    exec_pts = 0
    if_then = len(re.findall(r"如果|若|when|→|->", body, re.I))
    exec_pts += min(10, if_then * 2)
    steps = len(re.findall(r"^\d+\.", body, re.MULTILINE))
    exec_pts += min(10, steps * 2)
    if "升级" in body and "知识库" in body:
        exec_pts += 5
    scores["executability"] = (min(25, exec_pts), 25, f"{steps} 步骤, {if_then} 分支/条件")

    topics = expected_topics or []
    if topics:
        found = [t for t in topics if t in body]
        cov_pts = int(25 * len(found) / len(topics))
        cov_note = f"命中 {len(found)}/{len(topics)}: {', '.join(found)}"
    else:
        cov_pts = 0
        cov_note = "未提供 expected_topics"
    scores["coverage"] = (cov_pts, 25, cov_note)

    port_pts = 0
    if "draft: true" not in text:
        port_pts += 5
    if "description:" in yaml_part or "tool_description" in body:
        port_pts += 5
    if "Instructions" in body or "S_body" in body:
        port_pts += 5
    scores["portability"] = (port_pts, 15, "非草稿" if "draft: true" not in text else "仍为草稿")

    pending = body.count("[待确认]")
    clarity_pts = max(0, 10 - pending * 2)
    scores["clarity"] = (clarity_pts, 10, f"[待确认] x{pending}")

    total = sum(v[0] for v in scores.values())
    max_total = sum(v[1] for v in scores.values())

    return {
        "layer": "heuristic",
        "skill_name": skill_name,
        "total": total,
        "max": max_total,
        "grade": grade_from_score(total, max_score=max_total),
        "official": False,
        "dimensions": {
            k: {"score": v[0], "max": v[1], "note": v[2]} for k, v in scores.items()
        },
    }


def build_quality_payload(
    *,
    skill_name: str,
    body: str,
    heuristic: dict[str, Any] | None = None,
    moe: dict[str, Any] | None = None,
    expected_topics: list[str] | None = None,
) -> dict[str, Any]:
    """Unified quality block for API responses."""
    if heuristic is None and body:
        heuristic = evaluate_heuristic(body, skill_name, expected_topics=expected_topics)

    official_score = None
    official_grade = None
    official_passed = None
    if moe:
        official_score = moe.get("overall_score")
        official_grade = grade_from_score(int(official_score or 0))
        official_passed = moe.get("passed", (official_score or 0) >= MOE_PASS_THRESHOLD)

    return {
        "layers": SCORE_LAYERS,
        "official_layer": OFFICIAL_LAYER,
        "official_score": official_score,
        "official_grade": official_grade,
        "official_passed": official_passed,
        "heuristic": heuristic,
        "moe": moe,
        "note": (
            "对话中 1–5 分是 draft_readiness，不与 MoE 对比；"
            f"终稿官方分 = MoE overall_score（≥{MOE_PASS_THRESHOLD} 通过）；"
            "heuristic 仅用于 CI/脚本快速回归。"
        ),
    }
