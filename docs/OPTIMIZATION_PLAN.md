# SkillOS 后续优化计划

> 2026-06-25 · 基于 Claude Code 自动化配置后的项目扫描
> 当前版本：v0.3.4 · 120 个文件处于修改状态 · 无 git remote

---

## 一、基础设施（P0 — 阻塞发布）

### 1.1 配置 Git Remote
**现状**：无 `origin`，所有 `git push` 操作均失败。AI_DEV_LOG 中至少 4 条记录以「未修改/刻意不做：git push（无 remote）」结尾。

**动作**：
```bash
git remote add origin <repo-url>
git push -u origin main
git push origin v0.3.4
```

### 1.2 清理脏数据状态
**现状**：120 个文件处于 modified 状态，分为三类：

| 类别 | 数量 | 说明 |
|------|:----:|------|
| Lineage 运行时数据 | 34 | `skillos/knowledge/data/lineage/` — 已在 `.gitignore` |
| Skills 测试数据 | 11 | `skills/` 目录下测试/集成用 skill — 部分应为 gitignored |
| 系统状态文件 | 2 | `skill_state.json`、`skill_dna.json`、`skill_variants.json` |

**动作**：
1. 检查 `.gitignore` 是否遗漏了 `skillos/knowledge/data/lineage/` 和 `skillos/skills/knowledge/` 下的运行时 JSON
2. 对合法修改执行 `git add` + commit；对运行时数据恢复或 gitignore
3. 最终目标：`git status` 干净，可以 clean release

### 1.3 安装 Pre-commit Hooks
**现状**：`.pre-commit-config.yaml` 已配置（ruff + trailing-whitespace + check-yaml/json/toml），但 hooks 未安装到 `.git/hooks/`。

**动作**：
```bash
pre-commit install
pre-commit run --all-files  # 首次全量扫描
```

---

## 二、质量门禁（P1 — 回归修复）

### 2.1 Reference Quick8 回归修复
**现状**：v0.3.3 发版时 Reference Quick8 **3/3 FAIL**（Δ 低于门槛：+9.4 / -4.4 / +7.3 pp）。v0.3.4 尝试修复但尚未重新验证。

**动作**：
1. 运行 `python scripts/run_bench_regression.py`（需 `DEEPSEEK_API_KEY`）
2. 针对 FAIL 的三门禁逐个排查：domain pack 路由是否正确、reference 技能内容是否需要调优
3. 目标：Reference Quick8 全部 PASS

### 2.2 测试覆盖率整理
**现状**：605 个测试，98.3% pass → 约 10 个测试失败。已知 `test_feasibility_eval.py` 需 `--ignore`。

**动作**：
1. 跑 `pytest tests/ -v --tb=short` 收集当前失败清单
2. 对每个失败测试：修复或标记 skip + issue
3. 目标：99%+ pass rate

### 2.3 CI 本地可复现
**现状**：GitHub Actions 的 `ci.yml` 包含 lint → Phase A → 闭包验证 → 门禁 → 全量测试 → import 校验 六阶段管道。本地没有等价的一键脚本。

**动作**：创建 `scripts/ci_local.sh` 复现 CI 管道（除需要 `DEEPSEEK_API_KEY` 的 bench 阶段外）

---

## 三、Claude Code 自动化验证（P1）

### 3.1 Hook 生效验证
**现状**：`.claude/settings.json` 已配置 3 个 hooks，需验证实际触发。

**动作**：
1. 重启 Claude Code 会话，确认 hooks 被加载
2. 做一次试编辑（修改 .py 文件），验证 ruff auto-fix 自动执行
3. 尝试编辑 `.env`，验证被阻断
4. 结束会话，确认 AI_DEV_LOG 提醒弹出

### 3.2 Skill 和 Agent 实战测试
**动作**：
1. `/ai-dev-log` — 验证自动日志写入
2. 用 security-reviewer 审查 `skillos/api/` 和 `skillos/db.py`
3. 用 test-writer 为一个模块生成测试

---

## 四、架构与代码质量（P2）

### 4.1 清理硬编码和桩代码
**现状**：DESIGN.md 声称「0 桩代码」，但需定期审计。

**动作**：
1. `grep -r "TODO\|FIXME\|HACK\|stub\|mock" skillos/ --include="*.py"` 收集技术债
2. 逐条评估并清理

### 4.2 异常处理审计
**现状**：AGENTS.md §3 要求「禁止裸 `except: pass`」。ruff 未配置 `B904` 规则。

**动作**：
1. 临时启用 ruff `B904`、`E722` 做一次性全量扫描
2. 修复所有裸异常，至少加 `_log.warning` 或 `_log.debug`

### 4.3 Mypy 错误逐步归零
**现状**：`pyproject.toml` 中 mypy 禁用了 13 个错误码。共计 0 errors 是关闭检查的结果。

**动作**：每次开启 1-2 个禁用码，修复后提交，渐进式严格化。

### 4.4 废弃脚本归档
**现状**：`scripts/archive/` 已有归档目录，`scripts/` 下仍有大量一次性验证脚本（`verify_*.py`、`stress_test_*.py`）和输出文件（`*_output.txt`）。

**动作**：
1. 将 `verify_*_output.txt` 移入 `scripts/archive/` 或删除
2. 将 `user_sim_*.txt` 大文件（61KB）归档或删除

---

## 五、产品化路线图（P3 — 延续 IMPROVEMENT_PLAN）

IMPROVEMENT_PLAN.md 中 Phase 0–7 已全部交付（所有验收项已打勾）。以下为 Post-Phase-7 剩余开放项：

### 5.1 论文完善
- [ ] `paper.tex` Layer 1 ablation 小节
- [ ] 费曼+类比对 bench Δ 的实证对比

### 5.2 冷启动迭代
- [ ] 6 个 Sprint 10 domain pack 跑 cold_start 迭代优化 heritage_body

### 5.3 测试修复
- [ ] `tests/test_feasibility_eval.py` 修复或在 CI 中 `--ignore`

### 5.4 下一步方向（来自 IMPROVEMENT_PLAN 末尾）
> 「以 bench 回归与产品化为主」

建议：不新增 Phase，聚焦已有系统稳定性 + 论文 + CI 自动化。

---

## 优先级汇总

| 优先级 | 分类 | 条目 | 估时 |
|:------:|------|------|:----:|
| 🔴 P0 | 基础设施 | 配置 Git Remote | 5 min |
| 🔴 P0 | 基础设施 | 清理 120 个脏文件 | 30 min |
| 🔴 P0 | 基础设施 | 安装 Pre-commit Hooks | 5 min |
| 🟡 P1 | 质量门禁 | Reference Quick8 回归修复 | 1-2 h |
| 🟡 P1 | 质量门禁 | 测试失败修复，目标 99%+ | 1-2 h |
| 🟡 P1 | 质量门禁 | 创建 `ci_local.sh` | 15 min |
| 🟡 P1 | 自动化 | Hook/Skill/Agent 实战验证 | 30 min |
| 🟢 P2 | 代码质量 | 异常处理审计 | 1 h |
| 🟢 P2 | 代码质量 | Mypy 渐进严格化 | 持续 |
| 🟢 P2 | 代码质量 | 废弃脚本归档 | 15 min |
| 🔵 P3 | 产品化 | 论文 + 冷启动 + 测试修复 | 持续 |

---

## 执行建议

1. **先收尾再前进**：P0 三项一天内完成，让仓库进入可发布状态
2. **每完成一项 → AI_DEV_LOG 追加记录**（Claude Code 已有 Stop hook 提醒）
3. **P1 回归修复需要 DEEPSEEK_API_KEY**，无 key 时先做本地可做的部分（ci_local.sh、测试修复）
4. **P2/P3 作为背景任务**，在正常开发中渐进完成
