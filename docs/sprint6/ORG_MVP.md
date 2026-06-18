# Sprint 6 · Org 商用 MVP

> **DoD**：Org 商用 MVP 演示；1 次 Personal→Org 转化实测

---

## 交付

| 能力 | API / 入口 |
|------|------------|
| **管理员控制台** | `GET /api/orgs/{id}/admin/overview` |
| **部门管理** | `GET/POST /api/orgs/{id}/departments` |
| **Org 配额** | `PATCH /api/orgs/{id}/admin/quota` |
| **用量统计** | `GET /api/orgs/{id}/admin/usage` |
| **技能搜索** | `GET /api/skills/?q=关键词&dept_id=` |
| **复制到公司** | `POST /api/skills/{name}/copy-to-org` |
| **创建团队** | 用户菜单 → 创建团队 / `POST /api/orgs` |
| **Agent UI** | 对话区萃取模式指示条 |

---

## Personal → Org 转化流程

1. 个人用户在「我的技能」沉淀技能
2. 用户菜单 → **创建团队** → 自动创建 org + 切换 workspace
3. 技能详情 → **复制到公司**（或 API `copy-to-org`）
4. org_admin 在管理控制台查看成员/部门/用量
5. 审批流发布（Sprint 3）

---

## 验证

```bash
pytest tests/test_sprint6_admin.py -q
```

---

## 演示脚本

```bash
# 1. 注册 + 创建 org
curl -X POST /api/auth/register ...
curl -X POST /api/orgs -H "Authorization: Bearer $TOKEN" -d '{"display_name":"Demo Corp"}'

# 2. 创建部门
curl -X POST /api/orgs/$ORG_ID/departments -d '{"name":"产品部"}'

# 3. 复制技能
curl -X POST /api/skills/my-skill/copy-to-org -d '{"org_id":"'$ORG_ID'"}'
```
