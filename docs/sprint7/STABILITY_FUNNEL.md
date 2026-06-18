# Sprint 7–8 · 稳定性与漏斗

## 稳定性目标

Personal 公测错误率 **< 1%**（`api_error / (llm_call + api_error)`）。

查询：

```bash
curl http://localhost:8765/api/analytics/stability
```

## 转化漏斗

| 步骤 | 事件 | 触发点 |
|------|------|--------|
| 注册 | `funnel_register` | `POST /api/auth/register` |
| 首个技能 | `funnel_first_skill` | 首次 `save_skill` |
| 创建团队 | `funnel_create_team` | `POST /api/orgs` |
| 复制到公司 | `funnel_copy_to_org` | `POST /api/skills/{name}/copy-to-org` |

查询（需登录）：

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8765/api/analytics/funnel
```

## LLM 脱敏 v1

出站 LLM 请求自动 redact：

- 手机号、身份证、邮箱
- `sk-*` API Key、Bearer Token
- `password=` / `api_key=` 赋值

禁用（开发）：`SKILLOS_SKIP_DESENSITIZE=1`

## 部门配额

`PATCH /api/orgs/{org_id}/departments/{dept_id}/quota`

```json
{"max_skills": 30, "max_llm_monthly": 150}
```

Pilot Batch 1：

```bash
python scripts/pilot_bootstrap.py --batch1
```
