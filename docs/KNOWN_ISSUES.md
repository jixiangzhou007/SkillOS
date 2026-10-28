# SkillOS Known Issues / Limitations（Closed Alpha）

> **版本目标**：v0.3.6 · 2026-10-28
> **用途**：发给 Alpha 用户的预期管理；登录/引导可链到本文。
> **路线图**：[`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md)

## 使用前必须知道

| 项 | 说明 |
|----|------|
| **API Key** | 本地需配置 `DEEPSEEK_API_KEY`（或设置页 BYOK）。无 Key 时沉淀/苏格拉底会失败或降级，属预期。 |
| **默认口令** | 首次部署请改默认管理员密码；勿把含真实密钥的 `.env` 提交或外传。 |
| **端口** | 默认 API/UI：`http://127.0.0.1:8765`。 |
| **Trust Tier** | `Verified` = 双门禁（认识论 ∧ 域内 smoke≥80）。**≠** 官方 SkillsBench 排行榜 SOTA。 |
| **本地 Quick8** | 日常快检 / Gate B 参考；与官方 Bench pass rate **不是同一指标**。 |
| **Hub** | 本地目录 + seed 目录，**不是**应用商店；无支付、无公开 UGC 审核流。 |
| **install-local** | 会把技能复制到本机 Cursor / `.agents` / `.dsh` 技能目录。Draft 默认可装但不宜直接当「已出师」交给模型；请先看 Tier。 |
| **实验技能** | 工作区 `skills/` 下若出现个人试炼目录，不属于发行默认包；Alpha 应以系统参考技能（如 GitHub Pull）为准。 |

## 已知限制（不修或不在本版修）

- 飞书 / 微信通道未作为本版主路径验收。
- 无支付、无多端云同步。
- 未接入 DeepSeek Harness / Cordis 沙箱审批执行链（仅借鉴发现/安装路径）。
- Windows 下部分 shell/路径边界与 Linux CI 行为可能不同。
- Demo Day **人工录像**仍可能滞后于代码；以本机走通 DEMO 剧本为准。

## 遇到问题时

1. 对照 [`DEMO_VERIFIED_SPINE.md`](DEMO_VERIFIED_SPINE.md) 黄金路径逐步排查。
2. 备份或清空本地技能数据前先复制整个 `skills/`（或租户数据目录）。
3. 向邀请人反馈时请注明：卡在哪一步、Trust Tier 是否理解、是否装进 Cursor。

## 诚实承诺（对外口径）

> 在对话中把经验炼成 **Draft / 学徒 / Verified** 的 AgentSkills.io 技能，并安装到 Cursor（或兼容 harness）。

除此以外的能力，一律视为实验或 Known Limitations。
