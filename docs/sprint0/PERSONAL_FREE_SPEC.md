# Sprint 0 · Personal Free 功能清单（M3 公测范围）

> **状态**：已定稿 v0.1 · 与 [`PRODUCT_ROLLOUT_PLAN.md`](../PRODUCT_ROLLOUT_PLAN.md) §1.1 对齐

---

## 注册与租户

| 功能 | M3 公测 | 说明 |
|------|:-------:|------|
| 邮箱注册 | ✅ | 验证码或 magic link（Sprint 1 实现） |
| GitHub OAuth | ✅ | Sprint 1 |
| 自动 Personal 租户 | ✅ | Sprint 0 地基 `create_personal_tenant` |
| 微信登录 | ❌ | P2 |

---

## 沉淀能力

| 功能 | M3 | 说明 |
|------|:--:|------|
| Web 对话萃取 | ✅ 简版 | Sprint 6 |
| Cursor MCP | ✅ | personal token |
| MCP extract_skill | ✅ | 单轮长文 |
| 多轮 Agent | ✅ | 与组织共用引擎 |
| 快速模式 | ✅ v1 | Sprint 4 |
| 认识论 pending 自助确认 | ✅ | Sprint 4 UI |

---

## 限额（Free）

| 项 | 限制 |
|----|------|
| 技能数量 | ≤ **10** |
| 平台 LLM 调用 | **50 次/月**（超出提示自带 Key） |
| 可见性 | **仅私有** |
| 公共市场发布 | ❌ M10+ |

---

## 注册流程线框（3 步）

```
1. 欢迎页
   [ GitHub 登录 ]  [ 邮箱注册 ]

2. 配置（可跳过）
   [ 粘贴 DeepSeek API Key ]  或  [ 使用免费 50 次/月 ]

3. 首个技能
   「帮我沉淀一下 _____」
   → 对话 / 粘贴 SOP → 预览 → 保存到个人空间
```

---

## 与 Sprint 0 工程关系

| 工程项 | Personal 依赖 |
|--------|---------------|
| F1 tenants 表 | `create_personal_tenant()` |
| F2 路径隔离 | `TenantContext.personal()` |
| F5 Workspace API | Sprint 2（切换 personal ↔ org） |

---

## 成功指标（M3 公测第 2 周）

- 注册 → 首技能完成率 ≥ **50%**
- 自带 API Key 占比 ≥ **40%**
- 崩溃/500 率 < **1%**
