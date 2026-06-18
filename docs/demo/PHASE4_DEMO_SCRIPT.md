# Phase 4 Demo 脚本（约 3 分钟）

> 存档用途：Cursor MCP 路径 + 认识论摘要。飞书路径见 [`FEISHU_HERMES_CHECKLIST.md`](../channels/FEISHU_HERMES_CHECKLIST.md)。

---

## 场景 A：Cursor MCP（推荐录制）

**环境**：Cursor + SkillOS MCP + `SKILLOS_WORKSPACE_SKILLS=./skills`

| 时间 | 画面 | 旁白要点 |
|:----:|------|----------|
| 0:00 | 打开 Cursor，展示 MCP skillos 已连接 | 「在熟悉的 IDE 里说话，就能沉淀标准 Skill」 |
| 0:20 | 调用 `extract_skill`，粘贴一段退款流程文本 | 「一条 MCP 调用，走 7 步认知管线」 |
| 1:00 | 滚动返回：**Pipeline log** + **认识论摘要** | 「不是裸 markdown — 每条硬规则有验证状态」 |
| 1:30 | 打开 `./skills/<name>/SKILL.md` | 「文件直接进工作区，AgentSkills.io 格式」 |
| 2:00 | 调用 `confirm_pending_claims(confirm_all=true)` | 「人工确认后，Experience → Knowledge」 |
| 2:30 | 再次 `get_skill` 展示「已验证」区 | 「可验证的 Agent Skill，不是一次性生成」 |

**验收对照**：IMPROVEMENT_PLAN Phase 4 — Cursor 一条 MCP 得到 SKILL.md + epistemic 摘要 ✅

---

## 场景 B：飞书群（Hermes）

| 时间 | 画面 | 旁白要点 |
|:----:|------|----------|
| 0:00 | 飞书群 @机器人 | 「团队已在用的 IM，无需打开 SkillOS 桌面」 |
| 0:30 | 发送：「帮我沉淀代码审查流程」 | 与 Cursor 同一套话术（USER_GUIDE） |
| 1:30 | 机器人回复含认识论状态 | session = `feishu:{chat_id}:{user_id}` 续接对话 |
| 2:30 | 发送「确认待审」 | 晋升 + SKILL.md 更新 |

**验收对照**：至少 1 个群完成「对话 → 技能文件」— 需真实飞书环境实测后勾选 checklist。

---

## 录制建议

- 分辨率 1920×1080，字幕含关键 API/MCP 工具名
- 导出文件命名：`phase4-cursor-mcp-YYYYMMDD.mp4`
- 存放：`docs/demo/`（视频文件 gitignore 可只存本脚本 + checklist 截图）
