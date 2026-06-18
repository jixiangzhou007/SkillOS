#!/usr/bin/env python3
"""Offline CI gates for reference skills: structure, routing metadata, task routing logic.

No live LLM required. Exit 0 = all gates passed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = Path(__file__).resolve().parent / "verify_skill_bench_gates_output.txt"

REFERENCE_SKILLS = (
    "电商客服退款处理",
    "运营级CSV清洗工坊",
    "GitHub PR",
)

MIN_OFFLINE_TOTAL = 55
MIN_OFFLINE_COMPLETENESS = 14


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def check_routing_yaml(name: str, fh) -> bool:
    from skillos.skills_bench import SKILLS_DIR

    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        log(f"  [FAIL] missing skill: {name}", fh)
        return False
    text = path.read_text(encoding="utf-8")
    ok = "bench_categories:" in text
    if "dna_lineage:" not in text:
        log(f"  [WARN] {name}: no dna_lineage (run backfill_dna_lineage.py)")
    if not ok:
        log(f"  [FAIL] {name}: no bench_categories in YAML", fh)
        return False
    log(f"  [OK] {name}: bench_categories + routing metadata", fh)
    return True


def check_offline_structure(name: str, fh) -> bool:
    from skillos.skills_bench import SKILLS_DIR, score_offline

    path = SKILLS_DIR / name / "SKILL.md"
    score = score_offline(path)
    ok = score.total >= MIN_OFFLINE_TOTAL and score.completeness >= MIN_OFFLINE_COMPLETENESS
    flag = "OK" if ok else "FAIL"
    log(
        f"  [{flag}] {name}: offline {score.total}/100 "
        f"(C={score.completeness} S={score.security} R={score.robustness})",
        fh,
    )
    return ok


def check_routing_logic(fh) -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_skill_routing.py", "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        log(f"  [FAIL] test_skill_routing:\n{proc.stdout}\n{proc.stderr}", fh)
        return False
    log("  [OK] test_skill_routing.py", fh)
    return True


def check_domain_templates(fh) -> bool:
    from skillos.skills.domain_templates import DOMAIN_TEMPLATES, match_domain_template, resolve_domain_competition

    ok = True
    for tmpl in DOMAIN_TEMPLATES:
        probe = " ".join(tmpl.keywords[:3])
        matched = match_domain_template(probe)
        if not matched or matched.template_id != tmpl.template_id:
            log(f"  [FAIL] template match {tmpl.template_id}", fh)
            ok = False
        else:
            log(f"  [OK] template match {tmpl.template_id}", fh)

    sec = resolve_domain_competition("安全审计 应急响应 合规检查")
    if not sec.primary or sec.primary.template_id != "security-audit":
        log("  [FAIL] security audit must match security-audit not finance", fh)
        ok = False
    elif any(s.template.template_id == "finance-expense-audit" for s in sec.secondary):
        log("  [FAIL] security audit must not inherit finance-expense-audit", fh)
        ok = False
    else:
        log("  [OK] security audit disambiguation (no finance false match)", fh)
    return ok


def check_harm_gate_mock(fh) -> bool:
    """Routed compare: matched_delta >= 0 on domain tasks; harm from forced cross-domain inject."""
    from unittest.mock import patch

    from skillos.skills_bench import SKILLS_DIR
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, compare_with_without

    skill_md = SKILLS_DIR / "电商客服退款处理" / "SKILL.md"
    if not skill_md.exists():
        log("  [SKIP] harm gate: reference skill missing", fh)
        return True

    def fake_eval(task_id, **kwargs):
        task = next(t for t in SKILLSBENCH_TASKS if t.task_id == task_id)
        baseline = 70 if task.category == "workflow" else 65
        if not kwargs.get("skill_content"):
            return {
                "task_id": task_id,
                "category": task.category,
                "score": baseline,
                "max_score": 100,
                "grade": "B",
            }
        use = kwargs.get("inject_skill", True)
        score = baseline + 12 if use else baseline
        return {
            "task_id": task_id,
            "category": task.category,
            "score": score,
            "max_score": 100,
            "grade": "B",
        }

    with patch("skillos.skillsbench_tasks.run_task_evaluation", side_effect=fake_eval):
        result = compare_with_without(str(skill_md), routed=True)

    harm = result.get("harm_score", 0)
    delta = result.get("matched_delta", -999)
    ok = (
        "harm_score" in result
        and "cross_domain" in result
        and "bench_categories" in result
        and delta >= 0
        and len(result.get("cross_domain", [])) >= 1
    )
    flag = "OK" if ok else "FAIL"
    log(
        f"  [{flag}] routed compare mock: matched_delta={delta}, "
        f"harm_score={harm}, cross_domain={len(result.get('cross_domain', []))}",
        fh,
    )
    return ok


def check_dna_evolution(fh) -> bool:
    import tempfile
    import skillos.knowledge.dna_evolution as de
    import skillos.knowledge.dna_store as ds
    from skillos.knowledge.dna_evolution import evolve_domain_template_record, get_template_generation_boost
    from skillos.knowledge.dna_semver import bump_semver
    from skillos.knowledge.dna_store import get_template_version
    from skillos.skills.domain_templates import get_template

    assert bump_semver("1.0.0", "minor") == "1.1.0"
    content = """## Instructions
1. 离线 gate 进化步骤 A 校验订单流程完整性
2. 离线 gate 进化步骤 B 识别退款类型与金额上限
"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        templates = root / "domain_templates"
        templates.mkdir()
        ds.DNA_DIR = root
        ds.DOMAIN_TEMPLATES_DIR = templates
        de.DNA_DIR = root

        result = evolve_domain_template_record("workflow-refund", "gate-skill", content, 85)
        if not result.get("evolved"):
            log("  [FAIL] domain evolution did not bump template", fh)
            return False
        version = get_template_version("workflow-refund")
        tmpl = get_template("workflow-refund")
        boost = get_template_generation_boost("workflow-refund", tmpl.skeleton)
        if "进化补充" not in boost:
            log("  [FAIL] generation boost missing evolution overlay", fh)
            return False
        log(f"  [OK] domain evolution semver → {version}", fh)
        return True


def check_golden_set(fh) -> bool:
    from skillos.knowledge.dna_golden import run_golden_set

    report = run_golden_set()
    if not report.ok:
        failed = [c for c in report.cases if not c.passed]
        for c in failed[:5]:
            log(f"  [FAIL] {c.group}/{c.case_id}: {c.detail}", fh)
        return False
    log(f"  [OK] DNA golden set {report.passed}/{report.passed} passed", fh)
    return True


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    checks = [
        ("Routing YAML (reference skills)", lambda fh: all(check_routing_yaml(n, fh) for n in REFERENCE_SKILLS)),
        ("Offline structure scores", lambda fh: all(check_offline_structure(n, fh) for n in REFERENCE_SKILLS)),
        ("Domain templates", check_domain_templates),
        ("DNA evolution semver", check_dna_evolution),
        ("DNA golden set", check_golden_set),
        ("Routing unit tests", check_routing_logic),
        ("Harm / lift mock gate", check_harm_gate_mock),
    ]
    passed = 0
    with OUT.open("w", encoding="utf-8") as fh:
        log("SkillOS skill bench gates (offline)", fh)
        for label, fn in checks:
            log(f"\n== {label} ==", fh)
            if fn(fh):
                passed += 1
            else:
                log(f"CHECK FAILED: {label}", fh)
        log(f"\n{passed}/{len(checks)} gate groups passed", fh)
    print(f"\nWrote {OUT}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
