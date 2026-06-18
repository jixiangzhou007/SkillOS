# Sprint 12 / Phase 4 — MetaSkill + SkillOpt 门户集成（M13–M18）

> 对应 [`PRODUCT_ROLLOUT_PLAN.md`](../PRODUCT_ROLLOUT_PLAN.md) Phase 4 智能化 · [`ENTERPRISE_ROLLOUT_PLAN.md`](../ENTERPRISE_ROLLOUT_PLAN.md) M18 智能化 v1。

## MetaSkill 流水线

| 能力 | 说明 |
|------|------|
| API 解析 | `GET /api/skills/{name}/metaskill` |
| API 运行 | `POST /api/skills/{name}/metaskill/run`（`dry_run: true` 无 LLM 试运行） |
| 详情标记 | `GET /api/skills/{name}` → `is_metaskill` |
| 前端 Tab | 技能详情「流水线」（MetaSkill 时显示） |
| 前端操作 | 试运行 / 完整运行 · 技能树 ▶ Run |

### 示例

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8765/api/skills/my-pipeline/metaskill

curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_input":"处理订单","dry_run":true}' \
  http://127.0.0.1:8765/api/skills/my-pipeline/metaskill/run
```

## SkillOpt / MoE 进化

| 能力 | 说明 |
|------|------|
| 状态 | `GET /api/evolution/{name}/state`（需 JWT） |
| MoE 路由 | `POST /api/evolution/{name}/route` |
| 优化一轮 | `POST /api/evolution/{name}/optimize` |
| 导出包 | `POST /api/evolution/{name}/export-skillopt`（租户隔离） |
| 前端 | 「进化」Tab：MoE KPI + 优化/导出/对话优化 |

本机 SkillOpt 引擎见 `skillos/evolution/skillopt.py`；外部 Microsoft SkillOpt 互补导出见 [`evolution/SKILLOPT_EXPORT.md`](../evolution/SKILLOPT_EXPORT.md)。

## 验收

- `pytest tests/test_sprint12_intelligence.py`
- 门户：MetaSkill 详情 → 流水线 Tab → 试运行
- 门户：普通技能 → 进化 Tab → 导出 SkillOpt

## 后续（非 MVP）

- ~~流水线可视化 DAG 图~~ → Sprint 13 ✅
- ~~岗位/部门推荐与 MetaSkill 模板库~~ → Sprint 13 ✅
- ~~外部 SkillOpt CLI 联调实测~~ → Sprint 13 ✅
- 流水线 DAG 交互编辑
- 岗位模板一键生成 MetaSkill 到工作区
