# SkillOS — AI Skill Operating System

> **SkillOS**：在飞书、Cursor 里对话，沉淀**可验证**的 Agent Skills — 不是又一份 AI 生成的 markdown。  
> 认识论引擎 + 7 步萃取管线 + **三层 DNA** + 本地 SkillsBench 闭环；证据见 [Epistemic Benchmark](docs/paper/experiments/epistemic_results.md)、[Layer 1 Ablation](docs/paper/experiments/layer1_ablation_results.md)、[本地 Bench 指南](docs/BENCHMARK_LOCAL.md)。

给 AI Agent 造子弹的兵工厂。基于 Hermes Agent 底座，通过 MCP 协议接入 Claude Code、Cursor、飞书/微信（Hermes Gateway）。

## 快速开始

```bash
# 安装
cd SkillOS && pip install -e .

# 启动（三选一）
skillos                          # 桌面应用
skillos --server-only            # API 服务 (http://127.0.0.1:9876)
skillos-mcp                      # MCP 服务器 (Claude Code / Cursor)

# 验证
curl http://127.0.0.1:9876/health
# → {"status": "ok", "version": "0.2.1"}
```

## 配置

在项目根目录创建 `.env`：

```bash
# 云模式（推荐）
DEEPSEEK_API_KEY=sk-your-key
DEEPSEEK_MODEL=deepseek-v4-flash

# 本地模式（无需 API key）
# 不设 DEEPSEEK_API_KEY，自动切换到 Ollama
# 需先执行: ollama pull llama3.2

# 角色分离（省钱）
SKILLOS_EVOLVER_MODEL=deepseek-v4-flash   # 进化用小模型
SKILLOS_EXECUTOR_MODEL=deepseek-v4-pro    # 执行用大模型
```

## AI 客户端接入

### Claude Code

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "skillos": {
      "command": "python",
      "args": ["-m", "skillos.mcp_server"]
    }
  }
}
```

### Hermes Agent

```bash
hermes mcp add skillos --command python --args "-m" --args "skillos.mcp_server"
hermes mcp test skillos
```

### 微信 / 飞书

通过 Hermes Gateway 接入。配置文档见 [deployment.md](deployment.md)。

## MCP Tools（12 个）

| Tool | 功能 |
|------|------|
| `extract_skill` | 7 步管线萃取 Skill（含 pipeline_log + 认识论摘要） |
| `export_for_skillopt` | 导出 best_skill.md + traces（SkillOpt 互补） |
| `confirm_pending_claims` | 晋升待审声明 Experience → Knowledge |
| `search_knowledge` | 搜索知识库 |
| `digest_document` | 深度消化文档（术语表+模式+速查表） |
| `list_skills` | 列出所有技能 |
| `get_skill` | 获取技能全文 |
| `query_lineage` | 追溯知识血缘 |
| `evolve_skill` | 触发技能进化（MoE 路由） |
| `get_epistemic_context` | 获取已验证知识上下文 |
| `ingest_file` | 文件摄入（PDF/Word/Excel/PPT/图片） |
| `fetch_url` | URL 抓取+消化（含微信公众号） |

## 项目结构

```
skillos/
├── api/          FastAPI 路由 (6 文件)
├── skills/       技能引擎（萃取/存储/执行/调度/管道）
├── knowledge/    知识引擎（认识论/图谱/血缘/深度消化）
├── evolution/    进化引擎（SkillOpt/SkillHone/MoE）
├── marketplace/  市场（注册/评分/支付/认证）
├── utils/        工具（文件摄入/微信抓取/文件监控）
├── ui/           桌面壳
├── mcp_server.py MCP 协议
└── hermes_bridge Hermes 互通层
```

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ --ignore=tests/test_feasibility_eval.py -v   # 全量单测
python scripts/run_bench_regression.py          # 本地回归（需 DEEPSEEK_API_KEY）
python -m skillos.api.server                  # 启动 API
open http://127.0.0.1:9876/docs               # OpenAPI 文档
```

### 本地 SkillsBench

| 命令 | 用途 |
|------|------|
| `python scripts/run_bench_regression.py` | 参考 + 泛化 Quick8 + 烟测 |
| `python scripts/archive/run_ablation.py` | HERITAGE×pack 2×2 ablation |
| `python scripts/archive/run_cold_start_generalize.py` | Path B 冷启动（`SKILLOS_FORCE_COLD_START=1`） |

详见 [`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) · 官方 CI 见 [`docs/SKILLSBENCH_CI.md`](docs/SKILLSBENCH_CI.md)

### AI 跨工具协作（必读）

所有 AI 编程工具在本仓库工作时须遵守 **[`AGENTS.md`](AGENTS.md)**：

1. **改代码前** — 读 [`docs/AI_DEV_LOG.md`](docs/AI_DEV_LOG.md) 最新一条  
2. **改代码后** — 按模板追加协作记录  

Cursor 自动加载 `.cursor/rules/`；Claude Code 读 `CLAUDE.md`。

**改进路线图**：[`docs/IMPROVEMENT_PLAN.md`](docs/IMPROVEMENT_PLAN.md) · **本地 Bench**：[`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) · **用户话术**：[`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) · **论文**：[`docs/paper/paper.tex`](docs/paper/paper.tex)
