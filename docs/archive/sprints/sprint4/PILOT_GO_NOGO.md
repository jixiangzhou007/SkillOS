# Sprint 4 · 试点 Go/No-Go 评审清单

> **时机**：M2 末 / Sprint 4 W9–10
> **输入**：[`PILOT_SCENARIOS.md`](../sprint0/PILOT_SCENARIOS.md)、[`PILOT_RUNBOOK.md`](../sprint2/PILOT_RUNBOOK.md)

---

## 量化指标

| 指标 | 目标 | 实际 | 通过 |
|------|------|------|------|
| 已发布技能（org published） | ≥ 20 | | ☐ |
| 6 场景中完成发布 | ≥ 4 | | ☐ |
| 每部门 verified 声明 | ≥ 10 | | ☐ |
| 试点用户完成 draft→publish 全流程 | ≥ 1 条 | | ☐ |
| Cross-tenant 数据泄露 | 0 | | ☐ |
| Champion NPS | ≥ 7 | | ☐ |

---

## 定性检查

- [ ] 客服 / 财务 Champion 能独立 Web 登录 + workspace 切换
- [ ] 成员能在「认识论」Tab 确认 pending 声明
- [ ] org_admin 能在 `/api/approval` 或后续 UI 完成审批
- [ ] 飞书 curl / bot α 至少完成 1 次成功 dispatch
- [ ] 相似技能去重提示被 Champion 认为「有用」
- [ ] 快速模式（≥500 字）减少平均萃取轮次 ≥ 30%

---

## 决策

| 选项 | 条件 |
|------|------|
| **Go** | 量化 ≥80% 通过 + 无 P0 安全/合规问题 |
| **Extend** | 60–80% 通过，延长试点 2 周 |
| **No-Go** | <60% 或存在 cross-tenant / 数据丢失 P0 |

**评审人**：_产品负责人_ · _Champion 代表_ · _信安_
**日期**：________
**结论**：Go / Extend / No-Go

---

## 附录：数据导出

```bash
# 待审 / 已发布技能
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8765/api/approval/queue

# 试点 manifest
cat data/pilot/manifest.json
```
