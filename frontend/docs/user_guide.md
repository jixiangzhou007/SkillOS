# SkillOS 用户话术指南 / User Phrase Guide

> 飞书、微信、Cursor MCP、SkillOS 桌面/API 共用同一套「沉淀协议」。  
> 技术实现：`skillos/skills/intent_router.py` · API：`POST /api/skills/dispatch`

---

## 意图速查

| 你想做什么 | 中文示例 | English example | 路由 |
|------------|----------|-----------------|------|
| 把对话/经验做成标准 Skill | 帮我**沉淀**退款流程 · **做成 skill** · **整理成标准** | Turn this into a **skill** · **Extract** this workflow | `extract` |
| 贴链接学习 | `https://…`（消息中含 URL） | Paste a URL | `learn_url` |
| 上传文件 | 使用上传入口（非纯文字） | Use file upload / MCP `ingest_file` | `ingest` |
| 确认待审声明 | **确认待审** · **确认 1,2** · **采纳全部** | **Confirm pending** · **Confirm 1,2** | `confirm_claims` |
| 团队 Playbook 冷启动 | **冷启动** · **团队手册** · **playbook** | Team **playbook** cold start | `playbook` |
| 普通聊天 | 其他任意内容 | Anything else | `chat` |

---

## 沉淀（extract）

**何时用**：你有一段可重复的方法、流程、检查清单，希望变成 AgentSkills.io 标准的 `SKILL.md`。

**推荐话术**：

- 「帮我沉淀一下代码审查流程」
- 「把这个退款处理做成 skill」
- 「整理成标准技能文档」

**系统行为**：

1. 进入苏格拉底式萃取对话（或续接当前 session）
2. 生成 SKILL.md 后自动跑认识论管道
3. 回复末尾显示：`已验证 N 条 · 待确认 M 条`

---

## 确认待审（confirm_claims）

**何时用**：技能已创建，但有「待确认」的硬规则声明，你人工审核后希望晋升为「已验证知识」。

**推荐话术**：

| 说法 | 含义 |
|------|------|
| `确认待审` / `确认全部` | 晋升当前范围内全部待审声明 |
| `确认 1,2` / `采纳 1和3` | 按认识论状态列表中的序号选择 |
| `技能: 退款流程 确认待审` | 仅确认指定技能下的待审项 |
| 消息中含 `claim_…` ID | 直接确认指定 claim |

**系统行为**：

1. Experience → Knowledge 晋升
2. 同步更新对应 SKILL.md 的 `## 认识论状态` 与 YAML `epistemic` 元数据

**Cursor MCP**：

```text
extract_skill(content="…", mode="skill")
confirm_pending_claims(confirm_all=true)
```

`extract_skill` 返回 **Pipeline log**（7 步）、**认识论摘要**、**Skill path**；设置 `SKILLOS_WORKSPACE_SKILLS=./skills` 可同步到工作区。

---

## 贴 URL（learn_url）

在消息中直接粘贴 `http://` 或 `https://` 链接。

- **可执行方法论** → 7 步技能创建管线
- **概念/参考内容** → 深度知识包（术语表、模式）

若已在萃取对话中，URL 内容会作为研究材料注入当前 session。

---

## 上传文件（ingest）

使用 API `POST /api/skills/ingest` 或 MCP `ingest_file`。

系统按内容类型自动分流：方法论 → Skill；参考材料 → 知识包。

---

## 保守路由原则

- **不确定时不强行萃取** — 避免误触发技能创建
- **「确认」单独出现**（如萃取对话里的「确认，生成」）不会触发 `confirm_claims`；需带「待审」或序号
- 完整触发词表见 `skillos/skills/intent_router.py`
