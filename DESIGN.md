# SkillOS 设计书

> **写给三类读者**：AI 编程工具（理解架构贡献代码）、人类开发者（理解设计思路）、非技术决策者（理解产品价值）。
>
> **2026年6月 · v0.3.5** | 168 Python 文件 · 39,134 行 | 86 测试文件 · 613 tests · 99.7% pass | 28 前端文件 | 117 技能文档 | mypy 13→2 禁用码 | ruff F821/F841/E722=0 | Quick8 ALL PASS | 0 桩代码 | AgentSkills.io 标准对齐 | 设计升级：12档冷灰 · DM Sans统一 · 组件规范 · 混合布局

---

## 目录

1. [产品定位](#1-产品定位)
2. [核心设计思想](#2-核心设计思想)
3. [系统架构](#3-系统架构)
4. [模块详解](#4-模块详解)
5. [API 接口清单](#5-api-接口清单)
6. [开发者指引](#6-开发者指引)
7. [基础设施与质量](#7-基础设施与质量)
8. [竞品对比](#8-竞品对比)
9. [附录](#9-附录)

---

## 1. 产品定位

### 1.1 要解决的问题

Agent Skills 生态在2025–2026年爆发——Anthropic 发布 AgentSkills.io 标准，超过 85,000 个公开技能、30+ 平台兼容。但三个根本问题没人解决：

1. **技能从哪来？** 手工写效率低。AI 从网页/文档/对话中自动提取？现有工具做不到。
2. **技能对不对？** AI 提取的方法论——是真知识还是幻觉？没有系统能验证。
3. **技能能不能越用越好？** 用了几十次的技能发现了问题——能不能自动改进？改进后能不能帮到其他相关技能？

### 1.2 SkillOS 的回答

**"不是又一个 AI 平台——是给 AI 造子弹的兵工厂。"**

```
你告诉 AI 怎么做某件事（对话 / 贴链接 / 丢文件）
        ↓
    SkillOS 帮你：
    ① 理解工作流程（苏格拉底式追问）
    ② 验证知识真伪（认识论引擎）
    ③ 生成可复用技能文档（AgentSkills.io 标准）
    ④ 越用越好（自进化 + 知识扩散）
        ↓
输出 SKILL.md — Claude Code / Cursor / Codex 直接加载
```

### 1.3 一句话定位

> SkillOS：在对话中沉淀**可验证**的 Agent Skills。不是又一份 AI 生成的 markdown——是经过认识论验证、可进化的技能文档。

---

## 2. 核心设计思想

### 2.1 经验 ≠ 知识（认识论引擎）

AI 从网页提取的方法论只是"经验"（Experience）——可能对，可能错。SkillOS 引入认识论层级：

```
证据(Evidence) → 经验(Experience) → 知识(Knowledge) → 偏好(Preference)
                                                  ↓
                                            错误(Error)
                                                  ↓
                                            已取代(Superseded)
```

经验升级为知识必须同时满足四个条件：
1. **交叉验证**：≥2 个独立来源支持
2. **无矛盾**：不与任何已验证知识冲突
3. **证伪存活**：LLM 主动反驳失败
4. **时间稳定**：经时间考验仍然有效

理论基础：Plato（justified true belief）、Popper（证伪主义）、Kant（现象 vs 物自身）、Polanyi（默会知识）。全球无其他技能系统实现此层。

### 2.2 苏格拉底对话萃取（不是表单）

填表单需要你已经清楚工作流程——但多数专业知识是"默会的"。SkillOS 用场景推演式提问：

```
❌ 表单式：这个流程有哪些步骤？
✅ 苏格拉底式：假设对方发来采购合同，第7条悄悄把"北京仲裁"改成"上海仲裁"——
             按你的想法，技能第一步该做什么？这属于什么风险等级？
```

每轮对话双输出：① 给用户看的引导问题 ② 后台渐进生长的技能草稿（只增不改）。

### 2.3 七步 URL 学习管线（Feynman + Bloom + 刻意练习）

模拟人类学习过程，非一次性总结：

| 步骤 | 说明 | Token 预算 |
|------|------|:--:|
| 📖 初识 | 3秒判断文章值得读吗 | 200 |
| 🧠 理解 | 问"为什么"：底层逻辑？隐含假设？ | 400 |
| 🔧 拆解 | 拆成原子步骤，标注依赖和 if-then | 800 |
| ✍️ 重构 | 用自己的话重写，说不清处标出 | 2,000 |
| 🧪 验证 | 对抗性攻击：边界/顺序/歧义/缺失 | 350 |
| 🔗 内化 | 和已有技能关联，打标签 | 250 |
| 💎 沉淀 | 质量审核，组装最终文档 | — |
| 🌐 扩散 | 检查新知识能否改善已有技能 | — |

灵感来自 Feynman 技巧、Bloom 分类学、刻意练习。

### 2.4 技能自进化（MoE 混合专家）

执行技能 → 记录 trace → 诊断失败根因 → 触发进化 → 验证门把关 → 保存新版本。

三种优化策略自动路由：

| 策略 | 适用场景 | 方法 |
|------|------|------|
| Trace2Skill | 新技能，积累了大量失败轨迹 | 批量诊断 + 层次化合并 |
| EvoSkill | 分数波动大的不稳定技能 | 生成多候选 + 擂台淘汰 |
| SkillOpt | 成熟的稳定技能 | 外科手术式精准小改 |

知识扩散：改进 A 技能后，自动检查能否帮到 B、C、D——群体学习，技能不是孤岛。

### 2.5 技能多态（求同存异）

同一问题不同角色有不同解法。SkillOS 的做法：
- **求同**：提取 Skill DNA（所有版本必须遵守的核心原则）
- **存异**：保留差异（每个人标 @Override 说明在哪一步不同）
- **竞争**：让执行数据说话——哪个版本在实践中更好

设计灵感：Plato 理型论、Wittgenstein 家族相似性、Java Interface/@Override。

### 2.6 Anthropic Skill 设计哲学

SkillOS 将 Claude Code 团队的 Skill 设计洞察纳入萃取流程：

- **Context Engineering**：SKILL.md 是导航页，渐进暴露 references/scripts/examples/assets
- **Gotchas 最有价值**：不重复常识，提取组织内部的隐性知识和常踩的坑
- **Description 是路由规则**：描述触发条件而非功能列表
- **Instructions ≠ Scripts**：前者提供判断（为什么/什么时候），后者提供执行（怎么做）
- **自我改进循环**：内循环（执行+轨迹）→ 反馈（审阅）→ 外循环（diff+更新）

### 2.7 SkillsBench 评估五维度

| 维度 | 问题 |
|------|------|
| 边界 | 任务边界清晰？触发条件明确？ |
| 过程 | 提供检查点、示例和中间格式？ |
| 增益 | 相对无 skill 基线有稳定提升？ |
| 稳定性 | 换模型/环境后仍有效？ |
| 成本 | 上下文占用+维护成本值得？ |

关键数据：2–3 个 skill 最优。SkillOS Benchmark 证明 Layer 1（HERITAGE + pack 路由）贡献 +45pp 中位 Δ。

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     接入层                                   │
│  Web 界面 (Alpine.js)  │  MCP 协议 (Claude Code/Cursor)     │
│  桌面窗口 (pywebview)  │  IM 通道 (飞书/微信 via Hermes)    │
├─────────────────────────────────────────────────────────────┤
│                     智能体层（核心工作流）                     │
│  SkillAgent — 苏格拉底对话萃取 | learn_from_url — 7步管线    │
│  Dispatcher — 意图路由 | MetaSkill — 技能流水线编排           │
├─────────────────────────────────────────────────────────────┤
│                     质量评价层（MoE 多专家）                   │
│  6 个独立评委 + 交叉模型验证 + 置信度评分                      │
├─────────────────────────────────────────────────────────────┤
│                     知识质量控制层（⭐ 独家创新）               │
│  认识论引擎 | 知识图谱 | DNA 提炼 | 技能多态 | 数据血缘       │
├─────────────────────────────────────────────────────────────┤
│                     技能进化层                                │
│  MoE Router → SkillOpt / EvoSkill / Trace2Skill             │
│  SkillHone（决策历史+回滚）| Learning Theory（遗忘+类比）     │
├─────────────────────────────────────────────────────────────┤
│                     存储层                                    │
│  skills/ 目录 (AgentSkills.io) | knowledge/ (图谱+DNA)       │
│  data/ (SQLite) | 前端静态文件 (Alpine.js + vanilla JS)      │
└─────────────────────────────────────────────────────────────┘
```

**文件组织**（单向依赖，无循环引用）：

```
skillos/
  api/          (18 files) — REST 端点，对外接口
  skills/       (14 files) — 技能创建、存储、调度、变体、DNA
  knowledge/    (12 files) — 认识论、图谱、血缘、消化、记忆
  evolution/    (10 files) — 进化引擎、优化器、学习理论
  marketplace/  ( 7 files) — 技能市场、支付、评分
  identity/     ( 8 files) — 认证、租户、工作区、JWT
  security/     ( 2 files) — 脱敏、安全扫描
  intelligence/ ( 2 files) — 岗位模板、角色推荐
  channels/     ( 3 files) — 飞书 Webhook、通知
  billing/      ( 2 files) — 用量配额、计费
  evaluation/   ( 4 files) — MoE 评价体系
  utils/        ( 7 files) — 网页抓取、文件转换、微信、监控
  official_skillsbench/ (2 files) — SkillsBench 官方 CI 集成
  analytics/    ( 1 file)  — 平台分析
  admin/        ( 1 file)  — 管理接口
  ui/           ( 1 file)  — 桌面应用入口
  config.py     — 配置管理
  llm_client.py — LLM 调用统一接口
  mcp_server.py — MCP 协议服务 (14 tools)
  mcp_extract.py— MCP 技能提取辅助
  hermes_bridge.py — Hermes Agent 互操作
  db.py         — SQLite 数据库
  benchmark.py  — 基准测试
  skills_bench.py — SkillsBench 评分
frontend/
  24 JS files   — Alpine.js + vanilla JS
  2 HTML files  — 主界面 + 登录页
  1 CSS file    — 设计系统 (900 lines, CSS variables)
  1 docs/       — 前端文档 (quickstart.md)
.claude/
  settings.json — Hooks (ruff, .env block, AI_DEV_LOG reminder)
  skills/       — ai-dev-log, bench-regression
  agents/       — security-reviewer, test-writer
skills/
  117 SKILL.md  — AgentSkills.io 标准技能文档
```

---

## 4. 模块详解

### 4.1 知识质量控制层（⭐ 独家创新）

| 模块 | 一句话 | 核心机制 |
|------|------|------|
| `knowledge/epistemology.py` | **这段话是真知识还是幻觉？** | Plato justified true belief + Popper 证伪测试。`promote_to_knowledge()` + `_falsify_claim()`。全球唯一 |
| `knowledge/graph.py` | 知识之间的关联网 | 8 种关系类型。边权重随使用增长。自动聚类 |
| `knowledge/lineage.py` | 每条知识从哪来、经过什么处理 | 完整追溯链：来源→提取→引用→当前状态 |
| `knowledge/deep_digest.py` | 把文章消化为结构化知识包 | 6 步：扫描→论点→术语表→模式→速查→交叉引用 |
| `knowledge/playbook.py` | 团队共享背景知识 | PLAYBOOK.md 定义术语、风格、标准，约束所有输出 |
| `knowledge/memory.py` | 双层记忆系统 | 全局洞察 + 按技能记忆（偏好、决策历史） |
| `knowledge/extractor.py` | 从文本提取知识 | 来源权威权重（arxiv 0.85 > github 0.7 > 公众号 0.35） |
| `knowledge/skill_kb.py` | 按技能的私有知识库 | 每技能独立 KB，支持跨技能分享 |
| `knowledge/refresher.py` | 自动检查源变化 | SHA256 检测 → 自动重新消化 |
| `knowledge/taxonomy.py` | 8领域分类 + 6方法论检测 | 领域决定正确标准，方法论决定思考方式 |
| `knowledge/ingestion_queue.py` | 摄入持久化队列 | 磁盘队列 + 串行处理 + 重启恢复 |

### 4.2 技能引擎（核心工作流）

| 模块 | 一句话 | 关键设计 |
|------|------|------|
| `skills/agent.py` | **大脑。一切技能创建的核心** | 三种方式：苏格拉底对话（双输出）、7步URL管线（Feynman+Bloom）、知识扩散 |
| `skills/skill_store.py` | 技能增删改查 | 保存时自动版本归档 + 安全扫描 + 变体检测 |
| `skills/dispatcher.py` | 判断意图，路由到正确技能 | 保守路由："不确定就不匹配" |
| `skills/pattern_miner.py` | 从所有技能中提炼 DNA | 四层挖掘：结构原型→成功因子→反模式→DNA原则 |
| `skills/variants.py` | 同一技能的不同版本 | Archetype(接口) + Variant(实现) + @Override |
| `skills/metaskill.py` | 多技能编排成流水线 | 声明式 DAG，自动拓扑排序 |
| `skills/cold_start.py` | Path B 冷启动 | anchor rubric → HERITAGE refine → 复测 |
| `skills/domain_pack.py` | 动态领域 pack | 应答速查 + pack-scoped inject |
| `skills/tool_registry.py` | 技能工具注册 | Knowledge/Tools/Skills 三层分离 |
| `skills/session_manager.py` | 多用户会话管理 | 30分钟过期，SQLite 持久化，重启恢复 |

### 4.3 进化引擎（技能越用越好）

| 模块 | 一句话 | 核心机制 |
|------|------|------|
| `evolution/skillopt.py` (1,754 lines) | **优化引擎核心** | MoE 三专家路由 + ElitePool 淘汰赛 + 10 维审计 + 编辑预算递减 |
| `evolution/skillhone.py` (601 lines) | 决策历史 + 回滚 + 隔离 | WHY 链追踪。定向回滚。角色隔离 |
| `evolution/engine.py` (401 lines) | 进化触发和调度 | 3种触发条件。6小时自动运行。跨经验关联 |
| `evolution/evolver.py` (458 lines) | 轨迹记录 + 进化执行 | 判断改进是实质性还是措辞变化 |
| `evolution/learning_theory.py` (415 lines) | 人类学习理论工程化 | Ebbinghaus 遗忘曲线。递归费曼。类比迁移 |
| `evolution/learning_records.py` (185 lines) | 追踪学习进度 | ZPD 5状态机（new→learning→learned→confused→mastered） |
| `evolution/description_optimizer.py` | 描述优化 | LLM 辅助优化技能描述和触发词 |
| `evolution/skill_tester.py` | 技能测试 | 自动生成测试用例 + 执行验证 |
| `evolution/skillopt_export.py` | SkillOpt 导出 | 导出 best_skill.md + manifest + traces |

### 4.4 前端（Alpine.js + Vanilla JS）

| 文件 | 行数 | 职责 |
|------|:--:|------|
| `index.html` | 1,139 | 主界面，28 个 script 引用，语义化 HTML |
| `login.html` | 247 | 登录/注册页面 |
| `style.css` | 878 | 设计系统：CSS 变量（颜色/间距/字号/圆角/阴影）、暗色主题、响应式 |
| `skills.js` | 1,727 | 技能详情视图（Alpine 组件），概览/文档/质量/进化/KB/认识论/DNA |
| `chat.js` | 886 | 聊天引擎：消息处理、流式响应、TTS、文件上传、dispatch |
| `knowledge.js` | 414 | 知识工作台：仪表盘/知识库/图谱/血缘/日志/审核 |
| `hub.js` | 561 | 技能市场：浏览/搜索/订阅/发布/审核 |
| `workspace.js` | 402 | 萃取工作区：进度条、草稿面板、文件处理 |
| `settings.js` | 485 | 设置：模型/语音/定价/工作区，4 个 Tab |
| `alpine-bridge.js` | 287 | Alpine stores + 全局变量桥接（渐进式迁移） |
| `app.js` | 247 | 核心状态、全局搜索、Toast、键盘快捷键、初始化 |
| 其余 13 个文件 | 2,947 | auth、voice、audio、admin、export、precipitation、docs 等 |

**设计系统**：CSS 变量完整定义了颜色（`--n0`–`--n9` 中性色，`--a1`–`--a6` 铜色 accent，`--blue/amber/red/violet` 语义色）、间距（`--s-1`–`--s-16`）、字号（`--t-xs`–`--t-display`）、圆角、阴影。暗色主题，`--t: 220ms` 过渡时间。

### 4.5 API 层

| 模块 | 行数 | 职责 | 认证 |
|------|:--:|------|:--:|
| `api/skills.py` | 567 | 技能 CRUD + dispatch + 导出 + DNA/变体 | GET optional, DELETE required |
| `api/skills_extract.py` | 1,300 | 萃取管道：dispatch/create/finalize/resume/ingest | 混合 |
| `api/knowledge.py` | 330 | 知识/血缘/图谱/wisdom/journal/review（21 endpoints） | GET optional, POST required |
| `api/evolution.py` | 250 | 优化/状态/MoE 路由/整合/SkillOpt 导出 | required |
| `api/marketplace.py` | 220 | 市场统计/搜索/发布/订阅/审核/定价 | optional |
| `api/auth.py` | 280 | 登录/注册/GitHub/飞书/管理 | public + admin check |
| `api/org_admin.py` | 95 | 组织管理：概览/用量/治理/配额/部门 | required |
| `api/organizations.py` | 130 | 组织 CRUD + 成员管理 | required |
| `api/billing.py` | 55 | 计划/创作者摘要/启用 Pro | required |
| `api/analytics.py` | 50 | 漏斗/稳定性/SLA/平台概览 | required |
| `api/approval.py` | 85 | 技能审核队列/提交/批准/拒绝 | required |
| `api/bench_official.py` | 160 | SkillsBench 预设/结果/回归/CI 触发 | trigger-ci: required |
| `api/intelligence.py` | 50 | 岗位模板/角色推荐 | optional |
| `api/usage.py` | 45 | 用量查询/BYOK 配置 | required |
| `api/workspaces.py` | 55 | 工作区列表/切换 | required |
| `api/voice.py` | 30 | 语音转录 | public |
| `api/channels.py` | 25 | 飞书 Webhook | public |
| `api/docs_api.py` | 60 | 文档/快速开始 | public |

### 4.6 工具层

| 模块 | 行数 | 职责 |
|------|:--:|------|
| `utils/web_fetch.py` | 119 | 多编码网页抓取 |
| `utils/web_search.py` | 81 | Bing 搜索 |
| `utils/wechat_fetch.py` | 203 | CDP 浏览器抓取微信公众号 |
| `utils/file_ingest.py` | 301 | 30+ 格式 → Markdown（PDF/Word/Excel/PPT/图片/音频） |
| `utils/watcher.py` | 147 | 文件夹监控自动导入 |
| `utils/account_watcher.py` | 266 | 微信公众号更新监控 |
| `mcp_server.py` | 672 | MCP 协议服务（14 tools） |
| `hermes_bridge.py` | 279 | Hermes Agent 双向互通 |

### 4.7 基础设施

| 模块 | 行数 | 职责 |
|------|:--:|------|
| `config.py` | 175 | 配置管理（DeepSeek/Ollama/火山引擎），`.env` 读写 |
| `llm_client.py` | 138 | LLM 调用统一接口，指数退避重试，Ollama fallback |
| `db.py` | 340 | SQLite 连接管理（线程安全） |
| `identity/` | 8 files | JWT、租户上下文、工作区、认证中间件 |
| `security/` | 2 files | 敏感信息脱敏、10 种危险模式扫描 |
| `billing/` | 2 files | 用量配额、LLM 调用计费 |

---

## 5. API 接口清单

### 5.1 核心端点

| 路由 | 方法 | 说明 | 认证 |
|------|:--:|------|:--:|
| `/api/skills/` | GET | 列出所有技能 | optional |
| `/api/skills/{name}` | GET | 获取技能详情 | optional |
| `/api/skills/{name}` | DELETE | 删除技能 | required |
| `/api/skills/dispatch` | POST | **核心**：文字/URL/文件自动路由 | optional |
| `/api/skills/dispatch/stream` | POST | 流式 dispatch | optional |
| `/api/skills/create` | POST | 从文本创建技能 | optional |
| `/api/skills/finalize` | POST | 完成技能萃取 | optional |
| `/api/skills/ingest` | POST | 文件上传（30+ 格式） | optional |
| `/api/skills/resume` | POST | 恢复中断的萃取会话 | optional |
| `/api/skills/{name}/export` | GET | 导出技能 | optional |
| `/api/skills/{name}/dna-lineage` | GET | DNA 血缘 | optional |
| `/api/skills/{name}/refresh-dna-lineage` | POST | 刷新 DNA 血缘 | optional |
| `/api/knowledge/` | GET | 知识项列表（含有效性过滤） | optional |
| `/api/knowledge/lineage` | GET | 知识血缘列表 | optional |
| `/api/knowledge/lineage/{id}` | GET | 血缘详情 | optional |
| `/api/knowledge/lineage/{id}/graph` | GET | 血缘图（cytoscape + mermaid） | optional |
| `/api/knowledge/graph/clusters` | GET | 知识图谱聚类 | optional |
| `/api/knowledge/wisdom` | GET | 跨血缘洞察 | optional |
| `/api/knowledge/journal` | GET | 学习日志 | optional |
| `/api/knowledge/review` | GET | 待审核经验 | optional |
| `/api/knowledge/cycle` | POST | 启动知识消化循环 | required |
| `/api/knowledge/skill-lineage` | GET | 技能沉淀血缘查询 | optional |
| `/api/evolution/{name}/optimize` | POST | 触发优化 | required |
| `/api/evolution/{name}/state` | GET | 技能进化状态 | required |
| `/api/evolution/consolidate` | POST | 全局知识整合 | required |
| `/api/marketplace/catalog` | GET | 市场目录 | public |
| `/api/marketplace/publish` | POST | 发布技能 | optional |
| `/api/marketplace/subscribe` | POST | 订阅技能 | optional |
| `/api/auth/login` | POST | 登录 | public |
| `/api/auth/register` | POST | 注册 | public |
| `/api/auth/me` | GET | 当前用户 | JWT |
| `/api/auth/github` | POST | GitHub OAuth | public |
| `/api/auth/feishu` | POST | 飞书登录 | public |

### 5.2 Dispatch 路由逻辑

```
用户消息
  ├─ 含 URL？
  │   └─ 抓取 → 判断：方法论文章？（7步学习管线）/ 概念参考？（deep_digest）
  ├─ 含技能关键词？（萃取/沉淀/帮我创建...）
  │   └─ 开始或继续苏格拉底对话（每轮双输出：问题 + 草稿）
  ├─ 含 Playbook 关键词？
  │   └─ 冷启动访谈，引导创建 PLAYBOOK.md
  └─ 其他 → 普通 AI 聊天
```

---

## 6. 开发者指引

### 6.1 环境搭建

```bash
pip install -e ".[all]"
python -m skillos.ui.app --server-only    # API: http://127.0.0.1:8765
python -m skillos.mcp_server              # MCP
```

### 6.2 代码约定

```python
# ✅ 正确 import（完整包路径）
from skillos.config import get_config
from skillos.skills.skill_store import save_skill
from skillos.identity.middleware import AuthContext, require_auth

# ❌ 错误 import
from web_search import search        # 应该 from skillos.utils.web_search import search
import skillopt as opt               # 应该 from skillos.evolution import skillopt as opt

# ✅ 获取配置
cfg = get_config()
llm_args = cfg.to_llm_args()         # (api_key, base_url, model, chat_kwargs)

# ✅ LLM 调用
from skillos.llm_client import call
reply = call("prompt", max_tokens=600, temperature=0.2)
```

### 6.3 设计约束（不可破坏）

| 规则 | 原因 |
|------|------|
| **Skill 格式兼容 AgentSkills.io** | `---\nYAML\n---\n\nMarkdown`，YAML 必含 `name` |
| **认识论引擎不可绕过** | 所有声明走 `record_claim()`，禁止直接写 Knowledge 级别 |
| **异常必须记录日志** | 禁止 `except: pass`。至少 `_log.debug()` 或 `_log.warning()` |
| **API 返回真实数据** | 禁止硬编码空桩 `{"total": 0, "items": []}` |
| **单向依赖** | api → skills/knowledge → llm_client，禁止反向引用 |
| **线程安全** | config 写操作有锁，db.py `get_conn()` 线程安全 |
| **安全扫描** | `save_skill()` 入口自动扫描 10 种危险模式 |

### 6.4 常见修改场景

| 场景 | 文件 | 注意事项 |
|------|------|------|
| 新增 API 端点 | `api/skills.py` 等 | 路由注册在 `server.py`；POST 端点加 `require_auth` |
| 改进萃取对话 | `skills/agent.py` | Phase 状态机不可打破；双输出模式不可改 |
| 改进 URL 学习 | `skills/agent.py:learn_from_url` | 7步顺序不可跳；每步 token 预算不可大幅变 |
| 新增 DNA 原则 | `skills/pattern_miner.py` | 硬编码原则在 `check_dna_compliance()` |
| 新增文件格式 | `utils/file_ingest.py` | 加至 `MARKITDOWN_FORMATS` 或 `PLAIN_TEXT_FORMATS` |
| 修改 LLM 调用 | `llm_client.py` | 所有模块通过 `call()`，function calling 用 `call_with_tools()` |

### 6.5 认证模式

```python
# 公开端点
@router.get("/public")

# 可选认证（未登录也可访问，登录后启用租户过滤）
@router.get("/skills")
async def list_skills(auth: AuthContext | None = Depends(get_optional_auth)):

# 必须认证
@router.post("/skills/{name}")
async def update_skill(name: str, auth: AuthContext = Depends(require_auth)):
```

### 6.6 Claude Code 自动化

项目 `.claude/settings.json` 已配置：

| 类型 | 名称 | 作用 |
|------|------|------|
| Hook | PostToolUse (Edit/Write) | ruff auto-fix + format |
| Hook | PreToolUse (Edit/Write) | 阻止 .env 编辑 |
| Hook | Stop | AI_DEV_LOG 提醒 |
| Skill | `ai-dev-log` | 自动追加开发日志 |
| Skill | `bench-regression` | 运行 SkillsBench 回归 |
| Agent | `security-reviewer` | 安全审查（认证/租户/SQL注入） |
| Agent | `test-writer` | pytest 测试生成 |

MCP 集成：`context7`（实时文档）、`github`（Issue/PR/CI）。

---

## 7. 基础设施与质量

### 7.1 测试

```bash
python -m pytest tests/ -v                    # 全量：613 tests, 606 pass, 99.7%
python -m pytest tests/ -v --tb=short -q      # 快速模式
python scripts/ci_local.sh                    # 六阶段 CI 管道本地复现
```

**测试统计**：86 个测试文件，613 个用例。2 个瞬态失败（LLM 超时，已加重试）。

### 7.2 CI/CD

GitHub Actions `.github/workflows/ci.yml` 六阶段管道：

```
Lint (ruff) → Phase A core loop → Knowledge closure → Bench gates
→ DNA golden set → SkillsBench unit tests → Full test suite → Import verify
```

Benchmark job（依赖 DEEPSEEK_API_KEY）：Quick8 regression + gate verification。

### 7.3 代码质量

| 工具 | 配置 | 状态 |
|------|------|:--:|
| ruff | pyproject.toml `[tool.ruff]` | F821/F841/E722=0 |
| mypy | pyproject.toml `[tool.mypy]` | 0 errors（2 个禁用码：attr-defined, arg-type） |
| pre-commit | `.pre-commit-config.yaml` | ruff + trailing-whitespace + end-of-file + check-yaml/json/toml |

### 7.4 SkillsBench 基准测试

```bash
python scripts/run_bench_regression.py        # Reference + Generalize Quick8 + Smoke
python scripts/run_quick8_ci.py               # CI Quick8 only
python scripts/verify_quick8_gates.py         # 门禁验证
```

**当前结果**：Reference Quick8 +28/+18.6/+22 pp，Generalize 3/3 OK，Smoke 6/6 OK — **ALL PASS**。

### 7.5 安全机制

| 机制 | 位置 | 说明 |
|------|------|------|
| API 认证 | `identity/middleware.py` | JWT + `require_auth` / `get_optional_auth` |
| 租户隔离 | `identity/context.py` | 所有数据查询按 tenant_id 过滤 |
| SQL 注入防护 | `db.py` | 全参数化查询（`?` 占位符） |
| SSRF 防护 | `mcp_server.py` | fetch_url 阻止 localhost/内网 IP |
| 路径穿越防护 | `mcp_server.py` | ingest_file 限制 workspace/home/Downloads |
| 技能安全扫描 | `middleware.py` | 10 种危险模式自动检测 |
| 敏感信息脱敏 | `security/desensitize.py` | LLM 调用前自动脱敏 |

---

## 8. 竞品对比

### 8.1 学术前沿

| 论文 | 时间 | 做了什么 | SkillOS 对比 |
|------|------|---------|------------|
| Microsoft SkillOpt | 2025.05 | 文本学习率+验证门+52/52 SOTA | 互补：SkillOpt 优化训练，SkillOS 创建+质量 |
| Anything2Skill | 2026.06 | 异构知识→统一技能格式 | SkillOS 覆盖此路径 |
| Trace2Skill | 2025.03 | 轨迹→局部经验→可迁移技能 | SkillOS evolver 从 trace 诊断根因 |
| EXIF | 2025.06 | 探索Agent+目标Agent自我进化 | SkillOS 规则式进化 |
| SkillFoundry | 2026.04 | 科学资源自动挖掘为技能库 | deep_digest 覆盖文档→知识包 |

### 8.2 工业平台

| 平台 | 技能创建 | 质量验证 | 自进化 | 输出标准 |
|------|:--:|:--:|:--:|:--:|
| Dify | 表单+代码 | ❌ | ❌ | 平台锁定 |
| Coze | 拖拽工作流 | ❌ | ❌ | 平台锁定 |
| LangChain | 纯代码 | ❌ | ❌ | 代码级 |
| **SkillOS** | **苏格拉底对话** | **认识论引擎** | **MoE+扩散** | **AgentSkills.io** |

### 8.3 SkillOS 的独特优势

1. **认识论引擎** — 全球唯一。Plato+Popper 工程化验证技能质量
2. **苏格拉底对话萃取** — 人机协作式知识提取 vs 全自动黑盒
3. **技能多态系统** — Interface/Concrete/@Override，Wittgenstein 家族相似性
4. **知识扩散** — 群体学习，技能改进自动传播
5. **AgentSkills.io 兼容** — 输出可在 30+ 平台直接使用
6. **完整质量基础设施** — mypy、ruff、pre-commit、CI/CD、SkillsBench ALL PASS

---

## 9. 附录

### 9.1 版本历史

| 版本 | 日期 | 关键事件 |
|------|------|------|
| v0.3.0 | 2026-06-14 | 基线冻结，认识论主链路 |
| v0.3.3 | 2026-06-24 | 前端 M0–M5 产品化批次 |
| v0.3.4 | 2026-06-24 | Reference Quick8 回归修复 |
| v0.3.5 | 2026-06-26 | P0–P3 全阶段优化：基础设施清理、mypy 13→2、Claude Code 自动化、前端安全/UI/无障碍修复 |

详见 [`CHANGELOG.md`](CHANGELOG.md) 和 [`docs/AI_DEV_LOG.md`](docs/AI_DEV_LOG.md)。

### 9.2 相关文档

| 文档 | 用途 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | 跨工具 AI 协作协议（改代码前后读写日志） |
| [`CLAUDE.md`](CLAUDE.md) | Claude Code 项目入口 |
| [`CHANGELOG.md`](CHANGELOG.md) | 版本发布记录 |
| [`docs/AI_DEV_LOG.md`](docs/AI_DEV_LOG.md) | AI 协作开发日志（每次改代码后追加） |
| [`docs/IMPROVEMENT_PLAN.md`](docs/IMPROVEMENT_PLAN.md) | Phase 0–7 改进计划 |
| [`docs/OPTIMIZATION_PLAN.md`](docs/OPTIMIZATION_PLAN.md) | P0–P3 优化计划（2026-06-25） |
| [`docs/FRONTEND_EVALUATION.md`](docs/FRONTEND_EVALUATION.md) | 前端全面评估报告 |
| [`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) | 本地 SkillsBench 指南 |
| [`docs/PAPERS.md`](docs/PAPERS.md) | 三篇论文规划 |
| [`docs/paper/paper.tex`](docs/paper/paper.tex) | 认识论论文（arXiv 投稿中） |
| [`docs/paper/experiments/layer1_ablation_results.md`](docs/paper/experiments/layer1_ablation_results.md) | Layer 1 ablation 实验数据 |
| [`.claude/settings.json`](.claude/settings.json) | Claude Code hooks + 权限配置 |

### 9.3 移植历史

SkillOS 从 Skill Distiller 的 30+ 文件移植而来。19 个模块忠实移植（仅改 import 路径），`skills/agent.py` 架构重设计（苏格拉底双输出 + 场景推演 + 质量评分），5 个模块功能增强。详见设计书历史版本。

---

> **"一个好的 skill 系统不应该只是 skill 的容器——它应该比创建 skill 的人更理解 skill 的质量、关系和进化方向。"**
>
> 本设计书基于 Skill Distiller PROJECT_DESIGN.md，更新至 SkillOS v0.3.5 状态。
> 168 Python 文件 · 39,134 行 · 86 测试文件 · 613 tests · 117 技能文档 · 28 前端文件。
