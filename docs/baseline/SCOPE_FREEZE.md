# Phase 1–4 范围冻结

> **生效**：2026-06-14（Phase 0 完成起）  
> **解冻**：Phase 4 验收后由用户决定是否扩展  
> **目的**：防止「广而不深」— 先证明 Verified Skill，再扩商业与通道。

---

## 本阶段必须做（In Scope）

| ID | 内容 | 对应 Phase |
|----|------|:----------:|
| S1 | 认识论接入主创建链路 | 1 |
| S2 | Epistemic benchmark + ablation | 2 |
| S3 | 「沉淀 / 确认待审」统一协议 | 3 |
| S4 | Cursor MCP 体验 + 飞书 Hermes E2E | 4 |
| S5 | chat → Playbook 绑定（最小） | 5 |
| S6 | 论文 1 实验节 + 对外叙事 | 6 |
| S7 | P0 API bug 修复（`_list_skills_impl`） | ~~0.5 / 1 首日~~ **0.5 已完成** |

---

## 本阶段刻意不做（Out of Scope）

| ID | 不做的事 | 原因 |
|----|----------|------|
| O1 | Marketplace **支付**新功能、佣金逻辑扩展 | 无 trust signal 前不做交易 |
| O2 | 新增 Python 业务模块（>58 文件） | 先打通主链路，不叠模块 |
| O3 | 原生飞书 Bot（Lark SDK 全量） | Phase 4 先用 Hermes 快路径；B 路径按需 |
| O4 | 对标 SkillOpt 52 格 benchmark | 差异化在创建+验证，非复制优化器 |
| O5 | chromadb / 新向量库 | 设计书已移除，不 resurrect |
| O6 | 前端大改版 | 通道在 IM/IDE，非 Web UI |
| O7 | user_store / i18n 全量 | 设计书已推迟 |

---

## 允许的小改动

- 修 bug（如 `_list_skills_impl`）  
- 为 Phase 1–2 增加的 **新文件**：`epistemic_bridge.py`、`benchmark_epistemic.py`、`data/benchmarks/epistemic/`  
- 测试、文档、`AI_DEV_LOG.md`  
- 依赖版本 pin（若测试需要）  

---

## 变更请求流程

若 Phase 1–4 期间必须做 Out of Scope 项：

1. 在 `AI_DEV_LOG.md` 记录理由  
2. 更新本文件「例外」小节  
3. 用户明确确认  

---

## 例外

（暂无）
