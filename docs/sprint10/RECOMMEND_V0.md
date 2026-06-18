# Sprint 10 — 去重 + 推荐 v0（M7–M8）

> 对应 [`PRODUCT_ROLLOUT_PLAN.md`](../PRODUCT_ROLLOUT_PLAN.md) M7–M8 共同基础项。

## 去重（Dedup）

| 能力 | 说明 |
|------|------|
| API | `GET /api/skills/{name}/similar` |
| 算法 | 名称相似度 + 正文词重叠（同租户） |
| 前端 | 技能详情「概览」「认识论」Tab 展示相似技能横幅 |

## 推荐 v0（Recommend）

| 能力 | 说明 |
|------|------|
| API | `GET /api/marketplace/recommendations?limit=6` |
| 逻辑 | 目录高分技能；排除已拥有/名称相似技能 |
| 标签 | `高分精选` / `同类目` / `热门` |
| 前端 | 技能市场首页「为你推荐」横条（无搜索/筛选时） |

## 验收

- `tests/test_sprint9_scale.py::TestMarketplaceReadonly::test_recommendations_excludes_owned`
- `tests/test_portal_e2e.py::test_usage_and_export_with_jwt`

## 后续（非 v0）

- 基于用户行为 / 订阅历史的协同过滤
- Org 部门库内推荐
- 创建技能时实时去重拦截
