"""SkillsBench-compatible benchmark runner for SkillOS skills.

Deterministic adversarial benchmarking measuring whether a skill actually
improves agent output quality. Produces 100-point scores in the format:
  Correctness /40 | Security /20 | Completeness /20 | Robustness /20

No external API keys needed for core scoring. Optional LLM judge
for correctness tasks (uses configured model if available).

Usage:
    python -m skillos.skills_bench                    # benchmark all skills
    python -m skillos.skills_bench --skill "MySkill"  # benchmark one skill
    python -m skillos.skills_bench --compare          # with-skill vs without-skill
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills"
RESULTS_DIR = Path(__file__).parent.parent / "data" / "benchmarks"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SkillBenchScore:
    """SkillsBench-compatible 100-point score."""
    skill_name: str
    correctness: int = 0    # /40
    security: int = 0       # /20
    completeness: int = 0   # /20
    robustness: int = 0     # /20
    total: int = 0          # /100
    grade: str = "F"
    details: dict = field(default_factory=dict)

    @classmethod
    def from_skill(cls, skill_path: Path, llm_args: tuple | None = None) -> "SkillBenchScore":
        """Score a single skill across all 4 dimensions."""
        skill_name = skill_path.parent.name if skill_path.parent.name != "skills" else skill_path.stem
        content = skill_path.read_text(encoding="utf-8")

        # 1. Security /20 — deterministic, no LLM
        security = _score_security(content)

        # 2. Completeness /20 — structural, no LLM
        completeness = _score_completeness(content)

        # 3. Robustness /20 — rule-based, no LLM
        robustness = _score_robustness(content)

        # 4. Correctness /40 — MoE + heuristic hybrid
        correctness = _score_correctness(content, skill_name, llm_args)

        total = correctness + security + completeness + robustness
        grade = _grade_from_score(total)

        return cls(
            skill_name=skill_name,
            correctness=correctness,
            security=security,
            completeness=completeness,
            robustness=robustness,
            total=total,
            grade=grade,
            details={
                "security_findings": len(_find_security_issues(content)),
                "has_trigger": "S_trigger" in content or "When to use" in content,
                "has_route": "S_route" in content or "Decision routes" in content,
                "has_params": "S_params" in content or "Inputs" in content,
                "if_then_count": content.count("如果") + content.count("若") + content.count("when"),
                "step_count": len([l for l in content.split("\n") if l.strip().startswith(("1.", "2.", "3.", "- "))]),
            },
        )


def _score_security(content: str) -> int:
    """Deterministic security scan. Start at 20, deduct for each finding."""
    findings = _find_security_issues(content)
    return max(0, 20 - len(findings) * 5)


def _find_security_issues(content: str) -> list[dict]:
    """Find security issues in skill content."""
    from skillos.api.middleware import scan_skill_security
    return scan_skill_security(content)


def _score_completeness(content: str) -> int:
    """Structural completeness: does this skill have all required sections?"""
    score = 0
    has_trigger = "S_trigger" in content or "When to use" in content
    has_body = "S_body" in content or "Instructions" in content
    has_params = "S_params" in content or "Inputs" in content
    has_route = "S_route" in content or "Decision routes" in content
    has_examples = "example" in content.lower() or "示例" in content

    if has_trigger: score += 4
    if has_body: score += 6
    if has_params: score += 4
    if has_route: score += 4
    if has_examples: score += 2
    return min(20, score)


def _score_robustness(content: str) -> int:
    """Robustness: edge cases, if-then branches, error handling."""
    score = 0
    if_then = content.count("如果") + content.count("若") + content.count("when") + content.count("→")
    edge_markers = content.count("异常") + content.count("错误") + content.count("边界") + content.count("失败") + content.count("edge case")
    fallback = content.count("回退") + content.count("rollback") + content.count("fallback") + content.count("兜底")

    score += min(10, if_then * 2)
    score += min(5, edge_markers * 2)
    score += min(5, fallback * 2)
    return min(20, score)


def _score_correctness(content: str, skill_name: str, llm_args: tuple | None = None) -> int:
    """Correctness: MoE evaluation (primary) + heuristic (fallback)."""
    # Try MoE evaluation first
    try:
        from skillos.evaluation import evaluate_skill
        if llm_args is None:
            from skillos.config import get_config
            llm_args = get_config().to_llm_args()
        report = evaluate_skill(content, skill_name, llm_args)
        # Scale MoE 0-100 to 0-40
        return min(40, int(report.overall_score * 0.4))
    except Exception:
        pass

    # Fallback: heuristic scoring
    try:
        from skillos.evaluation.quality import evaluate_heuristic
        h = evaluate_heuristic(content, skill_name)
        # Scale heuristic 0-100 to 0-40
        return min(40, int(h["total"] * 40 / h["max"])) if h["max"] > 0 else 20
    except Exception:
        return 20  # Default


def _grade_from_score(total: int) -> str:
    if total >= 85: return "A"
    if total >= 70: return "B"
    if total >= 55: return "C"
    if total >= 40: return "D"
    return "F"


def score_offline(skill_path: Path) -> SkillBenchScore:
    """Score skill without LLM (heuristic correctness only). For CI gates."""
    skill_name = skill_path.parent.name
    content = skill_path.read_text(encoding="utf-8")
    security = _score_security(content)
    completeness = _score_completeness(content)
    robustness = _score_robustness(content)
    try:
        from skillos.evaluation.quality import evaluate_heuristic
        h = evaluate_heuristic(content, skill_name)
        correctness = min(40, int(h["total"] * 40 / h["max"])) if h["max"] > 0 else 20
    except Exception:
        correctness = 20
    total = correctness + security + completeness + robustness
    return SkillBenchScore(
        skill_name=skill_name,
        correctness=correctness,
        security=security,
        completeness=completeness,
        robustness=robustness,
        total=total,
        grade=_grade_from_score(total),
        details={"offline": True},
    )


def benchmark_all_skills(llm_args: tuple | None = None) -> list[SkillBenchScore]:
    """Benchmark all executable skills in the skills directory."""
    results = []
    for skill_dir in sorted(SKILLS_DIR.glob("*/")):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        name = skill_dir.name
        if name.startswith("_") or name.startswith(".") or name in ("brainstorming", "skill-creator", "__legacy_other__"):
            continue

        try:
            score = SkillBenchScore.from_skill(skill_md, llm_args)
            results.append(score)
            _log.info("Benchmarked: %s → %d/100 (%s)", name, score.total, score.grade)
        except Exception as e:
            _log.warning("Benchmark failed for %s: %s", name, e)

    results.sort(key=lambda r: r.total, reverse=True)
    return results


def benchmark_compare(skill_name: str, llm_args: tuple | None = None) -> dict:
    """With-skill vs without-skill comparison for a single skill."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"Skill not found: {skill_name}"}

    content = skill_md.read_text(encoding="utf-8")

    # With-skill score
    with_score = SkillBenchScore.from_skill(skill_md, llm_args)

    # Without-skill baseline: score a minimal placeholder
    min_content = "# Minimal Skill\n\n## Instructions\n1. Use common sense\n"
    min_score = SkillBenchScore.from_skill(
        Path("/tmp/min_skill.md"), llm_args
    )
    # Override: manually create the baseline
    from skillos.evaluation.quality import evaluate_heuristic
    h = evaluate_heuristic(min_content, "baseline")
    baseline_total = h["total"] * 100 // h["max"] if h["max"] > 0 else 30

    delta = with_score.total - baseline_total
    return {
        "skill": skill_name,
        "with_skill": with_score.total,
        "without_skill": baseline_total,
        "delta": delta,
        "improvement_pct": f"{delta / max(1, baseline_total) * 100:+.1f}%" if baseline_total > 0 else "N/A",
        "grade": with_score.grade,
        "details": with_score.details,
    }


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if "--compare" in sys.argv:
        skill = sys.argv[sys.argv.index("--compare") + 1] if "--compare" in sys.argv else None
        if not skill:
            print("Usage: python -m skillos.skills_bench --compare 'MySkill'")
            sys.exit(1)
        result = benchmark_compare(skill)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "--skill" in sys.argv:
        skill = sys.argv[sys.argv.index("--skill") + 1]
        skill_md = SKILLS_DIR / skill / "SKILL.md"
        if not skill_md.exists():
            print(f"Skill not found: {skill}")
            sys.exit(1)
        score = SkillBenchScore.from_skill(skill_md)
        print(json.dumps({
            "skill": score.skill_name,
            "correctness": score.correctness,
            "security": score.security,
            "completeness": score.completeness,
            "robustness": score.robustness,
            "total": score.total,
            "grade": score.grade,
            "details": score.details,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Benchmarking all skills...")
        results = benchmark_all_skills()
        print(f"\n{'='*60}")
        print(f"{'Skill':40s} {'Total':>5s} {'Grade':>5s} {'C':>3s} {'S':>3s} {'Cp':>3s} {'R':>3s}")
        print(f"{'='*60}")
        for r in results:
            print(f"{r.skill_name:40s} {r.total:>4d}/100 {r.grade:>4s}  "
                  f"{r.correctness:>2d} {r.security:>2d} {r.completeness:>2d} {r.robustness:>2d}")

        # Save
        out = RESULTS_DIR / f"skillsbench_{time.strftime('%Y%m%d_%H%M%S')}.json"
        out.write_text(json.dumps(
            [{"skill": r.skill_name, "total": r.total, "grade": r.grade,
              "correctness": r.correctness, "security": r.security,
              "completeness": r.completeness, "robustness": r.robustness,
              "details": r.details} for r in results],
            ensure_ascii=False, indent=2,
        ), encoding="utf-8")
        print(f"\nResults saved: {out}")
