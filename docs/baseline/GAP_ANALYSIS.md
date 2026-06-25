# SkillOS 差距分析（设计声称 vs 运行时现状）

> **基线日期**：2026-06-14 · **更新**：2026-06-18（Layer 1 bench 闭合）
> **依据**：`DESIGN.md`、`docs/PAPERS.md`、pytest、benchmark、源码 grep
> **优先级**：P0 阻塞产品/API · P1 Phase 1–2 核心 · P2 Phase 3+ · P3 延后

---

## 2026-06-18 更新摘要

| 类别 | 原差距 | 现状 |
|------|--------|------|
| Layer 1 领域 DNA bench | 无 held-out / 无 ablation | **已闭合** — median 泛化 Δ +45；HERITAGE×pack 2×2 见 [`layer1_ablation_results.md`](../paper/experiments/layer1_ablation_results.md) |
| Path B 冷启动 | Playbook 绑定未产品化 | **部分闭合** — `cold_start.py` + 10 pack；泛化三技能可自动 HERITAGE |
| 本地 bench 回归 | 仅 3 用例结构 benchmark | **已扩展** — `run_bench_regression.py` + Quick8 cohort |
| pytest 规模 | 123 collected | **501 collected**（`test_feasibility_eval.py` 仍收集失败，需 ignore） |
| 认识论主链路 | 曾零调用 | Phase 1 已接入（见 §1 表） |

---

## 总览

| 类别 | 设计/论文声称 | 运行时现状 | 差距等级 |
|------|--------------|-----------|:--------:|
| 认识论主链路 | 创建技能必经 epistemology | `record_claim` 零调用 | **P1** |
| API 稳定性 | 30+ 端点可用 | `GET /api/skills/` 500 | **P0** |
| 质量评测 | 10 维 Auditor + benchmark | 审计解析失败，score 恒 60 | **P1** |
| 沉淀协议 | 飞书/IM 对话沉淀 | 有关键词，无 `confirm_claims` | **P2** |
| 通道集成 | 微信/飞书 gateway | 文档级（Hermes），未 E2E 验证 | **P2** |
| 进化证据 | MoE + SkillOpt 级优化 | 有实现，无 held-out 数字 | **P3** |
| Marketplace | 发布/支付/评分 | 有模块，Phase 1–4 冻结扩展 | **—** |

---

## 详细差距表

### 1. 认识论引擎（论文 1 核心）

| 设计书声称 | 运行时现状 | 优先级 | Phase 1 动作 |
|-----------|-----------|:------:|--------------|
| Experience→Knowledge 四条件晋升 | `EpistemicStore` + 单测完整 | — | 保留 |
| 创建技能时 `record_claim()` | **已接入** — `epistemic_bridge` + `save_skill` + `extractor` | — | 完成 |
| URL 7 步「验证」步接证伪 | 保存时统一 falsify（有 API key 时） | P1 | Phase 1 ✓ |
| 苏格拉底 GENERATING 接认识论 | 经 `_persist_created_skill` → `save_skill` | — | 完成 |
| `extractor.py` 与 epistemology 统一 | `save_knowledge` → `record_claim()` | — | 完成 |
| SKILL.md 含 epistemic 元数据 | `save_skill` 写入 YAML `epistemic` + body 章节 | — | 完成 |
| 用户可见「已验证/待审」 | API/MCP 返回 `epistemic_summary` + 回复后缀 | — | 完成 |

### 2. 技能创建管线

| 设计书声称 | 运行时现状 | 优先级 |
|-----------|-----------|:------:|
| 7 步认知管线 | 已实现，`learn_from_url` 完整 | — |
| S_route 决策表 | benchmark：Pipeline 100% vs Baseline 0% | — |
| 双输出苏格拉底 | 已实现，有 integration 测试 | — |
| 知识扩散（第 8 步） | agent.py 有扩散逻辑 | P2 需 epistemic gate |
| Playbook 冷启动 | `playbook.py` 存在，绑定未产品化 | P2 |

### 3. API / 集成

| 设计书声称 | 运行时现状 | 优先级 | 动作 |
|-----------|-----------|:------:|------|
| `GET /api/skills/` 列出技能 | ~~`_list_skills_impl()` 未定义~~ → Phase 0.5 已修复 | — | 改为 `skill_store.list_skills` 或补 impl |
| `POST /api/evolution/consolidate` | 功能存在，测试 10s timeout | P1 | 测试提 timeout 或 mock LLM |
| MCP 10 工具 | 118 相关测试通过 | — | — |
| 飞书/微信对话沉淀 | README/deployment 指向 Hermes | P2 | Phase 4 E2E |
| `except: pass` 禁止（DESIGN §6） | `api/server.py` 等 4+ 处仍存在 | P2 | 渐进清理 |

### 4. 评测与学术

| 论文/设计声称 | 运行时现状 | 优先级 |
|--------------|-----------|:------:|
| Pipeline vs Baseline 实验 | 3 用例，结构指标 only | P1 |
| false claim 过滤率 | **100 条标注集 + ablation 指标**（C_full false_filter=1.0） | — | 完成 |
| Ablation A/B/C | `benchmark_epistemic.py` 离线/LLM 可复现 | — | 完成 |
| **Layer 1 HERITAGE×pack ablation** | **2×2 factorial，泛化 median Δ +45** | — | **2026-06-18 完成** |
| **本地 Quick8 回归** | `run_bench_regression.py` + 参考/泛化 cohort | — | **2026-06-18 完成** |
| 52 格级进化 benchmark | 无 | P3 Phase 7 |

### 5. 产品叙事（用户确认方向）

| 目标 | 现状 | 优先级 |
|------|------|:------:|
| Skill IDE — 对话即沉淀 | 桌面/MCP/dispatch 有，IM 未通 | P2 |
| 飞书群沉淀技能 | 架构设计有，无实测 checklist | P2 |
| Verified Skill 信任标 | 未实现 | P1 |

---

## 测试覆盖缺口

| 区域 | 有测试 | 缺测试 |
|------|:------:|--------|
| epistemology 单元 | ✓ | 主链路集成 |
| agent URL 管线 | ✓（mock/短内容） | epistemic 断言 |
| API list_skills | ✗（因 bug 失败） | — |
| benchmark epistemic | ✓ | — |
| 飞书/Hermes E2E | ✗ | Phase 4 |

---

## Phase 0 发现的可立即修复项

1. ~~**P0** `_list_skills_impl`~~ → **Phase 0.5 已完成**（2026-06-14）
2. ~~**P1** `test_consolidate` timeout~~ → **Phase 0.5 已完成**（120s）

---

## 与改进计划映射

```
P0 API bug          → Phase 0.5 或 Phase 1 第一天
P1 认识论 + 评测    → Phase 1 + Phase 2
P2 沉淀协议 + 通道  → Phase 3 + Phase 4
P3 进化证据         → Phase 7
```

完整路线图：[`../IMPROVEMENT_PLAN.md`](../IMPROVEMENT_PLAN.md)
