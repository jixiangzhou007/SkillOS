# Official SkillsBench CI

SkillOS 通过 [`.github/workflows/official-skillsbench.yml`](../.github/workflows/official-skillsbench.yml) 在 **Linux + Docker** 上跑官方 BenchFlow 评测。

## 前置条件

| 项 | 说明 |
|----|------|
| 运行环境 | GitHub Actions `ubuntu-latest`（native Windows 不支持 oracle/agent eval） |
| Secret | `DEEPSEEK_API_KEY` — agent compare 必需 |
| 可选 env | `GITHUB_TOKEN` + `GITHUB_REPOSITORY` — 从 SkillOS API/脚本触发 `repository_dispatch` |

## 预设对照

| preset | 官方 task | SkillOS 技能 |
|--------|-----------|--------------|
| `citation-curated` | citation-check | （bundled） |
| `csv-sales-pivot` | sales-pivot-analysis | CSV数据清洗助手 |
| `pr-dependency-audit` | software-dependency-audit | GitHub Pull |
| `refund-invoice-fraud` | invoice-fraud-detection | 电商客服退款处理 |

## 触发方式

### 1. GitHub CLI（推荐）

```bash
# Oracle smoke（无需 LLM key）
gh workflow run official-skillsbench.yml

# 退款技能 agent compare
gh workflow run official-skillsbench.yml \
  -f run_agent_compare=true \
  -f compare_preset=refund-invoice-fraud
```

### 2. SkillOS 脚本

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=owner/SkillOS
python scripts/trigger_official_bench_ci.py --skill 电商客服退款处理
```

### 3. 前端 / API

`POST /api/bench/official/skills/{name}/trigger-ci` — 同上，需配置 `GITHUB_TOKEN` 与 `GITHUB_REPOSITORY`。

## 产物

- `data/benchmarks/official_eval_*.json`
- `data/benchmarks/official_compare_*.json`
- Actions artifact: `official-skillsbench-smoke` / `official-skillsbench-compare`

## 本地 Quick8 vs 官方

| 轨道 | 用途 | 文档 |
|------|------|------|
| 自建 Quick8 | 日常快检、域内 Δ、CI 门禁、ablation | [`BENCHMARK_LOCAL.md`](BENCHMARK_LOCAL.md) |
| 官方 BenchFlow | 权威 pass rate，需 Linux CI | 本文 |

## 本地回归 / 泛化 / Ablation（2026-06-18 起）

| 脚本 | 用途 | 需 `DEEPSEEK_API_KEY` |
|------|------|:---------------------:|
| `python scripts/run_bench_regression.py` | 参考 Quick8 + 泛化域 Quick8 + 6 技能烟测 | ✓ |
| `python scripts/archive/bench_generalize_3skills.py` | 泛化 vs 参考 cohort 对比 + verdict | ✓ |
| `python scripts/archive/run_cold_start_generalize.py` | Path B 冷启动三技能（`SKILLOS_FORCE_COLD_START=1` 强制重跑） | ✓ |
| `python scripts/archive/run_ablation.py` | HERITAGE×pack 2×2 ablation | ✓ |
| `python scripts/archive/repair_generalize_packs.py` | 清理跨域 quick8 / routing 词 | — |

产物目录：`data/benchmarks/`（`bench_regression_*`、`generalize_bench_*`、`ablation_*`、`cold_start_*`）。

API：`GET /api/bench/official/summary` 含 `generalize_skills`；`GET /api/bench/official/regression/latest` 含 `generalize_domain_quick8`。
