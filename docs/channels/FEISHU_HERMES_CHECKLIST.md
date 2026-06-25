# 飞书 × Hermes × SkillOS 端到端 Checklist

> Phase 4 M1/M2 · 路径 A（Hermes Gateway → MCP）
> 用户话术见 [`docs/USER_GUIDE.md`](../USER_GUIDE.md)

---

## 前置条件

- [ ] SkillOS API 或 MCP 可运行（`python -m skillos.mcp_server` 或 `skillos --server-only`）
- [ ] Hermes Agent 已安装：`pip install hermes-agent`
- [ ] 飞书开放平台应用已创建（App ID / App Secret）
- [ ] `DEEPSEEK_API_KEY` 或 Hermes 共享模型配置可用

---

## 1. 注册 SkillOS MCP

```bash
hermes mcp add skillos --command python --args "-m" --args "skillos.mcp_server"
hermes mcp test skillos
```

预期：`extract_skill`、`confirm_pending_claims` 等工具 listed。

---

## 2. 配置 Hermes Gateway（飞书）

```bash
hermes gateway add feishu \
  --app-id <APP_ID> \
  --app-secret <APP_SECRET> \
  --webhook-url <YOUR_PUBLIC_WEBHOOK_URL>
```

参考：项目根 [`deployment.md`](../../deployment.md)

---

## 3. Session 映射（M2）

SkillOS dispatch 支持显式 session 或自动构建：

| 字段 | 说明 |
|------|------|
| `channel` | `feishu` |
| `chat_id` | 飞书群 / 会话 ID（`oc_…`） |
| `user_id` | 飞书用户 ID（`ou_…`） |

**合成 session_id**：`feishu:{chat_id}:{user_id}`

实现：`skillos/channels/session_ids.py`

**API 示例**：

```json
POST /api/skills/dispatch
{
  "message": "帮我沉淀退款流程",
  "channel": "feishu",
  "chat_id": "oc_xxx",
  "user_id": "ou_yyy"
}
```

同一群同一用户的萃取对话会续接同一 session。

---

## 4. 群内需验证的场景

| # | 用户发送 | 预期 |
|---|----------|------|
| 1 | 帮我沉淀 XX 流程 | 进入萃取对话 / 返回 skill_active |
| 2 | （完成萃取后） | 回复含「认识论：已验证 N · 待确认 M」 |
| 3 | 确认待审 | promoted ≥ 1，SKILL.md 认识论区更新 |
| 4 | 贴 URL | learn_url 路由（方法论 → skill） |

---

## 5. 产物检查

- [ ] `skills/<name>/SKILL.md` 存在于 SkillOS 数据目录
- [ ] 若设置 `SKILLOS_WORKSPACE_SKILLS=./skills`，工作区有副本
- [ ] Hermes 可用时 `~/.hermes/skills/<name>/SKILL.md` 同步（可选）

---

## 6. 故障排查

| 现象 | 检查 |
|------|------|
| MCP 无响应 | `hermes mcp test skillos` |
| 萃取无认识论摘要 | 确认 `save_skill` 未设 `draft=True` |
| 确认待审无效果 | 声明是否为 Experience/Evidence；说「确认待审」非单独「确认」 |
| Session 未续接 | chat_id + user_id 是否稳定传入 |

---

## 7. 录屏 Demo

脚本见 [`docs/demo/PHASE4_DEMO_SCRIPT.md`](../demo/PHASE4_DEMO_SCRIPT.md)（约 3 分钟）。
