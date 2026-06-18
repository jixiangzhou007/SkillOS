# SkillOS 基线快照

> **冻结日期**：2026-06-14  
> **环境**：Windows · Python 3.14 · `D:\SkillOS`  
> **用途**：Phase 1+ 改进的「改前数字」；复现命令见下文。

---

## 代码规模

| 指标 | 数值 | 备注 |
|------|------|------|
| `skillos/` Python 模块 | 58 | `*.py` 文件数 |
| `skillos/` 代码行数 | 17,592 | 含空行与注释 |
| pytest 用例 | 123 collected | 2026-06-14 统计 |
| DESIGN.md 声称 | 17,465 行 / 111 测试 | 略有漂移，以本表为准 |

---

## pytest 结果（2026-06-14）

**命令**：
```bash
python -m pytest tests/ -v --tb=short
```

**结果**：`118 passed · 3 failed · 2 skipped · 103.38s`  
**Phase 0.5 后**：`122 passed · 0 failed · 2 skipped · 124 collected · ~119s`（见 [`pytest_20260614_phase05.txt`](pytest_20260614_phase05.txt)）

**完整日志**：[`pytest_20260614.txt`](pytest_20260614.txt)

### 失败用例（Phase 0 记录 · Phase 0.5 已修复）

| 测试 | 根因 | 状态 |
|------|------|:----:|
| `test_list_skills` / `test_02_list_skills` | `_list_skills_impl` 误并入 `detect_variants` 死代码 | ✅ 0.5 已修 |
| `test_consolidate` | LLM 整合 >10s timeout | ✅ 0.5 测试 timeout→120s |

### 跳过

| 测试 | 原因 |
|------|------|
| `test_create_run_delete_skill` | 需 LLM，CI 跳过 |
| （另 1 个 skip） | 见 pytest 日志 |

### 警告

- `websockets.legacy` / `uvicorn` DeprecationWarning  
- `speech_recognition` / `aifc` Python 3.13+ 兼容警告  

---

## Benchmark 结果（2026-06-14）

**命令**：
```bash
python -m skillos.benchmark --full
```

**模型**：`deepseek-v4-flash`  
**完整输出**：[`benchmark_20260614.txt`](benchmark_20260614.txt)  
**JSON**：[`../../data/benchmarks/benchmark_20260614_105554.json`](../../data/benchmarks/benchmark_20260614_105554.json)

### 对比摘要（3 用例）

| 指标 | Pipeline (7-step) | Baseline (bare LLM) |
|------|:-----------------:|:-------------------:|
| 平均 audit score | 60.0 | 60.0 |
| S_route 覆盖率 | **100%** (3/3) | **0%** (0/3) |
| 平均耗时 | 108.4s | 8.8s |
| 相对速度 | 12.3× 慢 | 1× |

### 已知 benchmark 局限

1. **审计解析失败**：3/3 用例 `audit.summary = "审计解析失败，降级放行"`，score 均为 60，**无法区分质量差异**。  
2. **仅结构指标**：无 claim-level 真/假标注，无人工可执行性评分。  
3. **样本量**：N=3，不足以支撑论文或对外 PR。  

---

## 认识论层接入（grep 验证）

```bash
# record_claim 定义与调用
grep -r "record_claim" skillos/  → 仅 epistemology.py:409（定义）
# agent.py 主链路
grep -i epistemic skillos/skills/agent.py  → 无匹配
```

**结论**：认识论引擎**已实现、有单测**，**未接入** URL 管线与苏格拉底保存路径。

---

## Phase 0 验收状态

- [x] pytest 运行并存档  
- [x] benchmark `--full` 运行并存档  
- [x] GAP_ANALYSIS 完成 → [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md)  
- [x] 范围冻结 → [`SCOPE_FREEZE.md`](SCOPE_FREEZE.md)  

**Phase 0 出口条件**：进入 Phase 1 前，建议先修 P0 `_list_skills_impl`（1 行级修复，非 Phase 1 范围）。

---

## 复现清单

```bash
cd D:\SkillOS
python -m pytest tests/ -v --tb=short
python -m skillos.benchmark --full
python -m pytest tests/ --collect-only -q
```

需配置 `.env` 中 `DEEPSEEK_API_KEY`（benchmark 与部分 integration 依赖 LLM）。

---

## 2026-06-18 增补（Post-Phase-7 · 不改写 Phase 0 冻结数字）

> Phase 0 基线仍有效作为「改前数字」；本节记录 Path B / DNA bench 交付后的规模与评测。

### 代码规模（2026-06-18）

| 指标 | 数值 | 备注 |
|------|------|------|
| `skillos/` Python 模块 | **159** | 较 Phase 0 的 58 显著增长 |
| pytest collected | **501** | `--ignore=tests/test_feasibility_eval.py` |
| pytest 结果 | **478 pass / 21 fail / 2 skip** | 2026-06-18 全量跑；失败多为 sprint/结构单测漂移 |
| domain pack | **10** | `data/domain_packs/*.json` |

### 本地 SkillsBench（2026-06-18）

**命令**：
```bash
python scripts/run_bench_regression.py
python scripts/archive/run_ablation.py
```

**产物**：`data/benchmarks/generalize_bench_1781757925.json`、`bench_regression_1781758148.json`、`ablation_1781759573.json`

| 指标 | 泛化 cohort | 参考 cohort |
|------|------------|------------|
| Median domain Quick8 Δ | **+45** | +117 |
| 烟测 | 100% | 100% |
| 回归 | **ALL PASS** | — |

Ablation：full +45 vs baseline 0 — heritage 边际 +23.3，pack 边际 +24.7。详见 [`../paper/experiments/layer1_ablation_results.md`](../paper/experiments/layer1_ablation_results.md)

### 认识论层（2026-06-18 注）

Phase 1 已接入 `epistemic_bridge` + `save_skill`；上文 Phase 0 grep 结论**已过时**，以 [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md) §1 为准。

### 复现（2026-06-18）

```bash
cd D:\SkillOS
python -m pytest tests/ --ignore=tests/test_feasibility_eval.py -q
python scripts/run_bench_regression.py
python scripts/run_dna_golden_ci.py
```
