# ADR 002: 认识论引擎接入策略

**日期**：2026-06-19
**状态**：已采纳（部分实施）
**决策者**：Claude Code

## 上下文

认识论引擎（`skillos/knowledge/epistemology.py`）实现了 Plato/Popper 四层知识验证（Evidence→Experience→Knowledge→Preference）和 Graphiti 双时态模型，是整个产品最独特的差异化功能。但在 v0.2.1 中，它**已实现、有单测、未接入任何主链路**（BASELINE_SUMMARY.md 记录）。

需要决定：在哪些管线节点调用 `record_claim()`，以及如何处理调用失败。

## 决策

采用 **fire-and-forget + 多路径覆盖** 策略：

1. **调用模式**：`try/except` 包裹，失败静默降级（`_log.debug`）。不阻塞主流程。
2. **接入路径**（按优先级）：
   - `_generate()` — 技能文档生成后，从 S_body/S_route/S_trigger 提取 claims
   - `learn_from_url()` — URL 学习管线的 Step 7（沉淀）后
   - `_confirm()` — 用户确认技能后，从对话上下文提取
   - （未来）`_explore()` + `_refine()` — 苏格拉底追问中的关键陈述

## 理由

1. **Fire-and-forget 是最低风险的接入模式**。认识论验证对用户不可见（后端异步处理），不应阻塞技能生成或对话回复。如果 `record_claim()` 抛异常，用户至少拿到了技能文档。

2. **多路径覆盖确保知识不遗漏**。技能萃取有三种入口（对话→生成、URL→学习、手动创建），每种入口产出的知识都需要进入验证管线。只接一个路径会导致知识库不完整。

3. **从 S_body/S_route/S_trigger 提取 claims 是合理的粒度**。每个 S_body 步骤是一个可验证的操作声明，每个 S_route 行是一个决策规则声明，每个 S_trigger 是一个触发条件声明。这些粒度足够细，可以被交叉验证和证伪测试。

4. **`_confirm()` 路径是对话知识的入口**。用户在多轮对话中提供的经验（如"我们公司的退款流程是..."）在确认生成时进入认识论——“用户说的”作为 Experience，后续通过交叉验证升级为 Knowledge。

## 后果

### 已实施
- `_generate()` 路径：每次生成技能自动提取 3-8 个 claims
- `learn_from_url()` 路径：URL 学习后自动记录
- 提取函数 `extract_claims_from_skill()` 在 `agent_learning.py` 中

### 未实施
- `_confirm()` 路径——对话确认后的知识提取
- `_explore()`/`_refine()` 路径——苏格拉底追问中的实时声明捕获
- 前端"认识论"Tab 展示 `epistemic_state.json` 内容（目前只有骨架）

### 设计权衡
- Fire-and-forget 意味着 false positive 的 claims（LLM 编造的内容）也会被记录为 Experience。这是可接受的——认识论引擎的职责正是通过交叉验证和证伪测试来过滤这些 false positives。
- 提取粒度受限于 SKILL.md 的结构——如果 LLM 生成的 S_body 步骤含糊（如"处理退款"），claims 的质量也低。但这是 GIGO 问题，不是接入策略的问题。
