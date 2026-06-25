# SkillOS 产品推广总计划 v2.0

> **版本**：v2.0 · 2026-06-14
> **战略决策**：**组织优先（收入与深度）+ 个人 Free 同期（获客与口碑）**
> **资源配比**：研发约 **70% 组织轨 / 30% 个人轨**（前 6 个月）
> **周期**：12 个月主计划 + 6 个月智能化延伸
> **取代关系**：本文件为 **唯一执行总纲**；细节架构见 [`MULTI_TENANT_PLAN.md`](MULTI_TENANT_PLAN.md)，组织治理见 [`ENTERPRISE_ROLLOUT_PLAN.md`](ENTERPRISE_ROLLOUT_PLAN.md)（作为组织轨附录）

---

## 〇、战略一句话

**同一平台、两套租户**：组织轨打穿「部门技能库 + 审批 + 飞书」拿付费与标杆；个人轨同步开放 **Free 注册 + 私有沉淀 + Cursor MCP**，为 Pro 与向组织转化蓄水。

```
                    ┌─────────────────────────────────┐
                    │         SkillOS Platform         │
                    │   引擎 · 认识论 · MCP · 计费    │
                    └───────────────┬─────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │ 70% 资源 · 优先交付                        │ 30% 资源 · 同期上线
              ▼                                             ▼
    ┌─────────────────────┐                       ┌─────────────────────┐
    │  Organization 轨     │                       │  Personal Free 轨    │
    │  试点→SSO→部门库     │                       │  注册→私有库→MCP     │
    │  审批→全公司推广     │                       │  50次/月·自带Key     │
    └─────────────────────┘                       └─────────────────────┘
              │                                             │
              └──────────────────┬──────────────────────────┘
                                 ▼
                    个人用户 ──「创建团队」──→ 组织租户转化
```

---

## 一、双轨产品定义（同期上线范围）

### 1.1 Personal Free（M3 公测）

| 能力 | Free 包含 | 刻意不做（后续 Pro） |
|------|-----------|---------------------|
| 注册 | 邮箱 + GitHub OAuth | 微信登录 |
| 租户 | 自动 `personal:{user_id}` | — |
| 沉淀 | 多轮对话 + MCP `extract_skill` | 快速模式增强 |
| 技能数 | ≤ **10** 个 | 无限 |
| LLM | **自带 API Key** 或平台 **50 次/月** | 500 次/月 |
| 可见性 | **仅私有** | 发布公共市场 |
| 认识论 | 自助 confirm pending | — |
| 通道 | Cursor MCP + Web 极简门户 | 移动端 App |
| 审批 | 无 | — |

### 1.2 Organization（M2 试点 → M4 商用）

| 能力 | 试点 (M2) | 商用 (M4+) |
|------|-----------|------------|
| 开通 | 邀请制 1–2 家试点 org | 自助创建 org + 付费席位 |
| 身份 | 飞书 SSO（试点） | + LDAP/OIDC |
| 结构 | 单 org 多部门 | 部门树 + 公司公共库 |
| 治理 | Champion 人工审批 | 审批流 + RBAC |
| 技能 | 部门库 | + 审计 + 配额报表 |
| LLM | 企业统一 Key | 部门配额 + 脱敏 |
| 通道 | 飞书群 bot | + 企业 Cursor 批量 token |

### 1.3 转化路径（Personal → Org）

| 触发 | 动作 |
|------|------|
| 个人点击「创建团队 / 邀请同事」 | 创建 `org` 租户，个人升为 `org_admin` |
| 个人技能「复制到公司」 | **复制**（非移动）到 org 部门库，进入审批 |
| 同一邮箱 | 保留 Personal 空间 + 加入 Org，Workspace 切换 |

---

## 二、12 个月里程碑总览

| 月 | 组织轨（优先） | 个人轨（同期） | 共同基础 |
|:--:|----------------|----------------|----------|
| **M1** | 试点 2 部门启动；信安评审 | — | **Sprint 0–2：租户隔离 MVP** |
| **M2** | 试点 ≥20 技能；飞书 bot 内测 | — | 租户 + 审计 + Workspace API |
| **M3** | 第 2 家 org 试点 | **Personal Free 公测** | 注册 + Personal 门户 |
| **M4** | Org 商用 MVP（SSO+审批+部门库） | Free 稳定；埋点转化漏斗 | 渗透测试通过 |
| **M5–M6** | Batch 推广 50% 部门 | Pro 内测（可选） | 配额计费 v1 |
| **M7–M8** | 全公司 / 5+ 外部 org 客户 | 公共市场 **只读** 浏览 | 去重 + 推荐 v0 |
| **M9–M12** | 治理合规 verified≥70% | **Pro 上线** + Creator 分成预留 | SLA + 灾备 |

---

## 三、成功指标（双轨分列）

### 3.1 组织轨（12 个月）

| 指标 | M4 | M8 | M12 |
|------|-----|-----|------|
| 付费/试点 org 数 | 2 | 5+ | 10+ |
| 已发布部门技能 | 40 | 150 | 300+ |
| verified 率 | 50% | 60% | **70%** |
| 飞书 bot 月活用户 | 50 | 200 | 500+ |
| 信安/审计 | 有条件通过 | 全量审计 | 零 P0 事故 |

### 3.2 个人轨（12 个月）

| 指标 | M3 公测 | M6 | M12 |
|------|---------|-----|------|
| 注册用户 | 200 | 2,000 | 10,000 |
| 完成首技能沉淀 | 100 | 800 | 4,000 |
| Personal→Org 转化 | — | 5 org | 30 org |
| Free→Pro 转化 | — | 内测 | **3–5%** |
| 自带 Key 占比 | 60% | 50% | 40% |

---

## 四、组织与资源

### 4.1 团队（12 个月）

| 角色 | FTE | 主责轨道 |
|------|-----|----------|
| Tech Lead / 架构 | 1 | 共同基础 |
| 后端 | 1.5 | **70% Org / 30% Personal** |
| 前端 | 0.75 | 50/50（Org 控制台 + Personal 门户） |
| 产品 | 0.5 | 双轨 PRD |
| 设计 | 0.25 | 门户 + 飞书卡片 |
| IT/运维 | 0.25 | Org 部署为主 |
| 客户成功 | 0.5（M4+） | Org 试点陪跑 |
| 部门 Champion | 0.1×N | Org |

### 4.2 研发容量分配原则

```
每个 Sprint（2 周）：
  · P0 组织需求     → 必须完成，占 70% story points
  · P0 共同基础     → 租户/Auth/隔离，两轨依赖
  · P1 个人 Free    → 占 30%，不可阻塞 Org P0
  · P2 个人增强     → 有余量才做
```

---

## 五、共同基础（必须先于两轨功能）

> **Sprint 0–2（M1 第 1–6 周）**：无此层，两轨不能安全上线。

| ID | 交付 | 验收 |
|----|------|------|
| **F1** | `tenant_id` 数据模型 + DB migration v3 | `organizations`, `memberships`, `tenants` 表 |
| **F2** | `skill_store.resolve_path(tenant_context)` | 个人/org 路径隔离 |
| **F3** | Auth 中间件：JWT 含 `user_id`, `tenant_id`, `tenant_type` | 无 token 拒绝写操作 |
| **F4** | `tenant_context` 贯穿 API / session / `_persist_created_skill` | 集成测试 cross-tenant 403 |
| **F5** | Workspace 切换 API `POST /api/workspaces/switch` | 同一用户切换 personal↔org |
| **F6** | 审计日志：技能 CRUD + workspace 切换 | 可按 user 导出 |
| **F7** | `SKILLOS_LEGACY_MODE` 迁移旧 `skills/` | 现有部署不中断 |

---

## 六、Sprint 级计划（前 6 个月 · 12 个 Sprint）

### Sprint 0（W1–2）— 租户地基

| 轨 | 任务 | 负责人 |
|----|------|--------|
| 共同 | F1 DB migration + `skillos/identity/models.py` | 后端 |
| 共同 | F2 技能路径按 tenant 隔离 | 后端 |
| 共同 | F7 legacy 迁移脚本 | 后端 |
| Org | 试点需求访谈定稿（2 部门 × 3 场景） | 产品 |
| Personal | Free 功能清单 + 注册流程线框 | 产品 |

**DoD**：pytest 新增 tenant 隔离用例全绿；旧单机模式仍可用。

---

### Sprint 1（W3–4）— Auth + 审计

| 轨 | 任务 |
|----|------|
| 共同 | F3 JWT 签发/校验；`identity/middleware.py` |
| 共同 | F4 `session_manager` + `api/skills.py` 注入 tenant |
| 共同 | F6 审计扩展（create/update/delete skill） |
| Org | 飞书开放平台应用创建（试点 org） |
| Personal | 邮箱注册 + GitHub OAuth 后端 API |

**DoD**：curl 带 token 创建技能写入正确 tenant 目录。

---

### Sprint 2（W5–6）— Workspace + 试点启动

| 轨 | 任务 |
|----|------|
| 共同 | F5 Workspace 切换 + 列表 API |
| Org | 创建 org + 邀请成员 + 角色 `org_admin/member` |
| Org | **试点启动**：2 部门、飞书群手工 dispatch（暂不用 bot） |
| Org | Champion 培训 1 场 |
| Personal | Personal 租户注册后自动 provisioning |
| Personal | Web 门户 v0：登录 + 我的技能列表 |

**DoD**：Org 试点 5 人各创建 1 个草稿；Personal 注册 E2E 通。

---

### Sprint 3（W7–8）— Org 审批 + 飞书 bot α

| 轨 | 任务 |
|----|------|
| Org | `skills/approval.py` 状态机 draft→pending→published |
| Org | Champion 审批 API + 飞书通知卡片 |
| Org | 飞书 bot α：消息 → `dispatch` extract |
| Org | 部门 Playbook 绑定 `dept_id` |
| Personal | MCP：token 解析 personal tenant |
| Personal | 自带 Key 配置页 + 50 次/月计数器 |

**DoD**：Org 完成 1 条「草稿→发布」全流程；Personal MCP 沉淀 1 skill。

---

### Sprint 4（W9–10）— 试点验收 + Personal 抛光

| 轨 | 任务 |
|----|------|
| Org | 试点 Go/No-Go 评审；≥20 已发布技能 |
| Org | 信安评审材料提交 |
| Org | 去重提示（相似 skill cosine/名称） |
| Personal | 认识论 pending 确认 UI |
| Personal | 快速模式 v1（长文本跳过部分 EXPLORING） |
| Personal | 注册 onboarding（3 步引导） |

**DoD**：试点报告；Personal 内测 20 用户。

---

### Sprint 5（W11–12）— M3 个人公测 + Org 第 2 家

| 轨 | 任务 |
|----|------|
| **Personal** | **Personal Free 公测发布** |
| Personal | 限额 enforcement（10 skill / 50 LLM） |
| Org | 第 2 家 org 试点 onboard |
| Org | 飞书 SSO OAuth 完整流 |
| 共同 | F8 渗透测试（cross-tenant）修复 |

**DoD**：公测公告；0 cross-tenant 漏洞。

---

### Sprint 6（W13–14）— Org 商用 MVP

| 轨 | 任务 |
|----|------|
| Org | 管理员控制台 v1（成员/部门/配额） |
| Org | 部门技能库浏览 + 搜索 |
| Org | 「个人技能复制到公司」API |
| Personal | 门户 v1：萃取对话 Web 版（简版 Agent UI） |
| Personal | 「创建团队」→ org 转化流 |
| 共同 | 用量统计表 `usage_events` |

**DoD**：Org 商用 MVP 演示；1 次 Personal→Org 转化实测。

---

### Sprint 7–8（M4）— 稳定 + 推广 Batch 1

| 轨 | 任务 |
|----|------|
| Org | LDAP/OIDC 调研 + 排期（若试点需要） |
| Org | 配额按部门；LLM 脱敏规则 v1 |
| Org | Batch 1：再扩 2 部门 |
| Personal | 稳定性：错误率 <1%；文档站 |
| Personal | 转化漏斗埋点 |
| 共同 | HA 部署（2 节点） |

---

### Sprint 9–12（M5–M6）— 规模化

| 轨 | 任务 |
|----|------|
| Org | 全公司/多 org 推广；200 技能目标 |
| Org | 审计导出 CSV；SLA 监控 |
| Personal | Pro 功能定义 + 内测（无限 skill、500 次/月） |
| Personal | 公共市场 **只读** 目录（无 UGC 发布） |
| 共同 | 计费集成预留（Stripe/国内支付调研） |

---

## 七、组织轨分阶段（附录精要）

与 [`ENTERPRISE_ROLLOUT_PLAN.md`](ENTERPRISE_ROLLOUT_PLAN.md) 对齐，按 v2 节奏压缩：

| 原 Phase | v2 对应 | 关键交付 |
|----------|---------|----------|
| Phase 0 试点 | M1–M2, Sprint 2–4 | 2 部门、20 技能 |
| Phase 1 平台化 | M3–M4, Sprint 5–8 | SSO、审批、控制台 |
| Phase 2 推广 | M5–M8, Sprint 9–12+ | 200 技能、5+ org |
| Phase 3 治理 | M9–M12 | verified 70%、审计 |
| Phase 4 智能 | M13–M18 | MetaSkill、SkillOpt |

---

## 八、个人轨分阶段

| 阶段 | 时间 | 交付 |
|------|------|------|
| **P0 内测** | M2 末 | 团队 dogfood + 20 种子用户 |
| **P1 Free 公测** | **M3** | 注册、私有库、MCP、50 次/月 |
| **P2 增长** | M4–M6 | Onboarding、快速模式、创建团队转化 |
| **P3 Pro** | M7–M9 内测，M10 上线 | 无限 skill、500 次/月、优先支持 |
| **P4 社区** | M10+ | 公共市场 UGC、Creator 分成（研究） |

---

## 九、技术模块路线图

```
M1          M2          M3          M4          M6          M12
│           │           │           │           │           │
identity ───┴───────────┴───────────┴───────────┴───────────┘
skill_store (tenant paths)
            approval ───┴───────────┘
            feishu bot ─┴───────────┘
                        portal ─────┴───────────┘
                                    billing ────┴───────────────┘
            usage/quota ────────────┴───────────┴───────────────┘
```

**新模块清单**：

| 模块 | 路径 | 最早 Sprint |
|------|------|-------------|
| Identity | `skillos/identity/` | 0 |
| Approval | `skillos/skills/approval.py` | 3 |
| Feishu channel | `skillos/channels/feishu.py` | 3 |
| Usage | `skillos/billing/usage.py` | 5 |
| Portal | `portal/` 或 `skillos/ui/web/` | 2–6 |
| Org admin | `skillos/admin/` | 6 |

---

## 十、Go-to-Market

### 10.1 组织（优先）

| 阶段 | 动作 |
|------|------|
| M1 | 内部 2 部门试点 + 1 家友好外部 org（可选） |
| M4 | 「部门技能库」案例白皮书 |
| M6 | 席位制报价：Team / Business |
| M8 | 渠道：飞书应用市场、Hermes 生态 |

### 10.2 个人 Free（同期）

| 阶段 | 动作 |
|------|------|
| M3 | Product Hunt / 开发者社区、Cursor 论坛 |
| M4 | 「10 分钟沉淀你的第一个 Skill」教程 |
| M6 | Personal→Org 邀请奖励（org 首月席位折扣） |
| M10 | Pro 订阅 |

---

## 十一、风险与对策

| 风险 | 对策 |
|------|------|
| 两轨抢资源，Org 延期 | **硬规则 70/30**；Personal 仅 P1，不抢 Org P0 |
| Personal 滥用 Free 额度 | 50 次/月 + 注册验证 + 速率限制 |
| 个人/org 数据混淆 | Sprint 5 前必须渗透测试通过 |
| Org 销售周期长 | M1 即锁试点 org LOI |
| 引擎质量波动 | 可行性脚本进 CI weekly（mock LLM 结构；LLM 抽检） |

---

## 十二、预算（12 个月 · 粗估）

| 项 | 金额 |
|----|------|
| 研发人力（3 FTE 等效） | ¥80–120 万 |
| 云 infra + LLM 平台代付（Personal Free 池） | ¥5–15 万 |
| 安全审计 | ¥8–12 万 |
| 客户成功 / 试点 | ¥10 万 |
| **合计** | **¥100–160 万** |

Personal Free LLM 池按 **50 次×1 万用户上限** 封顶预算；超出强制自带 Key。

---

## 十三、本周启动清单（Day 1–7）

| # | 动作 | 负责 | 轨 |
|---|------|------|-----|
| 1 | 确认 Sprint 0 backlog 进项目管理 | Tech Lead | 共同 |
| 2 | 锁试点 2 部门 + 1 外部 org LOI | Sponsor | Org |
| 3 | 飞书应用 + 信安并行评审预约 | IT | Org |
| 4 | Personal Free PRD 1 页（本文 §1.1）评审 | 产品 | Personal |
| 5 | 创建 `skillos/identity/` 骨架 PR | 后端 | 共同 |
| 6 | 定公测域名 + 注册合规（用户协议/隐私） | 法务 | Personal |
| 7 | Champion 名单 + 试点 3 场景 | 业务部门 | Org |

---

## 十四、文档索引

| 文档 | 用途 |
|------|------|
| **本文 v2.0** | 双轨执行总纲 |
| [`MULTI_TENANT_PLAN.md`](MULTI_TENANT_PLAN.md) | 租户/Auth/存储架构 |
| [`ENTERPRISE_ROLLOUT_PLAN.md`](ENTERPRISE_ROLLOUT_PLAN.md) | 组织治理政策附录 |
| [`USER_GUIDE.md`](USER_GUIDE.md) | 用户话术 |
| [`IMPROVEMENT_PLAN.md`](IMPROVEMENT_PLAN.md) | 引擎能力（已完成 Phase 0–7） |

---

## 十五、决策记录

| 日期 | 决策 | 状态 |
|------|------|------|
| 2026-06-14 | **组织优先 + 个人 Free 同期** | ✅ 确认 |
| 2026-06-14 | 研发 70/30 配比 | ✅ 确认 |
| 2026-06-14 | 个人→org 技能用 **复制** 非移动 | ✅ 确认 |
| 2026-06-14 | M3 Personal Free 公测（不等到 Org 商用） | ✅ 确认 |
| 待定 | Pro 定价 | 待 M6 前 |
| 待定 | 公共市场 UGC 审核策略 | 待 M8 前 |

---

*下一修订：M2 试点 Go/No-Go 后更新 Sprint 7–12 细节。*
