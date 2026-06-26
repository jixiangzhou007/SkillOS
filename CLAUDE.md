# Claude Code — SkillOS 工作说明

本仓库的 AI 协作规则见 **[`AGENTS.md`](AGENTS.md)**。Claude Code 在本项目中工作时**必须遵守**该文件中的强制协作协议。

## 快速 checklist

1. **改代码前** → 读 `docs/AI_DEV_LOG.md` 最新一条
2. **改代码后** → 按模板在 `docs/AI_DEV_LOG.md` 顶部追加记录
3. **架构** → 遵守 `DESIGN.md` §6
4. **测试** → `python -m pytest tests/ -v`
5. **Bench** → `python scripts/run_bench_regression.py`（需 `DEEPSEEK_API_KEY`）

完整说明、约束与命令见 [`AGENTS.md`](AGENTS.md)。
