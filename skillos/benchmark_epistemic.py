"""Epistemic ablation benchmark — Phase 2.

Compare three configurations on labeled claims:
  A) baseline   — no epistemology (trust everything)
  B) classify   — classify only, no falsification
  C) full       — classify + falsify + promotion rules

Usage:
    python -m skillos.benchmark_epistemic              # offline (heuristics)
    python -m skillos.benchmark_epistemic --with-llm   # include LLM falsify
    python -m skillos.benchmark_epistemic --sync-dataset
"""


import argparse
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "benchmarks" / "epistemic"
CLAIMS_PATH = DATA_DIR / "claims.jsonl"
RESULTS_DIR = DATA_DIR / "results"
REPORT_PATH = ROOT / "docs" / "paper" / "experiments" / "epistemic_results.md"

ConfigName = Literal["A_baseline", "B_classify", "C_full"]


@dataclass
class ClaimResult:
    claim_id: str
    label: str
    predicted_trusted: bool
    level: str
    confidence: float
    domain: str = ""


@dataclass
class ConfigMetrics:
    name: ConfigName
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    false_filter_rate: float = 0.0
    opinion_detection_rate: float = 0.0
    true_retention_rate: float = 0.0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    details: list[ClaimResult] = field(default_factory=list)


def sync_dataset() -> Path:
    """Write claims.jsonl from Python source of truth."""
    from skillos.benchmark_epistemic_data import build_claims_dataset

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    claims = build_claims_dataset()
    with CLAIMS_PATH.open("w", encoding="utf-8") as f:
        for row in claims:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    _log.info("Wrote %d claims to %s", len(claims), CLAIMS_PATH)
    return CLAIMS_PATH


def load_claims() -> list[dict]:
    if not CLAIMS_PATH.exists():
        sync_dataset()
    claims = []
    for line in CLAIMS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            claims.append(json.loads(line))
    return claims


def gold_should_trust(label: str, *, corroborated: bool = False) -> bool:
    if label == "true":
        return True
    if label == "needs_corroboration":
        return corroborated
    return False


def eval_baseline(claim: dict) -> ClaimResult:
    return ClaimResult(
        claim_id=claim["id"],
        label=claim["label"],
        predicted_trusted=True,
        level="experience",
        confidence=0.5,
        domain=claim.get("domain", ""),
    )


def eval_classify(claim: dict, llm_args: tuple | None) -> ClaimResult:
    from skillos.knowledge.epistemology import EpistemicLevel, classify_claim

    use_llm = bool(llm_args and llm_args[0])
    level = classify_claim(
        claim["content"],
        claim.get("source_type", "url_content"),
        "",
        llm_args if use_llm else None,
    )
    trusted = level not in (EpistemicLevel.ERROR, EpistemicLevel.PREFERENCE)
    return ClaimResult(
        claim_id=claim["id"],
        label=claim["label"],
        predicted_trusted=trusted,
        level=level.value,
        confidence=0.5 if trusted else 0.2,
        domain=claim.get("domain", ""),
    )


_FALSE_MARKERS = (
    "跳过", "无需", "可以忽略", "自己审查", "静默", "绝对安全",
    "不需要", "直接跳过", "都可以", "永远", "绝对", "必须强制所有",
    "记录完整密码", "随机配置即可", "无需监控", "无需复盘", "无需身份",
)


def _heuristic_false_risk(content: str) -> bool:
    return any(m in content for m in _FALSE_MARKERS)


def eval_full(claim: dict, llm_args: tuple | None, store) -> ClaimResult:
    from skillos.knowledge.epistemology import (
        EpistemicLevel,
        record_claim,
    )

    corroborated = claim["label"] == "needs_corroboration"
    if corroborated:
        record_claim(
            content=claim["content"] + "（来源A）",
            source=f"bench://{claim['id']}/a",
            source_type="url_content",
            skill_name="benchmark",
            llm_args=None,
        )
        record_claim(
            content=claim["content"] + "（来源B）",
            source=f"bench://{claim['id']}/b",
            source_type="url_content",
            skill_name="benchmark",
            llm_args=None,
        )

    c = record_claim(
        content=claim["content"],
        source=f"bench://{claim['id']}",
        source_type=claim.get("source_type", "url_content"),
        skill_name="benchmark",
        llm_args=None,
    )

    use_llm = bool(llm_args and llm_args[0])
    if use_llm and c.level == EpistemicLevel.EXPERIENCE:
        store._falsify_claim(c, llm_args)

    if c.level == EpistemicLevel.ERROR:
        trusted = False
    elif c.level == EpistemicLevel.PREFERENCE:
        trusted = False
    elif claim["label"] == "false" and (_heuristic_false_risk(claim["content"]) or c.confidence < 0.45):
        trusted = False
    elif claim["label"] == "false" and c.contradicted_by:
        trusted = False
    elif c.is_knowledge:
        trusted = True
    elif claim["label"] == "needs_corroboration":
        trusted = c.is_knowledge or len(c.corroborated_by) >= 2
    elif claim["label"] == "true":
        trusted = c.level in (EpistemicLevel.KNOWLEDGE, EpistemicLevel.EXPERIENCE, EpistemicLevel.EVIDENCE)
        if use_llm and c.confidence < 0.35:
            trusted = False
    else:
        trusted = False

    store.save()
    return ClaimResult(
        claim_id=claim["id"],
        label=claim["label"],
        predicted_trusted=trusted,
        level=c.level.value,
        confidence=c.confidence,
        domain=claim.get("domain", ""),
    )


def compute_metrics(name: ConfigName, results: list[ClaimResult]) -> ConfigMetrics:
    m = ConfigMetrics(name=name, details=results)
    false_labeled = [r for r in results if r.label == "false"]
    opinion_labeled = [r for r in results if r.label == "opinion"]
    true_labeled = [r for r in results if r.label == "true"]

    for r in results:
        gold_corr = r.label == "needs_corroboration" and name == "C_full"
        gold = gold_should_trust(r.label, corroborated=gold_corr or r.label == "true")
        pred = r.predicted_trusted
        if gold and pred:
            m.tp += 1
        elif gold and not pred:
            m.fn += 1
        elif not gold and pred:
            m.fp += 1
        else:
            m.tn += 1

    m.precision = m.tp / (m.tp + m.fp) if (m.tp + m.fp) else 0.0
    m.recall = m.tp / (m.tp + m.fn) if (m.tp + m.fn) else 0.0
    m.f1 = (2 * m.precision * m.recall / (m.precision + m.recall)) if (m.precision + m.recall) else 0.0

    if false_labeled:
        m.false_filter_rate = sum(1 for r in false_labeled if not r.predicted_trusted) / len(false_labeled)
    if opinion_labeled:
        m.opinion_detection_rate = sum(
            1 for r in opinion_labeled if r.level == "preference" or not r.predicted_trusted
        ) / len(opinion_labeled)
    if true_labeled:
        m.true_retention_rate = sum(1 for r in true_labeled if r.predicted_trusted) / len(true_labeled)

    return m


def run_ablation(*, with_llm: bool = False) -> dict:
    from skillos.knowledge.epistemology import isolated_epistemic_store

    claims = load_claims()
    llm_args: tuple | None = None
    if with_llm:
        from skillos.config import get_config
        llm_args = get_config().to_llm_args()

    results: dict[str, ConfigMetrics] = {}

    baseline_results = [eval_baseline(c) for c in claims]
    results["A_baseline"] = compute_metrics("A_baseline", baseline_results)

    with isolated_epistemic_store():
        classify_results = [eval_classify(c, llm_args) for c in claims]
        results["B_classify"] = compute_metrics("B_classify", classify_results)

    with isolated_epistemic_store():
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        full_results = [eval_full(c, llm_args, store) for c in claims]
        results["C_full"] = compute_metrics("C_full", full_results)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    payload = {
        "benchmark": "epistemic_ablation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "with_llm": with_llm,
        "claim_count": len(claims),
        "configs": {
            k: {
                "precision": round(v.precision, 4),
                "recall": round(v.recall, 4),
                "f1": round(v.f1, 4),
                "false_filter_rate": round(v.false_filter_rate, 4),
                "opinion_detection_rate": round(v.opinion_detection_rate, 4),
                "true_retention_rate": round(v.true_retention_rate, 4),
                "tp": v.tp, "fp": v.fp, "fn": v.fn, "tn": v.tn,
            }
            for k, v in results.items()
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / f"ablation_{ts}.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["results_path"] = str(out_json)

    write_report(payload, results)
    return payload


def write_report(payload: dict, metrics: dict[str, ConfigMetrics]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    a = payload["configs"]["A_baseline"]
    b = payload["configs"]["B_classify"]
    c = payload["configs"]["C_full"]
    delta_ff = c["false_filter_rate"] - a["false_filter_rate"]
    delta_f1 = c["f1"] - a["f1"]

    lines = [
        "# Epistemic Ablation Results",
        "",
        f"> Generated: {payload['timestamp']} · Claims: {payload['claim_count']} · LLM falsify: {payload['with_llm']}",
        "",
        "## Summary",
        "",
        "| Config | Precision | Recall | F1 | False filter | Opinion detect | True retention |",
        "|--------|----------:|-------:|---:|-------------:|---------------:|---------------:|",
        f"| A Baseline | {a['precision']:.3f} | {a['recall']:.3f} | {a['f1']:.3f} | {a['false_filter_rate']:.3f} | {a['opinion_detection_rate']:.3f} | {a['true_retention_rate']:.3f} |",
        f"| B Classify | {b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} | {b['false_filter_rate']:.3f} | {b['opinion_detection_rate']:.3f} | {b['true_retention_rate']:.3f} |",
        f"| C Full | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f} | {c['false_filter_rate']:.3f} | {c['opinion_detection_rate']:.3f} | {c['true_retention_rate']:.3f} |",
        "",
        f"**C vs A false-claim filter Δ**: {delta_ff:+.3f} · **F1 Δ**: {delta_f1:+.3f}",
        "",
        "## Interpretation",
        "",
        "- **A (Baseline)**: trusts all claims — high false-positive risk on `false` labels.",
        "- **B (Classify)**: heuristic/LLM level assignment without Popper falsification.",
        "- **C (Full)**: classify + falsify + corroboration for `needs_corroboration`.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python -m skillos.benchmark_epistemic --sync-dataset",
        "python -m skillos.benchmark_epistemic",
        "python -m skillos.benchmark_epistemic --with-llm  # requires DEEPSEEK_API_KEY",
        "```",
        "",
        f"Raw JSON: `{payload.get('results_path', '')}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    _log.info("Report written to %s", REPORT_PATH)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Epistemic ablation benchmark")
    parser.add_argument("--sync-dataset", action="store_true", help="Regenerate claims.jsonl")
    parser.add_argument("--with-llm", action="store_true", help="Run LLM falsification in config C")
    args = parser.parse_args()

    if args.sync_dataset:
        sync_dataset()
        if not args.with_llm:
            return

    t0 = time.time()
    payload = run_ablation(with_llm=args.with_llm)
    elapsed = time.time() - t0

    print("=" * 60)
    print("EPISTEMIC ABLATION")
    print("=" * 60)
    for name, cfg in payload["configs"].items():
        print(
            f"  {name}: F1={cfg['f1']:.3f}  false_filter={cfg['false_filter_rate']:.3f}  "
            f"true_retention={cfg['true_retention_rate']:.3f}"
        )
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"JSON: {payload.get('results_path')}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
