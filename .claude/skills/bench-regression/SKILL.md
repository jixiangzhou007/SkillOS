---
name: bench-regression
description: 运行完整的本地 SkillsBench 回归套件（Reference Quick8 + Generalize Quick8 + Smoke），需要 DEEPSEEK_API_KEY 环境变量
disable-model-invocation: true
user-invocable: true
---

# SkillsBench 回归测试

运行 SkillOS 本地 bench 回归套件，验证技能质量门禁是否通过。

## 前置条件

- `DEEPSEEK_API_KEY` 已在 `.env` 或环境变量中设置
- 项目已通过 `pip install -e ".[all]"` 安装
- 终端位于项目根目录

## 执行步骤

### 1. 同步 Reference Domain Packs

```bash
python scripts/repair_reference_packs.py
```

确保三门禁 reference pack 快照已同步到 `data/domain_packs/`。

### 2. 运行完整回归

```bash
python scripts/run_bench_regression.py
```

该脚本会自动执行：
- **修复 reference packs**（sync 到 data/domain_packs/）
- **Reference Quick8**：三门禁回归（基础技能集质量基线）
- **Generalize domain Quick8**：泛化域技能回归
- **Smoke**：烟测（含 GitHub Pull 等）

### 3. 检查门禁结果

```bash
python scripts/verify_quick8_gates.py
```

输出各门禁的通过/失败状态及 Δ pp 值。

## 注意事项

- 此操作会消耗 DeepSeek API 配额（约 20-30 次 LLM 调用）
- 运行时间约 3-8 分钟，取决于 API 响应速度
- 若 API Key 未设置，脚本会报错退出
- bench 结果保存在 `data/benchmarks/` 目录下，文件名为 `bench_regression_*.json`

## CI 中的等效命令

在 GitHub Actions 中，此回归由 `.github/workflows/ci.yml` 的 `benchmark` job 执行（仅在 `test` job 通过后触发）。
