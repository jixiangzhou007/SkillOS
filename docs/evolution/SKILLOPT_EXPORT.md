# SkillOpt Export（Phase 7）

与 Microsoft SkillOpt **互补**，不正面竞争：SkillOS 负责认识论验证 + 萃取；SkillOpt 负责 trace-driven 文本编辑优化。

## 导出

```bash
# API
curl -X POST http://127.0.0.1:9876/api/evolution/{skill_name}/export-skillopt

# MCP
export_for_skillopt(skill_name="代码审查")

# Python
from skillos.evolution.skillopt_export import export_for_skillopt
result = export_for_skillopt("代码审查")
print(result.best_skill_path)
```

## 输出目录

默认：`data/exports/skillopt/{skill-name}-skillopt/`

| 文件 | 说明 |
|------|------|
| `best_skill.md` | SkillOpt 训练入口（主文档） |
| `skill.md` | 同上副本 |
| `traces.jsonl` | 执行轨迹（若有） |
| `manifest.json` | 认识论摘要 + 导出元数据 |
| `README.md` | 使用说明 |

## 知识扩散门控

`skillos/knowledge/diffusion_gate.py` 在 Step 8 扩散前检查：

- 含 ERROR 声明 → **禁止**扩散
- 仅 pending、无 verified → **仅建议**，不自动改写目标技能
- 已验证为主 → 允许自动扩散

## 本机优化（无需外部 SkillOpt）

```bash
curl -X POST http://127.0.0.1:9876/api/evolution/{skill_name}/optimize
```
