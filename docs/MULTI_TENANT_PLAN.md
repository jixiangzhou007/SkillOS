# SkillOS 多租户架构规划：个人用户 × 企业组织

> **版本**：v1.0 · 2026-06-14
> **⚠️ 执行总纲**：[`PRODUCT_ROLLOUT_PLAN.md`](PRODUCT_ROLLOUT_PLAN.md) v2.0（组织优先 + 个人 Free 同期）
> **本文档定位**：多租户 **架构与数据模型** 技术附录

---

## 一、产品定位矩阵

| 维度 | 个人版（Personal） | 组织版（Organization） |
|------|-------------------|------------------------|
| **典型用户** | 自由职业者、独立开发者、小团队 | 公司各部门、有 IT/信安要求 |
| **核心诉求** | 快速沉淀、Cursor/Claude 自用、可选分享 | 部门共享、审批、审计、合规 |
| **身份** | 邮箱 / GitHub / 微信 OpenID 注册 | 飞书/LDAP/SSO + 组织邀请 |
| **技能可见性** | 私有 → 可选公开到社区 | 个人草稿 → 部门库 → 公司库 |
| **治理** | 自助，无审批（或可选） | Champion 审核 + RBAC |
| **LLM** | 自带 API Key 或平台配额 | 企业统一网关 + 部门配额 |
| **计费** | 免费档 + Pro 订阅 | 按席位 / 按部门 / 私有化部署 |

**设计原则**：个人与组织 **共用同一萃取引擎、认识论管道、MCP 协议**；差异仅在 **租户边界、权限、治理策略、计费**。

---

## 二、租户模型（Tenant Hierarchy）

```
┌─────────────────────────────────────────────────────────────┐
│                      Platform（SkillOS Cloud）               │
│  全局：公共技能市场 · 认证 · 计费 · 系统 Playbook 模板        │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌───────────┐      ┌─────────────┐     ┌─────────────┐
   │ Personal  │      │ Org: 公司 A  │     │ Org: 公司 B  │
   │ tenant    │      │             │     │             │
   │ user_id   │      │ org_id      │     │ org_id      │
   └─────┬─────┘      └──────┬──────┘     └──────┬──────┘
         │                   │                    │
         │            ┌──────┴──────┐      ┌─────┴─────┐
         │            ▼             ▼      ▼           ▼
         │        Dept:财务    Dept:研发  ...        ...
         │            │             │
         ▼            ▼             ▼
    user skills   dept skills   dept skills
    (private)     (shared)      (shared)
```

### 2.1 标识符规范

| ID | 格式 | 说明 |
|----|------|------|
| `user_id` | `usr_{uuid}` | 自然人，跨租户唯一 |
| `org_id` | `org_{uuid}` | 企业组织 |
| `dept_id` | `dept_{org_id}_{slug}` | 组织内部门（可选） |
| `tenant_id` | `personal:{user_id}` 或 `org:{org_id}` | **数据隔离主键** |
| `skill_id` | `sk_{tenant_id}_{slug}` | 技能全局唯一 |

### 2.2 用户与组织关系

一个自然人 (`user_id`) 可同时属于：

- **1 个 Personal 租户**（始终存在，注册即创建）
- **N 个 Organization 租户**（被邀请加入）

登录后通过 **「当前工作空间 Workspace」** 切换：

```
个人空间 │ ACME 公司 · 财务部 │ ACME 公司 · 研发部
```

---

## 三、技能可见性与存储

### 3.1 可见性级别

| 级别 | 代码 | Personal | Organization |
|------|------|:--------:|:------------:|
| 私有草稿 | `private` | ✅ 默认 | ✅ 默认 |
| 工作空间 | `workspace` | — | ✅ 部门/全员可见 |
| 组织内 | `org` | — | ✅ 全公司 |
| 公开社区 | `public` | ✅ 可选发布 | ✅ 经管理员允许 |
| 归档 | `archived` | ✅ | ✅ |

### 3.2 存储布局（目标态）

```
data/
├── tenants/
│   ├── personal/usr_abc123/
│   │   ├── skills/
│   │   │   └── my-refund-flow/SKILL.md
│   │   └── playbook.md          # 个人 Playbook（可选）
│   └── org/acme_corp/
│       ├── org_playbook.md        # 公司级 Playbook
│       ├── departments/
│       │   ├── fin/
│       │   │   └── skills/...
│       │   └── eng/
│       │       └── skills/...
│       └── shared/                # 公司公共库
│           └── skills/...
```

**环境变量演进**：

| 现况 | 目标 |
|------|------|
| `SKILLOS_SKILLS_DIR` 单目录 | `SKILLOS_TENANT_ID` + 租户根路径解析 |
| `SKILLOS_WORKSPACE_SKILLS` | 保留，指向当前 workspace 镜像 |

### 3.3 API 请求上下文

每个请求携带（JWT / Session）：

```json
{
  "user_id": "usr_xxx",
  "tenant_id": "org:acme_corp",
  "dept_id": "dept_acme_fin",
  "role": "publisher",
  "plan": "org_pro"
}
```

现有 `team_context`（`session_manager` / `agent.set_team_context`）**扩展为** `tenant_context`，向后兼容：

```python
tenant_context = {
    "tenant_id": "...",
    "tenant_type": "personal" | "organization",
    "org_id": "",
    "dept_id": "",
    "user_id": "...",
    "channel": "feishu" | "cursor" | "web",
    "chat_id": "",
    "session_id": "",
}
```

---

## 四、身份认证与接入

### 4.1 个人用户

| 方式 | 场景 | 优先级 |
|------|------|:------:|
| 邮箱 + 密码 | Web 注册 | P1 |
| GitHub OAuth | 开发者 | P1 |
| 微信 OpenID | 国内 C 端 | P2 |
| API Token | Cursor/MCP 本地 | ✅ 已有雏形 |

**个人默认路径**：注册 → Personal 租户 → 配置自有 `DEEPSEEK_API_KEY` 或使用平台免费额度 → Cursor MCP 连接。

### 4.2 组织用户

| 方式 | 场景 | 优先级 |
|------|------|:------:|
| 飞书企业 SSO | 国内企业 | P0 |
| LDAP / Active Directory | 传统 IT | P1 |
| SAML 2.0 / OIDC | 通用企业 | P1 |
| 邀请链接 + 域名邮箱 | 中小团队 | P1 |

**组织默认路径**：IT 创建 org → 导入部门结构 → SSO → 员工首次登录自动加入 org 租户 → 飞书/Cursor 带 org 上下文。

### 4.3 统一 Auth 服务（目标模块）

```
skillos/identity/
├── models.py      User, Organization, Membership, Tenant
├── auth.py        login, token, refresh
├── sso/feishu.py
├── sso/oidc.py
└── middleware.py  注入 tenant_context 到每个 API/MCP 请求
```

与现有 `marketplace/auth.py`（SkillHub RBAC）**合并演进**：SkillHub 变为 **组织租户内的权限层**，Platform 层管跨租户身份。

---

## 五、权限模型（RBAC × ABAC）

### 5.1 平台级角色（Personal 租户）

| 角色 | 权限 |
|------|------|
| `owner` | 全部个人技能 CRUD、发布 public、管理 API Key |
| （无 admin） | 个人租户仅一人 |

### 5.2 组织级角色（继承 SkillHub）

| 角色 | 权限 |
|------|------|
| `org_admin` | 管理成员、部门、SSO、配额、审计导出 |
| `reviewer` | 审批技能发布、确认认识论 pending |
| `publisher` | 创建并提交技能到部门库 |
| `member` | 使用/订阅技能、创建私人草稿 |

### 5.3 属性策略（ABAC 示例）

```
IF tenant_type == "organization" AND skill.visibility == "workspace"
   THEN require membership(dept_id) OR role >= reviewer

IF skill contains tag "pii-sensitive"
   THEN block LLM external call OR require org.plan == "private_deploy"
```

---

## 六、产品体验差异

### 6.1 个人版功能集

| 功能 | 说明 |
|------|------|
| 对话/MCP 萃取 | ✅ 完整引擎 |
| 认识论 verified/pending | ✅ 自助确认 |
| 技能版本 | ✅ |
| 发布到公共市场 | 可选（Pro） |
| 团队 Playbook | 个人 Playbook（轻量） |
| 审批流 | ❌ |
| 部门隔离 | ❌ |
| 审计导出 | ❌（仅个人历史） |

### 6.2 组织版功能集

| 功能 | 说明 |
|------|------|
| 个人版全部能力 | ✅ |
| 部门/公司技能库 | ✅ |
| Champion 审批流 | ✅ |
| 公司 Playbook 强制注入 | ✅ |
| SSO + 审计 | ✅ |
| 管理员控制台 | ✅ |
| 配额与成本分摊 | ✅ |
| 私有化部署选项 | Enterprise |

### 6.3 同一用户的 UI 切换

```
┌──────────────────────────────────────┐
│ [个人空间 ▼]  沉淀新技能  我的技能    │
├──────────────────────────────────────┤
│  下拉：                               │
│  · 个人空间（仅自己）                  │
│  · ACME 公司                          │
│    ├ 财务部                           │
│    └ 研发部                           │
└──────────────────────────────────────┘
```

萃取 Agent 的 `start()` 开场白随 workspace 变化：

- 个人：「帮你沉淀个人工作流…」
- 组织：「帮你沉淀 **财务部** 的标准流程，将遵循公司 Playbook…」

---

## 七、商业与配额（预留）

| 计划 | 对象 | 技能数 | LLM 调用 | 协作 | 价格模型 |
|------|------|--------|----------|------|----------|
| **Free** | 个人 | 10 | 50 次/月 | — | 免费 |
| **Pro** | 个人 | 无限 | 自带 Key 或 500 次/月 | — | 订阅 |
| **Team** | 小组织 ≤20 人 | 无限 | 共享池 2000 次/月 | 1 个共享库 | 席位 |
| **Business** | 企业 | 无限 | 部门配额 | 部门库+审批 | 席位 |
| **Enterprise** | 大型 | 无限 | 私有 LLM | 全功能+私有化 | 定制 |

**实现预留**：`tenant.plan`、`usage_counters` 表、超限 soft-block 提示升级。

---

## 八、数据隔离与安全

| 层级 | 个人 | 组织 |
|------|------|------|
| 存储路径 | `tenants/personal/{user_id}/` | `tenants/org/{org_id}/` |
| 查询过滤 | `WHERE tenant_id = ?` 强制 | + `dept_id` 可选 |
| LLM 请求 | 用户 Key 或平台代付 | 企业网关，日志归 org |
| 备份 | 用户导出 | org 管理员全量备份 |
| 删除账号 | GDPR 式删除个人租户 | org 管理员移除成员，技能 ownership 转移 |
| 跨租户访问 | **禁止**（API 层 assert） | 公共市场只读 `public` 技能 |

**渗透测试必测**：用户 A 不能 list/get 用户 B 或 org B 的 `private`/`workspace` 技能。

---

## 九、与现有代码的映射

| 现模块 | 现况 | 目标改造 |
|--------|------|----------|
| `skill_store.py` | 单 `SKILLOS_SKILLS_DIR` | `resolve_skills_dir(tenant_context)` |
| `session_manager.py` | `user_id`, `chat_id` | + `tenant_id`, `org_id`, `dept_id` |
| `agent.set_team_context` | team_context dict | 别名 `set_tenant_context`，字段扩展 |
| `marketplace/auth.py` | 单库 users + team 字段 | memberships 表 `(user_id, org_id, role)` |
| `playbook.py` | 全局/按 chat 绑定 | 层级：org → dept → personal 覆盖 |
| `api/skills.py` `_persist_created_skill` | creator 字符串 | + tenant_id, visibility, dept_id |
| `mcp_server.py` | 无租户 | 启动参数或 env 默认 tenant；Cloud 模式带 token |

---

## 十、实施路线图（与 enterprise 计划对齐）

```
                    Personal          Organization
Phase A (M1-2)      试点共用引擎      企业试点（ENTERPRISE Phase 0）
Phase B (M3-5)      身份+Personal租户   org租户+SSO+部门库（ENTERPRISE Phase 1）
Phase C (M6-9)      公共市场+Pro计费    全面推广（ENTERPRISE Phase 2）
Phase D (M10-12)    社区生态            治理合规（ENTERPRISE Phase 3）
Phase E (M13-18)    Creator 经济        私有化+智能化（ENTERPRISE Phase 4）
```

### Phase B 核心交付（多租户 MVP，建议 8–10 周）

| 序号 | 任务 | 个人 | 组织 | 周 |
|:----:|------|:----:|:----:|:--:|
| B1 | `tenants` 表 + `tenant_context` 中间件 | ✅ | ✅ | 1 |
| B2 | 技能路径按 tenant 隔离 | ✅ | ✅ | 1 |
| B3 | 注册/登录（邮箱+GitHub） | ✅ | — | 2 |
| B4 | 创建 org + 邀请成员 | — | ✅ | 1 |
| B5 | 飞书 SSO + org 自动加入 | — | ✅ | 2 |
| B6 | Workspace 切换 API | ✅ | ✅ | 1 |
| B7 | visibility + 审批流 | 可选 | ✅ | 2 |
| B8 | 隔离渗透测试 + 文档 | ✅ | ✅ | 1 |

**MVP 验收**：

- [ ] 同一邮箱：个人空间技能 ≠ 公司空间技能
- [ ] 组织成员 A 看不到 B 部门 `workspace` 技能（非成员）
- [ ] Cursor MCP 带 token 自动解析 tenant
- [ ] 个人用户零配置可沉淀 1 个技能

---

## 十一、MCP / Cursor 双模式连接

### 个人用户（本地优先）

```json
{
  "mcpServers": {
    "skillos": {
      "command": "python",
      "args": ["-m", "skillos.mcp_server"],
      "env": {
        "SKILLOS_TENANT_ID": "personal:usr_xxx",
        "DEEPSEEK_API_KEY": "sk-..."
      }
    }
  }
}
```

### 组织用户（Cloud 或企业内网）

```json
{
  "mcpServers": {
    "skillos": {
      "command": "npx",
      "args": ["-y", "@skillos/mcp-bridge"],
      "env": {
        "SKILLOS_API_URL": "https://skillos.company.com",
        "SKILLOS_TOKEN": "org_token_..."
      }
    }
  }
}
```

Bridge 负责：Token 刷新、tenant 上下文、企业脱敏策略下发。

---

## 十二、迁移策略（现有单机部署 → 多租户）

| 步骤 | 动作 |
|------|------|
| 1 | 现有 `skills/` 映射为 `tenants/org/default/` 或 `personal/migration/` |
| 2 | 所有 skill frontmatter 补 `tenant_id`, `visibility` |
| 3 | API 默认 tenant = `personal:local` 兼容模式（env `SKILLOS_LEGACY_MODE=true`） |
| 4 | Deprecation 警告 2 个版本后强制 tenant_id |

---

## 十三、开放决策（需产品确认）

| # | 问题 | 选项 |
|---|------|------|
| 1 | 个人技能能否一键「贡献给组织」？ | 复制 vs 移动 vs 链接共享 |
| 2 | 公共市场是否 Moderation？ | 人工 / AI 预审 / 举报 |
| 3 | 组织离职员工个人草稿？ | 删除 / 转移给 manager |
| 4 | 私有化部署是否支持个人版？ | 仅 org / 两者 |
| 5 | 同一技能多 org 任职时 Playbook 冲突？ | 当前 workspace 的 org Playbook 优先 |

---

## 十四、文档与下一步

| 文档 | 更新 |
|------|------|
| [`ENTERPRISE_ROLLOUT_PLAN.md`](ENTERPRISE_ROLLOUT_PLAN.md) | 作为 Organization 轨道的执行细则 |
| 本文 | Personal + Org 统一架构 |
| `PROJECT_DESIGN.md` | 后续补「多租户」章节引用 |

**本周建议**：

1. 产品确认 **Phase B 优先级**（先 org 还是先 personal 注册）
2. 架构评审：`tenant_id` 贯穿 `skill_store` / API / MCP 的 PR 设计
3. 数据库 migration v3：`organizations`, `memberships`, `tenants`, `skill_metadata`

---

*变更记录见 `docs/AI_DEV_LOG.md`*
