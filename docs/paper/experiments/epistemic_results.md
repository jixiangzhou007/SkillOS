# Epistemic Ablation Results

> Generated: 2026-06-19T03:06:09.448122+00:00 · Claims: 100 · LLM falsify: False

## Summary

| Config | Precision | Recall | F1 | False filter | Opinion detect | True retention |
|--------|----------:|-------:|---:|-------------:|---------------:|---------------:|
| A Baseline | 0.300 | 1.000 | 0.462 | 0.000 | 0.000 | 1.000 |
| B Classify | 0.357 | 1.000 | 0.526 | 0.000 | 0.800 | 1.000 |
| C Full | 1.000 | 0.600 | 0.750 | 1.000 | 1.000 | 1.000 |

**C vs A false-claim filter Δ**: +1.000 · **F1 Δ**: +0.288

## Interpretation

- **A (Baseline)**: trusts all claims — high false-positive risk on `false` labels.
- **B (Classify)**: heuristic/LLM level assignment without Popper falsification.
- **C (Full)**: classify + falsify + corroboration for `needs_corroboration`.

## Reproduce

```bash
python -m skillos.benchmark_epistemic --sync-dataset
python -m skillos.benchmark_epistemic
python -m skillos.benchmark_epistemic --with-llm  # requires DEEPSEEK_API_KEY
```

Raw JSON: `D:\SkillOS\data\benchmarks\epistemic\results\ablation_20260619_030609.json`
