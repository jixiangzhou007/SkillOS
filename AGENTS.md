# SkillOS — AI Agent 协作说明

> **所有 AI 编程工具（Cursor、Claude Code、Codex、Copilot 等）在本仓库中工作前必须阅读并遵守本节。**

## 项目是什么

SkillOS 是 Agent Skills 的「技能 IDE」：在对话（飞书 / 微信 / Cursor 等）中沉淀经验，输出 AgentSkills.io 标准的 `SKILL.md`。架构见 [`DESIGN.md`](DESIGN.md)。

## 强制协作协议（不可跳过）

### 1. 动手前 — 读日志

每次会话**第一次改代码前**，必须阅读：

```
docs/AI_DEV_LOG.md
```

重点看：**最新一条**记录的「开放问题 / 下一步」和「未修改 / 刻意不做」，避免重复劳动或推翻已有决策。

### 2. 动手后 — 写日志

每次**完成一轮代码修改**（哪怕只改一个文件），必须在 `docs/AI_DEV_LOG.md` 的「新会话记录区」**顶部**追加一条，使用文件内「记录模板」，至少包含：

| 字段 | 必填 |
|------|:----:|
| 背景 / 触发 | ✓ |
| 修改思路 | ✓ |
| 修改内容（文件表） | ✓ |
| 未修改 / 刻意不做 | ✓ |
| 验证（命令 + 结果，未跑须说明） | ✓ |
| 开放问题 / 下一步 | ✓ |

**禁止**：只改代码不写日志；把变更只写在聊天里而不落盘。

### 3. 架构约束

修改代码时遵守 [`DESIGN.md` §6`](DESIGN.md#6-给-ai-编程工具的指引)：

- Skill 输出兼容 **AgentSkills.io**（`---\nYAML\n---\nMarkdown`）
- 认识论层：不绕过 `epistemology` 直接当「已验证知识」入库（接入主链路时尤其注意）
- API 返回真实数据，不写硬编码空桩
- import 使用 `skillos.*` 包路径
- 异常至少 `_log.debug` / `_log.warning`，禁止裸 `except: pass`

### 4. 版本发布 vs 协作日志

| 文件 | 何时更新 |
|------|----------|
| `docs/AI_DEV_LOG.md` | **每次 AI 改代码后**（协作过程） |
| `CHANGELOG.md` | 用户明确要求发版 / 打 tag 时 |

## 常用命令

```bash
pip install -e .
python -m pytest tests/ --ignore=tests/test_feasibility_eval.py -v
skillos --server-only          # API http://127.0.0.1:9876
python -m skillos.mcp_server   # MCP
```

### 本地 SkillsBench（需 `DEEPSEEK_API_KEY`）

```bash
python scripts/run_bench_regression.py              # 参考 + 泛化 Quick8 + 烟测
python scripts/archive/run_ablation.py              # Layer 1 HERITAGE×pack 2×2
python scripts/archive/run_cold_start_generalize.py # Path B 冷启动（SKILLOS_FORCE_COLD_START=1）
```

详见 [`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) · 官方 CI：[`docs/SKILLSBENCH_CI.md`](docs/SKILLSBENCH_CI.md)

## 工具专属入口（内容一致，任选其一即可）

| 工具 | 会读取的文件 |
|------|----------------|
| Cursor | `.cursor/rules/*.mdc` + 本文件 |
| Claude Code | `CLAUDE.md` → 本文件 |
| 其他 Agent | 本文件 `AGENTS.md` |

若规则冲突，**以本文件 + `docs/AI_DEV_LOG.md` 最新记录为准**。

执行功能改进前，阅读分阶段路线图 [`docs/IMPROVEMENT_PLAN.md`](docs/IMPROVEMENT_PLAN.md)；Phase 0–7 已交付，后续以 bench 回归与产品化为主。
