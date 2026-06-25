# SkillOS 改进计划

> **版本**：v1.1 · 2026-06-18（Post-Phase-7 增补）
> **定位**：技能 IDE — 在飞书 / 微信 / Cursor 里对话，沉淀可验证的 Agent Skills
> **原则**：先证明「可信」，再扩「通道」；先学术可证，再产品规模化
> **执行协议**：每阶段遵守 [`AGENTS.md`](../AGENTS.md)，变更写入 [`AI_DEV_LOG.md`](AI_DEV_LOG.md)

---

## 总览

```
Phase 0  基线冻结 ──→ Phase 1  认识论主链路 ──→ Phase 2  Epistemic Benchmark
                              │                           │
                              └───────────┬───────────────┘
                                          ▼
Phase 3  沉淀协议 ──→ Phase 4  通道产品化 ──→ Phase 5  团队上下文
                                          │
                                          ▼
                              Phase 6  论文 + 对外叙事
                                          │
                                          ▼
                              Phase 7  进化深化（可选，与 SkillOpt 互补）
```

| 阶段 | 周期（估） | 产品产出 | 学术产出 |
|:----:|:--------:|----------|----------|
| 0 | 2–3 天 | 可复现基线 | 现状数据快照 |
| 1 | 1–2 周 | **Verified Skill** 运行时闭环 | 系统可描述、可 ablation |
| 2 | 1–2 周 | 质量数字可对外讲 | 论文 1 核心实验 |
| 3 | 3–5 天 | 「沉淀」统一体验 | — |
| 4 | 1–2 周 | 飞书/Cursor 主路径可用 | Demo 视频 / case study |
| 5 | 1 周 | 团队 Playbook + 变体 | — |
| 6 | 1–2 周 | 一句话 PMF + landing | arXiv 论文 1 |
| 7 | 2+ 周 | 越用越好（有证据） | 论文 3 或 SkillOpt 对接 |

---

## Phase 0：基线冻结与差距清单

**目标**：任何改进都有「改前数字」，避免自说自话。

### 任务

1. **跑通全量测试并记录**
   ```bash
   python -m pytest tests/ -v --tb=no 2>&1 | tee docs/baseline/pytest_20260614.txt
   python -m skillos.benchmark --full 2>&1 | tee docs/baseline/benchmark_20260614.txt
   ```

2. **确认认识论层接入缺口**（已知）
   - `record_claim()` 仅在 `knowledge/epistemology.py` 定义
   - `skills/agent.py`、`learn_from_url`、苏格拉底 `GENERATING` 阶段均未调用
   - `knowledge/extractor.py` 有平行验证逻辑，需规划合并或桥接

3. **写一页差距表** → `docs/baseline/GAP_ANALYSIS.md`
   | 设计书声称 | 运行时现状 | 优先级 |
   |-----------|-----------|:------:|

4. **冻结范围**：Phase 1–4 内 **不新增** marketplace 支付、不扩模块数。

### 验收

- [x] pytest 全绿或有 documented failures → **118 pass / 3 fail / 2 skip**，见 [`baseline/BASELINE_SUMMARY.md`](baseline/BASELINE_SUMMARY.md)
- [x] benchmark 结果存档 → [`baseline/benchmark_20260614.txt`](baseline/benchmark_20260614.txt)
- [x] GAP_ANALYSIS 完成 → [`baseline/GAP_ANALYSIS.md`](baseline/GAP_ANALYSIS.md)
- [x] 范围冻结 → [`baseline/SCOPE_FREEZE.md`](baseline/SCOPE_FREEZE.md)

**Phase 0 完成日期**：2026-06-14 · **Phase 0.5–7 完成日期**：2026-06-14 · **Post-Phase-7（2026-06-18）**：Path B 冷启动 + 10 domain pack + 本地 bench 回归/ablation 闭环

---

## Post-Phase-7：DNA Bench 与泛化验证（2026-06-18）

**目标**：证明 Layer 1 领域 DNA（HERITAGE + pack 路由）可量化提分，且对未见技能可冷启动泛化。

### 已交付

| 项 | 产物 |
|----|------|
| Path B 冷启动 | `skillos/skills/cold_start.py` + `data/domain_packs/*.json` |
| 回归 cohort | `scripts/run_bench_regression.py` — 参考 + 泛化 Quick8 + 烟测 |
| Layer 1 ablation | `evaluation/ablation.py` — HERITAGE×pack 2×2 |
| 文档 | [`BENCHMARK_LOCAL.md`](BENCHMARK_LOCAL.md) · [`layer1_ablation_results.md`](paper/experiments/layer1_ablation_results.md) |

### 关键数字

| 指标 | 泛化 cohort |
|------|------------|
| Median domain Quick8 Δ | **+45** |
| Ablation full vs baseline | +45 vs 0 |
| 回归 | ALL PASS |

### 开放项（非阻塞）

- [ ] `tests/test_feasibility_eval.py` 修复或 CI `--ignore`
- [ ] 论文 `paper.tex` Layer 1 ablation 节
- [ ] 6 个 Sprint 10 pack 跑 cold_start 迭代优化 heritage_body
- [ ] 费曼+类比对 bench Δ 的实证对比

---

## Phase 1：认识论主链路（最高优先级）

**目标**：创建技能时，每条「硬规则」声明走认识论管道；用户可见验证状态。

**学术**：Experience → Knowledge 从概念变为 **可执行数据流**。
**产品**：IM 沉淀技能时有 **「已验证 / 待审 / 经验性」** 反馈。

### 1.1 设计：声明提取与分区

在最终 SKILL.md 中区分：

| 区块 | 内容 | 认识论要求 |
|------|------|-----------|
| `S_body` 硬规则 | if-then、必须步骤 | 仅 **Knowledge** 或用户确认后的 Experience |
| `S_appendix` / 注释 | 参考、推测 | Experience，标注 `[待验证]` |
| YAML `epistemic` | 元数据 | `{verified: N, pending: M, source: url\|dialogue}` |

### 1.2 代码改动（按顺序）

| # | 文件 | 改动 |
|---|------|------|
| 1 | `skillos/knowledge/epistemic_bridge.py` | **新增**：从 LLM 输出提取 bullet/规则 → 批量 `record_claim()`；统一 falsify 调用 |
| 2 | `skillos/skills/agent.py` | `learn_from_url` 步骤 5「验证」、步骤 7「沉淀」后调用 bridge |
| 3 | `skillos/skills/agent.py` | 苏格拉底 `GENERATING` / `save` 前调用 bridge |
| 4 | `skillos/skills/skill_store.py` | `save_skill()` 写入 YAML `epistemic` 字段；拒绝（或 warn）全 Experience 硬规则 |
| 5 | `skillos/knowledge/extractor.py` | 提取结果改走 `record_claim()`， deprecate 重复逻辑（或 thin wrapper） |
| 6 | `skillos/api/skills.py` | 创建/导出 API 返回 `epistemic_summary` |
| 7 | `skillos/mcp_server.py` | `extract_skill` / `get_skill` 返回 epistemic 摘要 |

### 1.3 用户可见输出（产品）

沉淀完成后回复模板：

```
✅ 技能「XXX」已保存
· 已验证规则：3 条
· 待你确认：2 条（回复「确认 1,2」或继续对话修正）
· 来源：飞书对话 / URL / 文件
```

### 1.4 测试

| 测试 | 文件 |
|------|------|
| bridge 单元测试 | `tests/test_epistemic_bridge.py` |
| URL 管线集成 | `tests/test_integration.py` 扩展 |
| save_skill epistemic meta | `tests/test_skill_store.py` |

### 验收

- [x] `grep record_claim skillos/` 除 epistemology 外 ≥3 处调用（bridge + extractor）
- [x] 新建技能 YAML 含 `epistemic`
- [x] 集成测试：pipeline 不 crash（128 passed）
- [x] `AI_DEV_LOG.md` 记录本阶段

**实现说明**：认识论处理集中在 `save_skill()`（非 draft），而非重复嵌入 `agent.py` 各步骤——所有 API/MCP 保存路径自动覆盖。

### 反模式（禁止）

- 绕过认识论直接写 Knowledge 级别内容
- 认识论仅 API 暴露、主链路仍跳过

---

## Phase 2：Epistemic Benchmark + Ablation

**目标**：用数字证明认识论层有效 — 论文 1 与产品 trust 的共同地基。

### 2.1 数据集

路径：`data/benchmarks/epistemic/`

```
claims.jsonl          # 100 条：content, label(true|false|opinion), source_type, domain
sources/              # 对应网页/对话片段
README.md             # 标注规范、inter-rater 说明（可先单人标注 v0）
```

**构成建议**：
- 30 条：正确方法论事实（代码审查、事故响应等，复用现有 3 case 扩展）
- 30 条： plausible 但错误（常见 blog 误导）
- 20 条：主观偏好（不应进 Knowledge）
- 20 条：需多源交叉才成立的声明

### 2.2 实验矩阵

| 配置 | 说明 |
|------|------|
| **A** Baseline | 无认识论，单次 LLM 生成 skill |
| **B** Classify-only | 分级但不 falsify |
| **C** Full | 交叉验证 + falsify + 晋升 |

**指标**：
- Claim-level：precision / recall / F1（相对 label）
- Skill-level：结构完整性（现有 benchmark）、人工 1–5 可执行性（≥10 skills 抽样）
- 下游：选 3 skills 跑 `run` + trace 分数（若有）

### 2.3 代码

| 文件 | 说明 |
|------|------|
| `skillos/benchmark_epistemic.py` | 跑 ablation，输出 JSON + Markdown 报告 |
| `docs/paper/experiments/epistemic_results.md` | 论文图表素材 |

### 验收

- [x] 三套配置均可一键复现
- [x] Full vs Baseline：false claim 过滤率有可报告差异（C 100% vs A 0%，Δ +1.000）
- [x] 结果写入 `data/benchmarks/epistemic/results/`

---

## Phase 3：统一「沉淀」对话协议

**目标**：飞书 / Cursor / dispatch 同一套意图 — 降低误触发、提高可教性。

### 3.1 意图表

| 用户说法（示例） | 路由 | 行为 |
|------------------|------|------|
| 沉淀 / 做成 skill / 整理成标准 | `extract` | 苏格拉底或续接当前 session |
| 贴 URL | `learn_url` | 7 步管线 |
| 上传文件 | `ingest` | file_ingest → actionable/conceptual |
| 确认 1,2 / 采纳待审 | `confirm_claims` | 晋升 Experience → Knowledge |
| 其他 | `chat` | 普通对话 |

### 3.2 改动

| 文件 | 改动 |
|------|------|
| `skillos/api/skills.py` | `dispatch` 增加 `confirm_claims` 分支 |
| `skillos/skills/dispatcher.py` | 触发词表 + 保守路由文档化 |
| `skillos/mcp_server.py` | 新增或扩展 tool：`confirm_pending_claims` |
| `docs/USER_GUIDE.md` | **新增**：用户可见话术表（中/英） |

### 验收

- [x] E2E：dispatch「帮我沉淀退款流程」进入萃取
- [x] E2E：「确认待审」可晋升 claim
- [x] MCP 文档与 USER_GUIDE 一致

---

## Phase 4：通道产品化（对话入口）

**目标**：用户在 **已用的工具** 里完成「对话 → Verified Skill」，无需打开 SkillOS 桌面。

### 4.1 Cursor / Claude Code（P0）

| 任务 | 说明 |
|------|------|
| MCP `extract_skill` 抛错与进度 | 流式或分步返回 pipeline_log |
| 工作区 skill 写入 | 默认 `./skills/` 或可配置 |
| Cursor Rule 片段 | 可选：`.cursor/rules/skillos-precipitate.mdc` 教用户话术 |

### 4.2 飞书（P0）

**路径 A（快）**：Hermes Gateway → MCP（已有 `deployment.md`）
**路径 B（控）**：SkillOS 原生 Lark Bot（`skillos/channels/feishu.py`）

| 里程碑 | 内容 |
|--------|------|
| M1 | Hermes 路径文档 + 端到端 checklist 实测 |
| M2 | session_id = `feishu:{chat_id}:{user_id}` 映射 |
| M3（可选） | 原生 Bot：事件订阅、卡片回复 epistemic 摘要 |

### 4.3 微信（P1）

- **聊天沉淀**：同 Hermes，文档化即可
- **公众号摄入**：保持现有 `wechat_fetch` / `account_watcher`，与聊天叙事分离

### 验收

- [x] Cursor：一条 MCP 调用得到 SKILL.md + epistemic 摘要（`extract_skill` + pipeline_log + 单元测试）
- [x] 飞书：Hermes 路径 checklist + session 映射（`docs/channels/FEISHU_HERMES_CHECKLIST.md`；真实群实测待运维）
- [x] 录屏 3 分钟 demo 存档 `docs/demo/`（脚本 `PHASE4_DEMO_SCRIPT.md`）

---

## Phase 5：团队上下文

**目标**：「大家都」— 群/部门有共享 Playbook，同人不同角色有变体。

| 任务 | 文件 |
|------|------|
| chat_id → Playbook 绑定 | `knowledge/playbook.py` + 配置 JSON |
| 沉淀时注入 Playbook | `agent.py`（已有 hook，补绑定逻辑） |
| 变体自动建议 | `skills/variants.py` + dispatch |
| 贡献者 lineage | `knowledge/lineage.py` 记录 feishu_user / session |

### 验收

- [x] 两个不同 chat_id 沉淀同名流程，输出风格符合各自 Playbook（`get_playbook_context(chat_id=…)` 单元测试 + 示例 playbook）
- [x] lineage 可查到「谁、哪个群、哪次对话」（`skill_precipitations.jsonl` + `/api/knowledge/skill-lineage`）

---

## Phase 6：论文与对外叙事

**目标**：学术 credibility + 产品一句话。

### 6.1 论文 1（认识论）

- 更新 `docs/paper/paper.tex`：实验节接 Phase 2 数字
- arXiv 投稿 checklist：`docs/paper/SUBMIT.md`
- 标题建议：*Experience ≠ Knowledge: An Epistemology Engine for Agent Skill Quality*

### 6.2 产品叙事

**一句话**：
> SkillOS：在飞书、Cursor 里对话，沉淀**可验证**的 Agent Skills — 不是又一份 AI 生成的 markdown。

**证据链**：Phase 2 ablation 数字 + Phase 4 demo。

### 验收

- [x] PDF 可编译（`docs/paper/Makefile` + `tests/test_paper.py` 在有 pdflatex 时验证；无 TeX 时 tex 内容验收通过）
- [x] README 首段与叙事一致
- [x] `CHANGELOG.md` 发 v0.2.0（认识论主链路 + benchmark）

---

## Phase 7：进化深化（可选，Phase 1–2 之后）

**不与 Microsoft SkillOpt 正面竞争**，做互补：

| 方向 | 说明 |
|------|------|
| 导出 → SkillOpt | `export_for_skillopt()` 生成 `best_skill.md` 训练入口 |
| 知识扩散 + 验证 | 扩散前 epistemic gate，避免错误跨技能污染 |
| 论文 3 | MoE + 扩散 + 有 held-out 的多技能数据集 |

### 验收

- [x] `export_for_skillopt()` 生成 best_skill.md + manifest（API/MCP/Python）
- [x] 扩散前 epistemic gate：ERROR 阻断；全 pending 仅建议不自动改写
- [x] 文档 [`docs/evolution/SKILLOPT_EXPORT.md`](evolution/SKILLOPT_EXPORT.md)

## 风险与依赖

| 风险 | 缓解 |
|------|------|
| LLM 证伪 LLM（同模型自洽） | Benchmark 含人工 label；Phase 2 报告 limitatio |
| 认识论过严导致 skill 太空 | 硬规则 / 附录分区；用户可「确认」晋升 |
| Hermes 版本漂移 | 已有 `hermes_bridge.check_compatibility` |
| 范围蔓延 | Phase 4 前冻结 marketplace 功能 |

---

## 执行顺序（给下一个 AI 会话）

```
1. 读 AGENTS.md + AI_DEV_LOG 最新条
2. 执行 Phase 0（若无 baseline 目录）
3. Phase 1.2 从 epistemic_bridge.py 开始
4. 每完成一个 Phase → AI_DEV_LOG + 本文件对应验收打勾
```

---

## 相关文档

| 文档 | 用途 |
|------|------|
| [`DESIGN.md`](../DESIGN.md) | 架构与 AI 约束 §6 |
| [`docs/PAPERS.md`](PAPERS.md) | 三篇论文规划 |
| [`deployment.md`](../deployment.md) | Hermes / 飞书 / 微信 |
| [`AGENTS.md`](../AGENTS.md) | 跨工具协作协议 |
| [`AI_DEV_LOG.md`](AI_DEV_LOG.md) | 增量变更记录 |

---

*本计划由产品化 + 学术顶端视角制定；Phase 1–2 为不可跳过核心。*
