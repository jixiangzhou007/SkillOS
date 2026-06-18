# 本地 SkillsBench 评测指南

> **更新**：2026-06-18 · 与 [`SKILLSBENCH_CI.md`](SKILLSBENCH_CI.md)（官方 CI）互补

## 轨道对照

| 轨道 | 环境 | 用途 |
|------|------|------|
| **本地 Quick8** | Windows/macOS/Linux + `DEEPSEEK_API_KEY` | 日常回归、域内 Δ、ablation |
| **官方 BenchFlow** | GitHub Actions Linux + Docker | 权威 pass rate |

## 核心脚本

| 脚本 | 说明 | 需 API Key |
|------|------|:----------:|
| [`scripts/run_bench_regression.py`](../scripts/run_bench_regression.py) | 参考 Quick8 + 泛化域 Quick8 + 6 技能烟测 | ✓ |
| [`scripts/verify_skill_bench_gates.py`](../scripts/verify_skill_bench_gates.py) | 离线 CI 门禁（路由/harm） | — |
| [`scripts/run_dna_golden_ci.py`](../scripts/run_dna_golden_ci.py) | DNA 黄金集 13 项 | — |
| [`scripts/run_nightly_dna_bench.py`](../scripts/run_nightly_dna_bench.py) | nightly golden + gates + 可选 LLM | 可选 |
| [`scripts/run_quick8_ci.py`](../scripts/run_quick8_ci.py) | 参考技能 Quick8 CI | ✓ |

### 归档脚本（`scripts/archive/`）

研究/泛化实验用，功能仍有效：

| 脚本 | 说明 |
|------|------|
| `run_cold_start_generalize.py` | Path B 冷启动三泛化技能（`SKILLOS_FORCE_COLD_START=1`） |
| `bench_generalize_3skills.py` | 泛化 vs 参考 cohort + verdict |
| `run_ablation.py` | HERITAGE×pack 2×2 ablation |
| `repair_generalize_packs.py` | 清理跨域 quick8 / routing 词 |
| `run_local_agent_compare.py` | 单 preset Quick8 对比 |

## API

| 端点 | 说明 |
|------|------|
| `GET /api/bench/official/summary` | 参考 + **generalize_skills** dashboard |
| `GET /api/bench/official/regression/latest` | 含 **generalize_domain_quick8** |
| `POST /api/bench/official/regression/run` | 后台跑回归 |
| `POST /api/bench/official/skills/{name}/quick8` | 单技能 Quick8（`domain_only=true` 仅 pack 题） |

## 产物目录

`data/benchmarks/`：

| 前缀 | 含义 |
|------|------|
| `bench_regression_*` | 全量回归快照 |
| `generalize_bench_*` | 泛化对比 |
| `ablation_*` | Layer 1 2×2 ablation |
| `cold_start_*` | 冷启动轮次记录 |
| `skill_quick8_*` / `skill_domain_quick8_*` | 单技能 Quick8 |

`data/domain_packs/`：10 个领域 pack（HERITAGE + anchor + routing）

## 最新关键数字（2026-06-18）

| 指标 | 泛化 cohort | 参考 cohort |
|------|------------|------------|
| Median domain Quick8 Δ | **+45** | +117 |
| 烟测 | 100% | 100% |
| 判定 | `strong_generalization` | — |
| 回归 | **ALL PASS** | — |

Ablation 详见 [`paper/experiments/layer1_ablation_results.md`](paper/experiments/layer1_ablation_results.md)

## 认识论 Ablation（Layer 0，独立）

```bash
python -m skillos.benchmark_epistemic
```

报告：[`paper/experiments/epistemic_results.md`](paper/experiments/epistemic_results.md)
