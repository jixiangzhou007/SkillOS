# Sprint 11 — 治理合规 + Creator 分成预留 + 灾备（M9–M12）

> 对应 [`PRODUCT_ROLLOUT_PLAN.md`](../PRODUCT_ROLLOUT_PLAN.md) Phase 3 治理项。

## 认识论 verified 率（M12 目标 ≥70%）

| 能力 | 说明 |
|------|------|
| 模块 | `skillos/admin/governance.py` |
| Org API | `GET /api/orgs/{id}/admin/governance` |
| 平台 API | `GET /api/analytics/platform` → `governance` 字段 |
| 前端 | 管理控制台「治理合规」KPI 卡片 + 待提升技能列表 |
| 算法 | 按租户技能 frontmatter `epistemic.verified / total_claims` 聚合 |

### 响应示例（org）

```json
{
  "org_id": "org_abc123",
  "target_verified_rate": 0.7,
  "org_verified_rate": 0.8,
  "meets_target": true,
  "skills_with_claims": 5,
  "skills_meeting_target": 4,
  "claims": { "verified": 16, "pending": 4, "total": 20 },
  "at_risk_skills": []
}
```

## Creator 分成预留

| 能力 | 说明 |
|------|------|
| API | `GET /api/billing/creator-summary` |
| 数据源 | `skillos/marketplace/payments.py` → `get_author_revenue` |
| 状态 | `payout_status: reserved` — Stripe/国内支付结算待 M10+ 集成 |

## 灾备

| 能力 | 说明 |
|------|------|
| 脚本 | `python scripts/backup_skillos_data.py` |
| 内容 | `skillhub.db`、`tenants/`、`epistemic_state.json`、其他 `*.db` |
| 输出 | `backups/skillos_backup_YYYYMMDD_HHMMSS.zip`（默认） |

### 恢复步骤（Runbook）

1. 停止 SkillOS API 进程
2. 备份当前 `data/` 目录（以防误操作）
3. 解压备份 zip 到 `SKILLOS_DATA_DIR`（或项目 `data/`）
4. 确认 `skillhub.db` 与 `tenants/` 权限可读
5. 重启 API，验证 `GET /api/analytics/sla` 与 org 技能列表

## 验收

- `pytest tests/test_sprint11_governance.py`
- 管理控制台加载治理 KPI
- `python scripts/backup_skillos_data.py --output /tmp/skillos_test.zip`

## 后续（非 MVP）

- verified 率告警 webhook / 飞书通知
- 部门级治理报表
- Creator 自动打款与税务预留
