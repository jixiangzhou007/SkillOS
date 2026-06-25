# Sprint 2 · 组织试点运行手册

> **状态**：可执行 · W5–6
> **DoD**：5 人各创建 1 个技能草稿（org tenant 目录）
> **前置**：`SKILLOS_LEGACY_MODE=false`

---

## 1. 一键初始化试点环境

```bash
# 启动 API
python -m skillos.api.server

# 另一终端：创建组织 + 7 个演示账号
python scripts/pilot_bootstrap.py --org-name "Pilot Corp"
```

产出：
- `data/pilot/manifest.json` — 组织 ID、用户列表（token 脱敏）
- `data/pilot/tokens.local.json` — 本地开发用 JWT（勿提交 git）

| 账号 | 部门 | 角色 |
|------|------|------|
| `pilot_admin` | — | org_admin |
| `champ_cs` | customer-service | Champion |
| `member_cs1/2` | customer-service | member |
| `champ_fin` | finance | Champion |
| `member_fin1/2` | finance | member |

默认密码：`pilot1234`

---

## 2. Web 门户 E2E（Personal / Org 通用）

1. 打开 `http://127.0.0.1:8765/login.html`
2. 用 `champ_cs` / `pilot1234` 登录
3. 顶栏 workspace 下拉 → 选择 **Pilot Corp**
4. 对话区输入：`帮我沉淀电商退款标准流程`
5. 侧边栏「我的」应出现草稿技能（org tenant 路径）

---

## 3. 飞书群手工 dispatch（暂不用 bot）

试点阶段由 Champion 在飞书群收集话术，**手工调用 API** 或让 IT 代发 curl。

### Session 映射

| 字段 | 示例 |
|------|------|
| `channel` | `feishu` |
| `chat_id` | `oc_pilot_cs`（群 ID，试点自定） |
| `user_id` | `ou_champ_cs`（飞书 user id） |
| `dept_id` | `customer-service` 或 `finance` |

合成 session：`feishu:oc_pilot_cs:ou_champ_cs`

### 客服群示例

```bash
TOKEN="<champ_cs JWT from tokens.local.json>"

curl -X POST http://127.0.0.1:8765/api/skills/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我沉淀电商退款标准流程",
    "channel": "feishu",
    "chat_id": "oc_pilot_cs",
    "user_id": "ou_champ_cs",
    "dept_id": "customer-service"
  }'
```

### 财务群示例

```bash
curl -X POST http://127.0.0.1:8765/api/skills/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我沉淀飞书费用报销审批流程",
    "channel": "feishu",
    "chat_id": "oc_pilot_fin",
    "user_id": "ou_champ_fin",
    "dept_id": "finance"
  }'
```

JWT 已含 org tenant 时，**无需** body 再传 `tenant_id`；`dept_id` 用于部门子目录隔离。

---

## 4. Org 管理 API

```bash
# 创建组织（登录用户 → org_admin）
curl -X POST http://127.0.0.1:8765/api/orgs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"My Team"}'

# 邀请成员（需 org_admin）
curl -X POST http://127.0.0.1:8765/api/orgs/org_xxx/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","role":"member","dept_id":"customer-service"}'

# 成员列表
curl http://127.0.0.1:8765/api/orgs/org_xxx/members \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. 试点场景与验收

场景清单见 [`PILOT_SCENARIOS.md`](../sprint0/PILOT_SCENARIOS.md)。

### Sprint 2 DoD 检查表

- [ ] `pilot_bootstrap.py` 成功，7 账号可登录
- [ ] 5 人（含 2 Champion + 3 member）各完成 1 次 dispatch 萃取
- [ ] 技能文件落在 `data/tenants/org/<org_id>/departments/<dept>/skills/` 或 org 根目录
- [ ] Web 门户 workspace 切换后列表隔离正确
- [ ] Champion 培训 1 场（话术 + 确认草稿流程）

### 记录模板（每场 30 分钟访谈）

见 PILOT_SCENARIOS 访谈清单；结论写入飞书文档，Champion 负责在 Web 或 curl 完成首次沉淀。

---

## 6. 故障排查

| 现象 | 处理 |
|------|------|
| 登录后技能列表为空 | 确认 workspace 已切到 Org；检查 JWT 内 `tenant_id` |
| 技能写到 legacy `skills/` | 设置 `SKILLOS_LEGACY_MODE=false` 并重启 |
| dispatch 401 | Header 带 `Authorization: Bearer <token>` |
| 成员看不到 Org workspace | `pilot_admin` 执行 invite API 或重跑 bootstrap |

---

## 7. 下一步（Sprint 3）

- 飞书 bot α（消息自动 → dispatch）
- 审批流 draft → pending → published
- Champion 飞书通知卡片
