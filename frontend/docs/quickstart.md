# 快速开始

## 1. 注册

打开 `/login.html` 注册账号，自动获得个人工作区。

## 2. 创建第一个技能

在对话区描述工作流程，例如：

> 帮我创建一个处理客户投诉的技能

多轮对话后点「生成技能」。保存走 Dual Gate：Gate A 认识论 ∧ Gate B 烟测 → Trust Tier（Draft / 学徒 / Verified）。

## 3. 看 Trust Tier 与可调用目录

侧栏筛选：**全部 / Verified / 学徒 / Draft / 可调用**。

- **Draft**：可编辑，默认**不**进模型 catalog（`model_invocable=false`）
- **学徒（Provisional）**：可试用安装
- **Verified**：出师，优先导出

列表徽章含来源层：系统 / 工作区 / 市场安装。Skill ≠ Plugin。

## 4. 认识论确认

打开技能详情 → **认识论** Tab → 确认待审声明；Overview 可看 Evidence。

## 5. 装进 Harness（Cursor / agents / dsh）

详情「输出与安装」或导出 Zip（含 `INSTALL.txt` / `TRUST.txt`）：

| 目标 | 路径 |
|------|------|
| Cursor | `~/.cursor/skills/<slug>/` |
| 项目 Agents | `.agents/skills/<slug>/` |
| DeepSeek Harness | `~/.dsh/skills/<slug>/` |

**UI 一键安装**：技能详情「输出与安装」→「装到 Cursor / dsh / .agents」（`POST /api/skills/{name}/install-local`）。

或 CLI：

```bash
python scripts/install_skill_to_harness.py "技能名" --target cursor
python scripts/install_skill_to_harness.py "技能名" --target dsh
```

设置 → **Harness** 可复制命令 / 打开 model catalog。试用：`npx @deepseek-ai/dsh web`

渐进披露 API：`GET /api/skills/catalog?model_only=true`（仅 name+description，无正文）。

## 6. 市场安装（本地）

Hub 空目录会自动 seed cohort。详情「安装到工作区」会**直接落库**（不重跑 LLM），来源标为市场安装。

## 7. MCP（Cursor）

设置 `SKILLOS_MCP_TOKEN` 后连接 SkillOS MCP。`list_skills` 默认只列模型可调用技能；正文用 `get_skill`。

## 限额

| 项目 | 个人免费版 |
|------|---------------|
| 技能数 | 10 |
| LLM/月 | 50 |
| BYOK | 设置 → 用量 → 自带 API Key |

完整文档见 [用户指南](/api/docs/guide)。Alpha 预期与限制见仓库 `docs/KNOWN_ISSUES.md`；黄金路径见 `docs/DEMO_VERIFIED_SPINE.md`。
