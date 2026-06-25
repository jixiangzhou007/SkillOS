# Sprint 5 · Personal Free 公测

> **状态**：可发布 · M3
> **DoD**：公测公告就绪；cross-tenant 测试 0 漏洞

---

## 新能力

| 能力 | 说明 |
|------|------|
| **Personal Free 限额** | ≤10 技能；50 次/月平台 LLM |
| **BYOK** | `POST /api/usage/byok` 配置自带 Key 后豁免 LLM 额度 |
| **用量查询** | `GET /api/usage/me` |
| **飞书 SSO** | `POST /api/auth/feishu`（需 `FEISHU_APP_ID/SECRET`） |
| **Cross-tenant 修复** | `GET /api/skills/{name}` JWT 租户隔离 |
| **第 2 家 Org** | `python scripts/pilot_bootstrap.py --org-name "Pilot Corp B"` |

---

## 公测公告（草案）

**SkillOS Personal Free 现已开放**

- 注册即得个人技能空间（对话即沉淀）
- 免费额度：10 个技能 + 每月 50 次 AI 萃取
- 支持 Cursor MCP（设置 `SKILLOS_MCP_TOKEN`）
- 团队版试点请联系管理员

注册：`https://<your-host>/login.html`

---

## 环境变量

| 变量 | 用途 |
|------|------|
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书 OAuth |
| `SKILLOS_SKIP_USAGE` | `true` 关闭限额（开发） |

---

## 验证

```bash
pytest tests/test_sprint5_quotas.py tests/test_sprint3_approval.py -q
```
