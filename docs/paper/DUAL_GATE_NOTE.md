# Dual Gate Trust Tier — 一页纸短文（Phase T）

> **状态**：Demo Day / arXiv 短文草稿 · 2026-10-28
> **定位**：非完整论文；把 Dual Gate + Trust Tier 写成可对外讲的 1–2 页叙事。
> **完整稿**：[`paper.tex`](paper.tex) · 规划：[`../PAPERS.md`](../PAPERS.md) · Demo：[`../DEMO_VERIFIED_SPINE.md`](../DEMO_VERIFIED_SPINE.md)

---

## Abstract（EN, ~150 words）

Agent skill ecosystems solved distribution (e.g. AgentSkills.io) faster than **trust**. Many pipelines treat extracted procedures as ready-to-run knowledge. SkillOS models the agent as an **apprentice**: acquire tacit know-how via Socratic dialogue, then graduate only under a **Dual Gate**—(A) claim-level epistemology and (B) task-level smoke / local Quick8—into an explicit **Trust Tier** (`draft` | `provisional` | `verified`). Verified skills export as standard `SKILL.md` with `skillos_trust_tier` metadata for Cursor-class hosts. On a generalization cohort, Layer-1 HERITAGE×pack routing yields median domain Quick8 Δ **+45** vs baseline 0 (2×2 ablation). We do **not** claim official SkillsBench SOTA; local Quick8 is a daily gate, distinct from BenchFlow CI.

---

## 中文摘要

Agent Skills 的分发已被标准与市场大体解决；缺口是「抽出来就能信」。SkillOS 用**学徒**隐喻：苏格拉底对话获取默会流程，再经 **Dual Gate**（Gate A 声明级认识论 ∧ Gate B 域内烟测 / 本地 Quick8）才写入 **Trust Tier**。仅 `verified` 表示出师；`provisional` 可安装试用但不宣称已验证。导出遵循 AgentSkills.io，并带 `metadata.skillos_trust_tier`。泛化 cohort 上 Layer 1（HERITAGE × pack）中位 Quick8 Δ **+45**。诚实口径：本地快检 ≠ 官方 SkillsBench pass rate。

---

## 1. Problem

| 常见假设 | 学徒视角的反例 |
|----------|----------------|
| 抽取 = 可用 | 经验与已验证知识被混为一谈 |
| 一次生成 SOP | 默会边界要靠追问与试错 |
| 单一分数 | 声明真假与任务能否跑通是两回事 |

## 2. Dual Gate → Trust Tier

```
Gate A (epistemic)          Gate B (outcome)
  verified claims ≥ 1    ∧    smoke min ≥ 80 (域内)
                 ↓
         trust_tier = verified
  任一缺失 → provisional（学徒态）或 draft
```

产品契约：UI / API / 导出三处同一套枚举；未过 Gate B **不得**标 Verified。

## 3. Evidence（可复现指针）

| 产物 | 路径 / 命令 |
|------|-------------|
| Trust Tier 契约 | `skillos/evaluation/trust_tier.py` |
| Evidence Card | `GET /api/skills/{name}/evidence` |
| Layer 1 ablation | [`experiments/layer1_ablation_results.md`](experiments/layer1_ablation_results.md) |
| 本地回归 | `python scripts/run_bench_regression.py` |
| Demo 剧本 | [`../DEMO_VERIFIED_SPINE.md`](../DEMO_VERIFIED_SPINE.md) |

## 4. Related Work（一句）

正面对比 EVISKILL / CoEvoSkills / OpenSkill / SoK: Agentic Skills（2026）：结果级验证渐成共识；SkillOS 差异在 **claim 分层 × 出师契约 × HITL 获取** 的组合，而非「全球唯一验证」。

## 5. Limitations

- 离线证伪有启发式成分；全量 LLM 证伪成本高。
- Quick8 为日常 Gate B，不替代官方 BenchFlow。
- Demo 录像与完整 `paper.tex` PDF 仍为人工交付项。

## 6. One-liner（对外）

> SkillOS：在对话里把专家经验炼成 **可验证、可安装、可继承** 的 Agent Skills——学徒出师，而不是又一份 AI markdown。
