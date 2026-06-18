"""SkillOS Benchmark — pipeline evaluation and bare-LLM comparison.

Usage:
    python -m skillos.benchmark              # Run quick self-test
    python -m skillos.benchmark --url URL    # Benchmark a single URL
    python -m skillos.benchmark --full       # Run full test suite
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent.parent / "data" / "benchmarks"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════

SELF_TEST_CASES = [
    {
        "id": "self_test_001",
        "title": "Code Review Methodology",
        "content": """# How to Write Effective Code Reviews

Code review is a systematic process. Follow these steps:

1. **Understand Context**: Read PR description and linked issue first.
2. **Check Correctness**: Verify logic, edge cases, null handling.
3. **Review Style**: Naming, structure, formatting per team standards.
4. **Verify Tests**: Happy path + edge cases + error conditions.
5. **Give Actionable Feedback**: Be specific. "Use Optional[T] because caller can pass None" not "this is wrong".

Common pitfalls: skipping context, vague comments, only checking happy path.""",
    },
    {
        "id": "self_test_002",
        "title": "Incident Response Process",
        "content": """# Incident Response Runbook

When a production incident occurs:

1. **Triage (5 min)**: Determine severity. P0=customer-facing outage, P1=degraded, P2=minor.
2. **Mitigate (15 min)**: Stop the bleeding. Rollback if needed. Don't debug yet.
3. **Diagnose (30 min)**: Find root cause. Check logs, metrics, recent deploys.
4. **Fix & Deploy**: Implement fix, code review, deploy with monitoring.
5. **Postmortem (24h)**: Blameless document. What happened? Timeline. Action items.

Key: Mitigate before diagnose. Never skip postmortem.""",
    },
    {
        "id": "self_test_003",
        "title": "Customer Onboarding Flow",
        "content": """# Customer Onboarding SOP

New customer signup process:

1. **Verify Identity**: Email verification + optional phone 2FA.
2. **Collect Requirements**: What problem are they solving? Team size? Budget?
3. **Setup Account**: Create workspace, configure defaults, add team members.
4. **Import Data**: Migration from previous tool if applicable.
5. **Training Session**: 30-min walkthrough of key features.
6. **Follow-up (Day 7)**: Check in, answer questions, gather feedback.
7. **Handoff to CS**: Transfer to customer success for ongoing relationship.

Edge cases: failed verification → manual review queue. Data import failure → partial import + notify.""",
    },
]


# ═══════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════

def run_pipeline_benchmark(test_case: dict, llm_args: Optional[tuple] = None) -> dict:
    """Run a single test case through the 7-step pipeline and return results."""
    from skillos.skills.agent import SkillExtractionAgent

    if llm_args is None:
        from skillos.config import get_config
        cfg = get_config()
        llm_args = cfg.to_llm_args()

    t0 = time.time()
    agent = SkillExtractionAgent()

    reply, doc = agent.learn_from_url(
        f"benchmark://{test_case['id']}",
        test_case["content"],
        [],
        llm_args,
    )

    elapsed = time.time() - t0
    skill_content = doc.get("content", "") if doc else ""
    skill_name = doc.get("name", "") if doc else ""

    # Score with 10-dimension audit
    audit = {}
    try:
        from skillos.evolution.skillopt import audit_skill
        audit_result = audit_skill(skill_content, skill_name or test_case["id"], llm_args)
        audit = {"overall_score": audit_result.score, "summary": audit_result.summary,
                 "passed": audit_result.passed, "checks": len(audit_result.checks)}
    except Exception as e:
        audit = {"error": str(e), "overall_score": 0}

    return {
        "test_id": test_case["id"], "title": test_case["title"],
        "elapsed_s": round(elapsed, 1), "skill_name": skill_name,
        "skill_length": len(skill_content),
        "has_trigger": "S_trigger" in skill_content,
        "has_body": "S_body" in skill_content,
        "has_params": "S_params" in skill_content,
        "has_route": "S_route" in skill_content,
        "audit": audit, "skill_content": skill_content[:2000],
    }


def run_bare_llm_baseline(test_case: dict, llm_args: Optional[tuple] = None) -> dict:
    """Generate a skill using bare LLM (single prompt, no pipeline) for comparison."""
    from skillos.llm_client import call

    if llm_args is None:
        from skillos.config import get_config
        cfg = get_config()
        llm_args = cfg.to_llm_args()

    model = llm_args[2] if len(llm_args) > 2 else ""

    prompt = f"""Create a skill document from this content. Output in skill_doc format.

Content:
{test_case['content'][:2000]}

Output format:
```skill_doc
# Skill Name: <name>
## Core Problem
<one sentence>
## S_body
<steps>
## S_trigger
- keywords: <keywords>
- context: <context>
## S_params
- <param>: <description>
```"""

    t0 = time.time()
    raw = call(prompt, model=model, max_tokens=800, temperature=0.3)
    elapsed = time.time() - t0

    m = __import__('re').search(r"```skill_doc\s*\n(.*?)```", raw, __import__('re').DOTALL | __import__('re').IGNORECASE)
    content = m.group(1).strip() if m else raw.strip()

    audit = {}
    try:
        from skillos.evolution.skillopt import audit_skill
        audit_result = audit_skill(content, test_case["id"], llm_args)
        audit = {"overall_score": audit_result.score, "summary": audit_result.summary,
                 "passed": audit_result.passed, "checks": len(audit_result.checks)}
    except Exception as e:
        audit = {"error": str(e), "overall_score": 0}

    return {
        "test_id": test_case["id"], "title": test_case["title"],
        "elapsed_s": round(elapsed, 1), "skill_length": len(content),
        "has_trigger": "S_trigger" in content, "has_body": "S_body" in content,
        "has_params": "S_params" in content, "has_route": "S_route" in content,
        "audit": audit, "skill_content": content[:2000],
    }


def run_full_benchmark(test_cases: list[dict] = None):
    """Run full benchmark: pipeline vs bare LLM on all test cases."""
    if test_cases is None:
        test_cases = SELF_TEST_CASES

    from skillos.config import get_config
    cfg = get_config()
    llm_args = cfg.to_llm_args()

    results = {
        "benchmark": "skillos_pipeline_vs_bare_llm",
        "model": cfg.model,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_count": len(test_cases),
        "pipeline": [],
        "baseline": [],
        "comparison": {},
    }

    print(f"Running benchmark on {len(test_cases)} test cases with model: {cfg.model}")
    print("=" * 60)

    for tc in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {tc['title']} ({tc['id']})")
        print(f"{'='*60}")

        # Pipeline
        print("  Pipeline (7-step)...")
        pipe_result = run_pipeline_benchmark(tc, llm_args)
        results["pipeline"].append(pipe_result)
        pipe_audit = pipe_result.get("audit", {})
        pipe_score = pipe_audit.get("overall_score", pipe_audit.get("score", 0))
        print(f"    Name: {pipe_result['skill_name']}, Length: {pipe_result['skill_length']} chars, "
              f"Time: {pipe_result['elapsed_s']}s, Score: {pipe_score}")
        print(f"    Trigger: {pipe_result['has_trigger']}, Body: {pipe_result['has_body']}, "
              f"Params: {pipe_result['has_params']}, Route: {pipe_result['has_route']}")

        # Baseline
        print("  Baseline (bare LLM)...")
        base_result = run_bare_llm_baseline(tc, llm_args)
        results["baseline"].append(base_result)
        base_audit = base_result.get("audit", {})
        base_score = base_audit.get("overall_score", base_audit.get("score", 0))
        print(f"    Length: {base_result['skill_length']} chars, Time: {base_result['elapsed_s']}s, Score: {base_score}")
        print(f"    Trigger: {base_result['has_trigger']}, Body: {base_result['has_body']}, "
              f"Params: {base_result['has_params']}, Route: {base_result['has_route']}")

    # Comparison summary
    pipe_scores = [r.get("audit", {}).get("overall_score", 0) for r in results["pipeline"]]
    base_scores = [r.get("audit", {}).get("overall_score", 0) for r in results["baseline"]]

    pipe_avg = sum(pipe_scores) / len(pipe_scores) if pipe_scores else 0
    base_avg = sum(base_scores) / len(base_scores) if base_scores else 0

    pipe_time = sum(r["elapsed_s"] for r in results["pipeline"])
    base_time = sum(r["elapsed_s"] for r in results["baseline"])

    results["comparison"] = {
        "pipeline_avg_score": round(pipe_avg, 1),
        "baseline_avg_score": round(base_avg, 1),
        "score_delta": round(pipe_avg - base_avg, 1),
        "pipeline_total_time_s": round(pipe_time, 1),
        "baseline_total_time_s": round(base_time, 1),
        "pipeline_slower_x": round(pipe_time / base_time, 1) if base_time > 0 else 0,
        "pipeline_has_route_rate": sum(1 for r in results["pipeline"] if r["has_route"]) / len(results["pipeline"]),
        "baseline_has_route_rate": sum(1 for r in results["baseline"] if r["has_route"]) / len(results["baseline"]),
    }

    c = results["comparison"]
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"  Pipeline avg score:  {c['pipeline_avg_score']}")
    print(f"  Baseline avg score:  {c['baseline_avg_score']}")
    print(f"  Score delta:         {c['score_delta']:+} (pipeline vs baseline)")
    print(f"  Pipeline time:       {c['pipeline_total_time_s']}s (baseline: {c['baseline_total_time_s']}s)")
    print(f"  Pipeline slower:     {c['pipeline_slower_x']}x")
    print(f"  Pipeline S_route:    {c['pipeline_has_route_rate']:.0%}")
    print(f"  Baseline S_route:    {c['baseline_has_route_rate']:.0%}")

    # Save results
    out_file = RESULTS_DIR / f"benchmark_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved: {out_file}")

    return results


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if "--url" in sys.argv:
        url = sys.argv[sys.argv.index("--url") + 1]
        from skillos.utils.web_fetch import fetch
        content = fetch(url)
        if not content:
            print(f"Failed to fetch: {url}")
            sys.exit(1)
        tc = {"id": "url_test", "title": url[:60], "content": content}
        run_full_benchmark([tc])
    else:
        print("Running self-test benchmark (3 built-in test cases)...\n")
        run_full_benchmark()
