# Sprint 7–8 · LDAP / OIDC 调研

> **结论**：M4 试点继续飞书 SSO；LDAP/OIDC 排入 M5 Sprint 9+ 实现。

## 需求场景

| 场景 | 协议 | 优先级 |
|------|------|--------|
| 传统企业 AD | LDAP / LDAPS | P1 |
| SaaS / 多云 | OIDC (Azure AD, Okta) | P1 |
| 已有飞书 | OAuth 2.0（已实现 `POST /api/auth/feishu`） | ✅ 试点 |

## 推荐架构

```
IdP (LDAP/OIDC) → SkillOS Auth Gateway → JWT (tenant_id, org_id, role)
                                      → user_workspaces sync
```

## 实现排期（建议）

| 阶段 | 交付 |
|------|------|
| **M4（当前）** | 飞书 SSO + 本地账号 |
| **M5 Sprint 9** | OIDC 通用端点 `/api/auth/oidc/callback` |
| **M6** | LDAP bind + 组→org 映射 |
| **M7+** | SCIM 用户同步 |

## 依赖

- `python-jose` / `authlib` for OIDC
- 组织 `org_settings` 存 IdP metadata URL
- 审计：`audit_log` 记录 SSO 登录

## 风险

- LDAP 密码不落库 → 仅 bind 验证
- OIDC token 与 SkillOS JWT 生命周期对齐（建议 24h + refresh）
