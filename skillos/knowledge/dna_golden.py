"""DNA + routing golden set runner for CI (offline, no LLM)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

GOLDEN_SET_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "benchmarks" / "dna" / "golden_set.json"
)
BASELINE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "benchmarks" / "dna" / "baseline.json"
)
NIGHTLY_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "benchmarks" / "dna" / "nightly"
)


@dataclass
class GoldenCaseResult:
    group: str
    case_id: str
    passed: bool
    detail: str = ""


@dataclass
class GoldenRunReport:
    passed: int = 0
    failed: int = 0
    cases: list[GoldenCaseResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "ok": self.ok,
            "pass_rate": round(self.passed / max(1, self.passed + self.failed), 3),
            "cases": [
                {"group": c.group, "id": c.case_id, "passed": c.passed, "detail": c.detail}
                for c in self.cases
            ],
        }


def load_golden_set(path: Path | None = None) -> dict[str, Any]:
    p = path or GOLDEN_SET_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def load_baseline(path: Path | None = None) -> dict[str, Any]:
    p = path or BASELINE_PATH
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _record(report: GoldenRunReport, group: str, case_id: str, ok: bool, detail: str = "") -> None:
    report.cases.append(GoldenCaseResult(group=group, case_id=case_id, passed=ok, detail=detail))
    if ok:
        report.passed += 1
    else:
        report.failed += 1


def _run_dna_detection(cases: list[dict], report: GoldenRunReport) -> None:
    from skillos.knowledge.philosophical_dna import detect_philosophical_dna

    for case in cases:
        det = detect_philosophical_dna(
            case["topic"],
            domain_key=case.get("domain_key", ""),
        )
        ids = [p.method_id for p in det]
        ok = True
        detail_parts: list[str] = []
        for mid in case.get("expect_contains", []):
            if mid not in ids:
                ok = False
                detail_parts.append(f"missing {mid}")
        if case.get("expect_primary") and (not ids or ids[0] != case["expect_primary"]):
            ok = False
            detail_parts.append(f"primary={ids[0] if ids else None}")
        _record(report, "dna_detection", case["id"], ok, "; ".join(detail_parts) or f"ids={ids[:3]}")


def _run_domain_templates(cases: list[dict], report: GoldenRunReport) -> None:
    from skillos.skills.domain_templates import resolve_domain_competition

    for case in cases:
        comp = resolve_domain_competition(case["topic"], top_k=3)
        ok = comp.primary is not None and comp.primary.template_id == case["expect_primary"]
        detail = comp.primary.template_id if comp.primary else "none"
        if ok and case.get("forbid_secondary"):
            sec_ids = [s.template.template_id for s in comp.secondary]
            for bad in case["forbid_secondary"]:
                if bad in sec_ids:
                    ok = False
                    detail += f"; forbidden secondary {bad}"
        _record(report, "domain_templates", case["id"], ok, detail)


def _run_reference_skills(cases: list[dict], report: GoldenRunReport) -> None:
    from skillos.knowledge.skill_routing import parse_bench_categories_from_skill
    from skillos.skills_bench import SKILLS_DIR, score_offline

    for case in cases:
        name = case["skill"]
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            _record(report, "reference_skills", name, False, "missing SKILL.md")
            continue
        text = path.read_text(encoding="utf-8")
        score = score_offline(path)
        cats = parse_bench_categories_from_skill(text)
        ok = (
            score.total >= case.get("min_total", 55)
            and score.completeness >= case.get("min_completeness", 14)
        )
        for req in case.get("require_categories", []):
            if req not in cats:
                ok = False
        detail = f"total={score.total} C={score.completeness} cats={cats}"
        _record(report, "reference_skills", name, ok, detail)


def _run_routed_compare_mock(cfg: dict, skills: list[str], report: GoldenRunReport) -> None:
    from unittest.mock import patch

    from skillos.skills_bench import SKILLS_DIR
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, compare_with_without

    def fake_eval(task_id, **kwargs):
        task = next(t for t in SKILLSBENCH_TASKS if t.task_id == task_id)
        base = 60
        if kwargs.get("skill_content") and kwargs.get("inject_skill", True):
            score = base + 12
        else:
            score = base
        return {
            "task_id": task_id,
            "category": task.category,
            "score": score,
            "max_score": 100,
            "grade": "B",
        }

    for name in skills:
        skill_md = SKILLS_DIR / name / "SKILL.md"
        if not skill_md.exists():
            _record(report, "routed_compare_mock", name, False, "missing")
            continue
        with patch("skillos.skillsbench_tasks.run_task_evaluation", side_effect=fake_eval):
            result = compare_with_without(str(skill_md), routed=True)
        ok = True
        detail_parts: list[str] = []
        if result.get("matched_delta", -999) < cfg.get("min_matched_delta", 0):
            ok = False
            detail_parts.append(f"matched_delta={result.get('matched_delta')}")
        if cfg.get("require_harm_field") and "harm_score" not in result:
            ok = False
            detail_parts.append("no harm_score")
        if len(result.get("cross_domain", [])) < cfg.get("min_cross_domain", 1):
            ok = False
            detail_parts.append("cross_domain empty")
        detail = "; ".join(detail_parts) or f"delta={result.get('matched_delta')} harm={result.get('harm_score')}"
        _record(report, "routed_compare_mock", name, ok, detail)


def run_golden_set(path: Path | None = None) -> GoldenRunReport:
    """Execute full offline golden set."""
    data = load_golden_set(path)
    report = GoldenRunReport()
    _run_dna_detection(data.get("dna_detection", []), report)
    _run_domain_templates(data.get("domain_templates", []), report)
    _run_reference_skills(data.get("reference_skills", []), report)
    mock_cfg = data.get("routed_compare_mock", {})
    skill_names = [c["skill"] for c in data.get("reference_skills", [])]
    _run_routed_compare_mock(mock_cfg, skill_names, report)
    return report


def assert_golden_set(path: Path | None = None) -> GoldenRunReport:
    report = run_golden_set(path)
    if not report.ok:
        failed = [c for c in report.cases if not c.passed]
        lines = [f"  [{c.group}] {c.case_id}: {c.detail}" for c in failed]
        raise AssertionError(
            f"DNA golden set failed ({report.failed}/{report.passed + report.failed}):\n"
            + "\n".join(lines)
        )
    return report
