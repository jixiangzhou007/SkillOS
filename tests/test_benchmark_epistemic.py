"""Tests for epistemic ablation benchmark."""

from skillos.benchmark_epistemic import (
    compute_metrics,
    eval_baseline,
    eval_classify,
    eval_full,
    load_claims,
    run_ablation,
    sync_dataset,
)
from skillos.knowledge.epistemology import isolated_epistemic_store


def test_dataset_has_100_claims():
    sync_dataset()
    claims = load_claims()
    assert len(claims) == 100
    labels = {c["label"] for c in claims}
    assert labels == {"true", "false", "opinion", "needs_corroboration"}


def test_baseline_trusts_everything():
    claims = load_claims()[:5]
    for c in claims:
        r = eval_baseline(c)
        assert r.predicted_trusted is True


def test_classify_rejects_opinion_heuristic():
    claim = {
        "id": "t1",
        "content": "我觉得代码审查应该只看风格",
        "label": "opinion",
        "domain": "code_review",
        "source_type": "url_content",
    }
    r = eval_classify(claim, None)
    assert r.level == "preference"
    assert r.predicted_trusted is False


def test_full_filters_false_claim_offline():
    claim = {
        "id": "t2",
        "content": "代码审查时可以直接跳过测试检查以节省时间",
        "label": "false",
        "domain": "code_review",
        "source_type": "url_content",
    }
    with isolated_epistemic_store():
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        r = eval_full(claim, None, store)
    assert r.predicted_trusted is False or r.level != "knowledge"


def test_run_ablation_offline():
    sync_dataset()
    payload = run_ablation(with_llm=False)
    assert payload["claim_count"] == 100
    assert "A_baseline" in payload["configs"]
    assert "C_full" in payload["configs"]
    a = payload["configs"]["A_baseline"]
    c = payload["configs"]["C_full"]
    assert a["false_filter_rate"] == 0.0
    assert c["false_filter_rate"] >= a["false_filter_rate"]


def test_compute_metrics_f1():
    from skillos.benchmark_epistemic import ClaimResult, ConfigName

    results = [
        ClaimResult("1", "true", True, "experience", 0.5),
        ClaimResult("2", "false", False, "experience", 0.3),
    ]
    m = compute_metrics("C_full", results)
    assert m.tp >= 1
    assert m.f1 > 0
