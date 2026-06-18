"""Domain delta metrics for quick8 (offline)."""

from skillos.benchmark_local import _domain_metrics


def test_domain_metrics_positive():
    m = _domain_metrics([
        {"task_id": "a", "with_score": 100, "without_score": 50, "skill_used": True},
        {"task_id": "b", "with_score": 80, "without_score": 80, "skill_used": False},
    ])
    assert m["domain_delta"] == 50
    assert m["domain_improvement_pct"] == "+100.0%"
    assert m["harm_tasks"] == []


def test_domain_metrics_harm():
    m = _domain_metrics([
        {"task_id": "x", "with_score": 50, "without_score": 100, "skill_used": True},
    ])
    assert m["harm_tasks"] == ["x"]
    assert m["domain_improvement_pct"] == "-50.0%"
