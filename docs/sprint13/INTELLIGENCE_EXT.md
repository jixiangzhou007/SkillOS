# Sprint 13 — DAG 可视化 · 岗位模板库 · SkillOpt CLI

> 扩展 [`sprint12/INTELLIGENCE.md`](INTELLIGENCE.md) Phase 4 后续项。

## 1. MetaSkill 流水线 DAG（Mermaid）

| 能力 | 说明 |
|------|------|
| 后端 | `pipeline_to_mermaid()` · `GET /api/skills/{name}/metaskill` → `mermaid` |
| 前端 | 技能详情「流水线」Tab 渲染 flowchart |

## 2. 岗位推荐模板库

| 能力 | 说明 |
|------|------|
| 模块 | `skillos/intelligence/role_templates.py` |
| API | `GET /api/intelligence/role-templates` |
| API | `GET /api/intelligence/role-templates/{role_id}/recommendations` |
| 前端 | 技能市场「岗位技能模板」+ 蓝图 DAG |
| 内置岗位 | 客服、研发、运营、财务、销售 |

## 3. 外部 SkillOpt CLI

| 能力 | 说明 |
|------|------|
| 模块 | `skillos/evolution/skillopt_runner.py` |
| 脚本 | `python scripts/skillopt_cli.py export\|validate\|run` |
| API | `GET /api/evolution/skillopt/cli` |
| API | `POST /api/evolution/{name}/skillopt-run?dry_run=true` |
| 导出增强 | `POST .../export-skillopt` 返回 `cli` 命令块 |

### CLI 示例

```bash
python scripts/skillopt_cli.py export my-skill
python scripts/skillopt_cli.py validate data/exports/skillopt/my-skill-skillopt
python scripts/skillopt_cli.py run my-skill --dry-run

# 挂载外部 SkillOpt（示例）
set SKILLOPT_EXTERNAL_CMD=python -m skillopt.run --skill {best_skill} --traces {traces}
python scripts/skillopt_cli.py run my-skill
```

## 验收

- `pytest tests/test_sprint13_intelligence_ext.py`
- 市场页岗位模板 → 客服蓝图 DAG
- MetaSkill 流水线 Tab 显示 DAG
- 进化 Tab → SkillOpt CLI dry-run
