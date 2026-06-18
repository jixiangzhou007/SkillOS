# SkillOS 设计书

> 写给三类读者：**AI 编程工具**（理解架构来贡献代码）、**人类开发者**（理解设计思路）、**不懂代码的创新者**（理解自己的产品）。
>
> 2026年6月 | 500+测试 | 0桩代码 | MoE评价 | 3层DNA(哲学→学科→技能) | 10 domain pack | SkillsBench 88任务 | 本地 bench 闭环 | 35轮长对话验证

---

## 目录

1. [这个产品解决什么问题](#1-这个产品解决什么问题)
2. [核心设计思路（为什么这么做）](#2-核心设计思路)
3. [系统架构（一图看懂全貌）](#3-系统架构)
4. [每个模块是干什么的](#4-每个模块是干什么的)
5. [API 接口清单](#5-api-接口清单)
6. [给 AI 编程工具的指引](#6-给-ai-编程工具的指引)
7. [从 Skill Distiller 到 SkillOS 的移植记录](#7-移植记录)
8. [竞品对比与定位](#8-竞品对比与定位)

---

## 1. 这个产品解决什么问题

### 背景：Agent Skills 生态爆发

2025年底，Anthropic 发布了 AgentSkills.io 开放标准——用 Markdown 文件来定义 AI 助手的能力。到2026年中，已经有超过 85,000 个公开技能、30+ 个平台兼容、Linux Foundation 在讨论把它纳为正式标准。

这创造了一个新的软件供应链：**技能文档就是 AI 的"可执行代码"**。

### 问题：技能从哪来？技能对不对？技能能不能越用越好？

市面上的 Dify、Coze、LangChain 都在解决"怎么执行技能"。但三个更根本的问题没人管：

1. **技能从哪来？** 目前只能手工写。让 AI 从网页、文档、对话中自动学？做不到。
2. **技能对不对？** AI 从一篇博客提取的方法论——它是真知识还是幻觉？没人验证。
3. **技能能不能越用越好？** 一个技能用了几十次，发现了问题——能不能自动改进？改进后能不能帮到其他相关技能？

### SkillOS 的回答

**"不是又一个 AI 平台——是给 AI 造子弹的兵工厂。"**

```
你告诉 AI 怎么做某件事（对话/贴链接/丢文件）
        ↓
    SkillOS 帮你：
    ① 理解你的工作流程（苏格拉底式追问）
    ② 验证提取的知识是否正确（认识论引擎）
    ③ 生成可复用的技能文档（AgentSkills.io 标准）
    ④ 越用越好，知识在技能之间传播（自进化+扩散）
        ↓
输出一个 .md 文件，Claude Code / Cursor / Codex 直接加载使用
```

---

## 2. 核心设计思路

### 2.1 为什么 AI 提取的知识不能直接用？

这是整个产品最根本的设计洞察。

AI 从网页提取一段方法论，它其实只是"经验"（Experience）——可能对，可能错。就像你听朋友说"代码审查要先看测试再看逻辑"——这个建议在特定场景下可能有用，但它不是"已验证的知识"。

SkillOS 引入了：**经验 ≠ 知识**。

```
证据(Evidence) → 经验(Experience) → 知识(Knowledge) → 偏好(Preference)
                                                  ↓
                                            错误(Error) — 被推翻的也要保留
                                                  ↓
                                            已取代(Superseded) — 曾是真知识但被新发现替代
```

经验要升级为知识，必须同时满足四个条件：

1. **交叉验证**：至少 2 个独立来源都这么说
2. **无矛盾**：没有任何已验证的知识和它冲突
3. **证伪存活**：我们主动让 AI 去反驳它，它活下来了
4. **时间稳定**：过了一段时间还是对的

这套设计来自四位哲学家：
- **Plato**：真信念需要 justification（justified true belief）
- **Popper**：通过证伪而不是证实来接近真理
- **Kant**：我们看到的（现象）不等于真实的（物自身）
- **Polanyi**：人类知道的多于能说出来的（默会知识）

代码实现了 Platon + Popper：`promote_to_knowledge()`（晋升）+ `_falsify_claim()`（证伪测试）。全球没有任何其他技能系统有这一层。

### 2.2 为什么用对话而不是表单？

填表单很无聊。而且最重要的是，填表单的前提是你已经很清楚你的工作流程是什么。但实际上，很多人的专业知识是"默会的"——你知道怎么做但说不清楚。

苏格拉底的方法是用提问帮助你发现自己已经知道但没清楚表达的知识。

SkillOS 的对话不是模板式的"请填写步骤1、步骤2"。它更像一个有经验的同事：

```
❌ 表单式：这个流程有哪些步骤？
✅ 苏格拉底式：假设对方发来采购合同，第7条悄悄把"北京仲裁"改成"上海仲裁"——
             按你的想法，技能第一步该做什么？这属于什么风险等级？
             [选项] 高风险，必须修改
             [选项] 中风险，建议修改
             [选项] 低风险，仅标注
```

每轮对话 AI 做两件事（**双输出模式**）：
1. 问一个场景推演式的问题（给用户看）
2. 在后台逐步完善技能草稿（用户看不到，但草稿在生长）

草稿规则是**只增不改**——已有的正确内容不动，新信息往上加，不确定的标 `[待补充]`。

### 2.3 为什么 URL 学习要分 7 步？

一次 LLM 调用可以直接"总结这篇文章并生成技能文档"。但这样做的问题是你没有真正"理解"——你只是在复制。人类学习新知识不是这样的。

SkillOS 模拟了人类的学习过程，分 7 步：

```
📖 初识 — 花 3 秒判断：这文章值得读吗？（200 tokens，快速淘汰垃圾）
🧠 理解 — 不列步骤，问"为什么"：底层逻辑？隐含假设？作者思维模式？（400 tokens）
🔧 拆解 — 拆成原子步骤：每步必须是单一动作，标注依赖和 if-then（800 tokens）
✍️ 重构 — 用自己的话重写，按执行者最容易理解的顺序，说不清的地方标出来（2000 tokens）
🧪 验证 — 对抗性攻击：边界/顺序/歧义/缺失，发现问题自动修复（350 tokens）
🔗 内化 — 和已有技能建立关联，打标签未来好搜索（250 tokens）
💎 沉淀 — 附上质量审核，组装成最终技能文档
🌐 扩散 — 检查新学到的能不能改善已有技能（最多检查 5 个）
```

每一步的 token 预算都不一样——初识只给 200 token 做快速判断，重构给 2000 token 做深度重写。这和 Bloom 的教育目标分类学（记忆→理解→应用→分析→评价→创造）一致。

灵感：Feynman 技巧（说不清楚的地方就是理解不够）+ Bloom 分类学 + 刻意练习（验证→反馈→调整→重复）。

### 2.4 为什么技能需要进化？

软件代码越改越好，技能为什么不能？

SkillOS 记录每一次执行的结果（trace）。当某个技能连续失败 3 次，系统自动运行进化：

```
执行技能 → 记录trace → 诊断失败根因 → 触发进化 → LLM 生成改进版 → 验证门把关 → 保存新版本
```

三种优化策略（**MoE 混合专家**）：
- **Trace2Skill**：新技能、积累了大量失败轨迹 → 批量诊断
- **EvoSkill**：分数波动大的不稳定技能 → 生成多个候选，擂台淘汰
- **SkillOpt**：成熟的稳定技能 → 外科手术式精准小改

系统自动选择用哪种策略（7 条路由规则基于：执行次数、分数方差、成熟天数、遗忘状态）。

还有一个独特的设计：**知识扩散**。当你改进了"客户退款处理"技能，系统会自动检查"这个改进能不能帮到'订单查询'或'支付对账'"。如果发现关联，自动应用改进。这就是"群体学习"——技能不是孤岛。

### 2.5 为什么允许同一个技能有不同版本？

现实中，同一个问题不同角色有不同的解法。比如"客服回复"：

- **客服主管**：关键词匹配 → 语义理解，回复风格：正式
- **NLP 工程师**：关键词匹配 → 意图识别 + 实体提取，回复风格：技术性
- **一线客服**：关键词匹配 → 先看最近 3 条聊天记录，回复风格：口语化

传统做法是统一成一套——但谁说了算？SkillOS 的做法是**求同存异**：

- **求同**：提取共性（Skill DNA——所有版本都必须遵循的核心原则）
- **存异**：保留差异（每个人标上 @Override 说明自己在哪一步和标准不同）

哪个版本更好？让执行数据说话。这和 Popper 的证伪主义一致：不是找"最正确的"，而是让不同版本在竞争中自然淘汰。

设计灵感：
- Plato 的理型论（Archetype 是理想 Form，Variant 是具体实现）
- Wittgenstein 的家族相似性（技能之间不需要共享一个本质）
- Java 的 Interface/Concrete/@Override 工程化

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户怎么用                                │
│                                                             │
│   Web 界面 (pywebview 桌面窗口)                               │
│   输入框 — 打字 / 贴 URL / 拖文件                             │
│   MCP 协议 — Claude Code / Cursor / Codex 直接调用            │
├─────────────────────────────────────────────────────────────┤
│                     大脑（智能体层）                           │
│                                                             │
│   SkillAgent         — 苏格拉底式对话萃取技能                  │
│   learn_from_url     — 从网页学技能（7步认知管线）              │
│   Dispatcher         — 判断用户意图，路由到正确的技能             │
│   MetaSkill          — 把多个技能编排成流水线                  │
├─────────────────────────────────────────────────────────────┤
│                     质量评价层（⭐ MoE 多专家）                  │
│                                                             │
│   Evaluation MoE — 6个独立评委 + 交叉模型验证 + 置信度评分      │
│   structure(1.2) security(1.5) params(1.2) routing(1.3)      │
│   content(1.0) brevity(0.8) — 聚焦评分，聚合加权              │
├─────────────────────────────────────────────────────────────┤
│                     知识质量控制层（⭐ 本项目独创）               │
│                                                             │
│   Epistemology (认识论)  — 这段话是真知识还是幻觉？              │
│   Knowledge Graph (知识图谱) — 知识之间的关联网络               │
│   Pattern Miner (DNA)    — 从所有技能中提炼好技能的本质          │
│   Skill Variants (多态)  — 同一技能的不同版本和竞争              │
│   Lineage (数据血缘)     — 每条知识从哪来、经过了什么处理           │
│   Deep Digest            — 把文章消化为结构化知识包              │
├─────────────────────────────────────────────────────────────┤
│                     技能进化层                                │
│                                                             │
│   MoE Router      — 自动选择用哪种优化策略                      │
│   SkillOpt        — 精细调优，编辑预算递减                      │
│   SkillHone       — 决策历史 + 定向回滚 + 角色隔离               │
│   EvoSkill        — 生成候选，擂台淘汰                         │
│   Trace2Skill     — 从执行轨迹中批量诊断                        │
│   Learning Theory — 遗忘曲线 + 费曼技巧 + 类比迁移               │
│   ZPD Records     — 追踪你对每个技能的掌握程度                   │
├─────────────────────────────────────────────────────────────┤
│                     存储层                                    │
│                                                             │
│   skills/ 目录    — 每个技能一个文件夹（SKILL.md + 历史版本）      │
│   knowledge/ 目录 — 知识图谱 + 认识论状态 + DNA + 变体注册表       │
│   data/ 目录      — SQLite 数据库（对话历史、市场交易）            │
│   agentskills.io 标准 — 输出的技能任何 AI 工具都能用              │
└─────────────────────────────────────────────────────────────┘
```

**文件组织结构**（58 个 Python 文件，单向依赖）：

```
skillos/
  api/          (8 个文件)  — REST API 端点，对外接口
  skills/       (10 个文件) — 技能创建、存储、调度、变体、DNA
  knowledge/    (12 个文件) — 认识论、图谱、血缘、消化、记忆
  evolution/    (8 个文件)  — 进化引擎、优化器、学习理论
  marketplace/  (5 个文件)  — 技能市场（发布、搜索、支付）
  utils/        (7 个文件)  — 网页抓取、文件转换、微信、监控
  config.py     — 配置管理
  llm_client.py — LLM 调用统一接口
  mcp_server.py — MCP 协议服务
  benchmark.py  — 基准测试系统
```

---

## 4. 每个模块是干什么的

> 以下对每个模块的解释面向**不懂代码的读者**。括号里 58→17,465 表示 58 个文件共 17,465 行代码。行数只是一个规模参考。

### 4.0 MoE 评价体系

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `evaluation/experts.py` | 170 | 6 个独立专家评委定义 | 每个评委只评 1-2 个维度，聚焦 prompt 比单一大 prompt 评 10 维更准。安全评委权重 1.5（最高），简洁度权重 0.8（最低） |
| `evaluation/moe.py` | 200 | MoE 引擎 + 交叉模型验证 | 加权聚合 + 置信度计算。可选交叉模型：用便宜模型复评，差异 > 15 分标记警告。`evaluate_skill()` → `MoEReport` |
| `evaluation/quality.py` | 170 | 三层质量口径 | `draft_readiness` 1–5（对话）≠ `heuristic` 0–100（CI）≠ `moe` 0–100（官方终稿）。禁止混用 |
| `evaluation/__init__.py` | 30 | 公共 API | `from skillos.evaluation import evaluate_skill` |

**API**：`GET /api/skills/{name}/evaluate`、`GET /api/skills/{name}/evaluate/markdown`。技能创建时自动跑 MoE（非阻塞）。

### 4.0b 领域分类 + 方法论检测（新增）

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `knowledge/taxonomy.py` | 220 | 8领域分类 + 6方法论检测 | 领域决定"什么算正确"（工程=可测试，科学=可复现，法律=法条引用）。方法论决定"怎么思考"（还原论/经验主义/实用主义）。跨领域类比：代码审查（工程）和论文审稿（出版）是同构的诊断方法论 |
| `skills/context_budget.py` | 110 | 上下文 token 预算比例控制 | LLM Wiki 启发：50%技能库/25%历史/15%系统/10%索引，替代硬编码 MAX_TOOLS=20 |
| `knowledge/ingestion_queue.py` | 270 | 摄入持久化队列 + 知识空白研究 | LLM Wiki 启发：磁盘队列+串行处理+重启恢复+3次重试。自动检测稀疏社区/孤立节点→入队研究 |

### 4.0c SkillsBench 基准测试（新增）

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `skills_bench.py` | 270 | SkillsBench 兼容 100 分制评分 | 确定性评分（60分规则+40分MoE）。Correctness/40 + Security/20 + Completeness/20 + Robustness/20 |
| `skillsbench_tasks.py` | 280 | 8 个领域匹配任务 + 领域匹配对比 | 代码审查/数据处理/API设计/文档/工作流。with-skill vs without-skill 领域匹配对比。GitHub PR 审查 +9%（客观验证） |

### 4.0d 三层 DNA + Path B 冷启动 + 本地 Bench（2026-06-18）

**三层 DNA 分工**（详见 `philosophical_dna.py` / `domain_templates.py` / `pattern_miner.py`）：

| 层 | 模块 | 运行时作用 | Bench 提分 |
|:--:|------|-----------|:----------:|
| **L0 哲学** | `philosophical_dna.py` + `dna_context.py` | 萃取 prompt 注入方法论；写 `dna_lineage` | 不直接 |
| **L1 领域** | `domain_templates.py` + **`domain_pack.py`** | HERITAGE 应答速查 + pack 任务强制 inject | **主因** |
| **L2 技能** | `pattern_miner.check_dna_compliance()` | 6 条结构原则合规 | 间接 |

**Path B（Auto Cold Start）**：烟测失败 → anchor rubric 反推 HERITAGE → 路由扩展 → prune/repair → 复测。入口：`skillos/skills/cold_start.py`；持久化：`data/domain_packs/*.json`（10 个 pack）。

**Bench cohort**（`bench_cohorts.py`）：

| Cohort | 技能 | 用途 |
|--------|------|------|
| 参考 | 电商退款 / 合同审核 / 安全审计 | 回归 Quick8 Δ |
| 泛化 | 财务欺诈 / 法律 triage / 医疗分诊 | 冷启动 + ablation |

**Layer 1 ablation**（`evaluation/ablation.py`）：2×2 factorial — HERITAGE on/off × pack-scoped inject on/off。报告：[`docs/paper/experiments/layer1_ablation_results.md`](docs/paper/experiments/layer1_ablation_results.md)。

**本地脚本**：[`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) · 回归：`scripts/run_bench_regression.py`

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `skills/cold_start.py` | — | Path B 冷启动主循环 | anchor rubric → HERITAGE refine → quick8 expand → prune/repair |
| `skills/domain_pack.py` | — | 动态领域 pack 读写 | anchor hints、expand 负向过滤、跨域题清理 |
| `skills/bench_cohorts.py` | — | 参考/泛化 cohort 定义 | 回归与 ablation 共用 |
| `knowledge/skill_routing.py` | — | pack 任务强制 inject | `pack_scoped_inject` ablation 开关 |
| `evaluation/ablation.py` | — | Layer 1 2×2 评测 | heritage / pack 边际贡献量化 |
| `benchmark_local.py` | — | dashboard API 数据层 | `generalize_skills` / regression 快照 |

### 4.1 基础设施（所有模块都依赖的）

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `config.py` | 175 | 管配置（API key、模型名） | 支持 DeepSeek 和火山引擎双模式，配置可以写回 .env 文件。**给 AI 的 note**：所有配置通过 `get_config()` 单例获取，不要直接读 os.environ |
| `llm_client.py` | 130 | 所有 LLM 调用的统一入口 | 自动重试（指数退避），失败时 fallback 到本地 Ollama。新增 `call_with_tools()` 支持 OpenAI function calling |

### 4.1 知识质量控制层（⭐ 独家创新）

这些模块是 SkillOS 和全世界所有其他技能系统最本质的区别。别人只管"执行"，SkillOS 管"对错"。

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `knowledge/epistemology.py` | 430 | **这段话是真知识还是幻觉？** | 实现 Plato 的 justified true belief + Popper 的证伪测试。每条声明都要经过 LLM 主动反驳才能升级为 Knowledge。全球唯一 |
| `knowledge/graph.py` | 486 | 知识之间的关联网 | 8 种关系类型（"是一个""属于""依赖""矛盾"等）。边每用一次权重+0.1，经常一起用的知识自动变强。自动聚类发现"前端技能""后端技能"等分类 |
| `knowledge/lineage.py` | 923 | 每条知识从哪来、经过什么处理 | 完整追溯：这个事实是从文章第几段提取的→被哪些技能引用过→当前还有效吗 |
| `knowledge/deep_digest.py` | 692 | 把文章消化为结构化知识包 | 6 步消化：扫描分类→提炼论点→术语表→模式挖掘→速查表→交叉引用。输出 glossary.md + patterns.md + cheatsheet.md |
| `knowledge/playbook.py` | 283 | 团队共享背景知识 | 在创建技能前，先花 10-15 分钟建立团队的 PLAYBOOK.md（术语、风格、标准）。后续所有技能输出都符合团队规范 |
| `knowledge/memory.py` | 160 | 两层记忆系统 | ① 全局对话洞察（HereVault 启发）② 按技能记忆（偏好、决策历史、对话记录） |
| `knowledge/store.py` | 213 | 知识库的存储和搜索 | 双层检索：低层关键词匹配 → 高层图谱遍历 |
| `knowledge/extractor.py` | 203 | 从文本中提取知识 | 来源权威权重（arxiv 0.85 > github 0.7 > 公众号 0.35），交叉验证去重 |
| `knowledge/skill_kb.py` | 403 | 按技能的知识库 | 每个技能可以有自己的私有知识库 |
| `knowledge/refresher.py` | 133 | 自动检查源内容变化 | SHA256 检测源变化 → 自动重新消化 → 更新知识包 |

### 4.2 技能引擎（核心工作流）

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `skills/agent.py` | 1,307 | **大脑。一切技能创建的核心** | 三种创建方式：① 苏格拉底对话（双输出：每轮同时出问题+草稿）② 7步URL学习管线（Feynman+Bloom+刻意练习）③ 知识扩散（新知识自动改已有技能）。场景推演式提问 + 质量评分告知 + 渐进草稿保存 |
| `skills/skill_store.py` | 167 | 技能的增删改查 | 保存时自动版本归档（v1.md, v2.md...）+ 安全扫描 + 变体自动检测。**给 AI 的 note**：skill 格式是 `---\nYAML前言\n---\n\nMarkdown正文` |
| `skills/dispatcher.py` | 515 | 判断用户想干什么，路由到正确技能 | 保守路由："不确定就不匹配"。技能自动转为 OpenAI function calling 工具。执行时自动进行变体分发（选择最适合当前场景的版本） |
| `skills/agent_factory.py` | 77 | 把技能文档变成可执行的 AI 助手 | 加载技能文档 → 构建 system prompt → 注入知识库上下文 → 创建可调用的 agent |
| `skills/metaskill.py` | 432 | 把多个技能编排成流水线 | 声明式 DAG："步骤A 依赖步骤B 的输出"。自动拓扑排序和循环检测 |
| `skills/pattern_miner.py` | 595 | **从所有技能中提炼好技能的本质（DNA）** | 四层挖掘：结构原型→成功因子→反模式→DNA 原则。DNA 生成时自动注入到新技能创建中。6 条硬编码验证规则 |
| `skills/variants.py` | 326 | **同一技能的不同版本** | Java 风格多态：Archetype=接口，Variant=实现，@Override=步骤覆写。Plato 理型论 + Wittgenstein 家族相似性。自动发现 + 语境分发 |
| `skills/session_manager.py` | 130 | 管理多用户会话 | 30分钟无活动自动过期。服务重启后从 SQLite 恢复历史。每个 session 持有自己的 agent 实例 |
| `skills/tool_registry.py` | 329 | 技能用什么工具 | Knowledge/Tools/Skills 三层分离。删工具前能看到影响哪些技能。支持内置/MCP/API/函数四种工具类型 |
| `skills/conversation_store.py` | 106 | 对话历史存 SQLite | WAL 模式写不阻塞读。30天自动清理 |

### 4.3 进化引擎（让技能越用越好）

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `evolution/skillopt.py` | 1,719 | **优化引擎核心** | MoE 三专家路由 + ElitePool 淘汰赛 + 10 维审计 + 编辑预算递减（前 4 后 1，先粗后细）。受 Microsoft SkillOpt 论文启发 |
| `evolution/skillhone.py` | 603 | **决策历史 + 回滚 + 隔离** | 每次修改记录 WHY 链（诊断→候选→评估→结果）。定向回滚：只退退步的段落，保留有益修改。角色隔离：优化器不能碰测试题 |
| `evolution/engine.py` | 406 | **进化触发和调度** | 检测三种触发条件：分数衰减/技能生疏/DNA 不合规。每 6 小时自动运行。跨经验关联：Skill A 的失败自动标记相关 Skill B 的同类步骤 |
| `evolution/evolver.py` | 462 | **轨迹记录 + 进化执行** | 记录每次技能执行的结果（trace）。判断改进是实质性的(significant)还是措辞变化(marginal) |
| `evolution/learning_theory.py` | 415 | **人类学习理论工程化** | Ebbinghaus 遗忘曲线：不用的技能自动降权。递归费曼：3 层简化暴露理解边界。类比迁移：发现"代码审查"和"论文审稿"结构同构 |
| `evolution/learning_records.py` | 187 | **追踪你的学习进度** | ZPD（最近发展区）：5 状态机（new→learning→learned→confused→mastered）。系统根据你的掌握程度调整引导粒度 |

### 4.4 API 层（对外接口）

| 文件 | 行数 | 一句话 |
|------|:--:|------|
| `api/server.py` | 57 | FastAPI 服务启动 |
| `api/skills.py` | 567 | 技能 CRUD + 统一消息分发 + 文件上传 + 导出 + DNA/变体端点 |
| `api/knowledge.py` | 218 | 知识列表/血缘/图谱/wisdom/journal/review + 公众号监控 |
| `api/evolution.py` | 141 | 优化/状态/MoE 路由/整合 |
| `api/marketplace.py` | 129 | 市场统计/搜索/发布 |
| `api/auth.py` | 60 | 登录/注册/验证 |
| `api/middleware.py` | 154 | 限流 + token 哈希 + 技能安全扫描（10 种危险模式） |

### 4.5 工具层

| 文件 | 行数 | 一句话 | 巧思 |
|------|:--:|------|------|
| `utils/web_fetch.py` | 120 | 抓取网页 | 多编码检测（utf-8/gbk/gb2312），对中国网站友好 |
| `utils/web_search.py` | 83 | 搜索网页 | Bing 搜索，中国市场可用 |
| `utils/wechat_fetch.py` | 205 | 抓取微信公众号文章 | CDP 浏览器真实渲染（微信公众号有反爬） |
| `utils/file_ingest.py` | 275 | 30+ 格式转 Markdown | PDF/Word/Excel/PPT/图片/音频/压缩包 → MarkItDown。SHA256 缓存跳过重复文件 |
| `utils/watcher.py` | 113 | 监控文件夹自动导入 | 丢文件到 inbox → 自动检测 → 消化 → 归档 |
| `utils/account_watcher.py` | 249 | 监控微信公众号更新 | 定时检查 + 新文章自动消化 |
| `mcp_server.py` | 652 | MCP 协议服务 | 任何 MCP 客户端可接入 SkillOS |
| `hermes_bridge.py` | 278 | Hermes Agent 互操作 | 双向技能互通 |

---

## 5. API 接口清单

### 完整端点（30+，0 个桩）

| 路由 | 方法 | 说明 |
|------|:--:|------|
| `/api/skills/` | GET | 列出所有技能 |
| `/api/skills/{name}` | GET | 获取技能详情 |
| `/api/skills/dispatch` | POST | **核心端点**。接受文字/URL/文件，自动路由 |
| `/api/skills/ingest` | POST | 文件上传（30+ 格式，自动分类 actionable vs conceptual） |
| `/api/skills/create` | POST | 从文本一键创建技能 |
| `/api/skills/{name}/run` | POST | **执行技能**（真实 LLM 执行 + 记录 trace + 评分） |
| `/api/skills/{name}/export` | GET | 导出（markdown / universal JSON） |
| `/api/skills/{name}/traces` | GET | 获取执行轨迹 |
| `/api/skills/{name}/security` | GET | 安全扫描 |
| `/api/skills/{name}/dna-check` | GET | DNA 合规检查 |
| `/api/skills/dna/view` | GET | 查看当前 Skill DNA |
| `/api/skills/dna/remine` | POST | 重新提炼 DNA |
| `/api/skills/{name}/variants` | GET | 查看技能变体（求同存异） |
| `/api/skills/{name}/variants` | POST | 注册新变体 |
| `/api/skills/variants/detect` | GET | 自动发现变体家族 |
| `/api/knowledge/` | GET | 列出知识项（含有效性过滤） |
| `/api/knowledge/lineage` | GET | 列出所有知识血缘 |
| `/api/knowledge/lineage/{id}` | GET | 查看特定血缘详情 |
| `/api/knowledge/lineage/{id}/graph` | GET | 血缘图（cytoscape + mermaid） |
| `/api/knowledge/graph/clusters` | GET | 知识图谱聚类 |
| `/api/knowledge/wisdom` | GET | 跨血缘洞察 |
| `/api/knowledge/journal` | GET | 学习日志 |
| `/api/knowledge/review` | GET | 待审核经验列表 |
| `/api/evolution/{name}/optimize` | POST | 运行优化 |
| `/api/evolution/{name}/state` | GET | 技能状态（用于 MoE 路由） |
| `/api/evolution/{name}/route` | POST | MoE 路由决策 |
| `/api/evolution/consolidate` | POST | 全局知识整合 |
| `/api/auth/login` | POST | 登录 |
| `/api/auth/register` | POST | 注册 |
| `/api/auth/me` | GET | 当前用户 |

### 分发端点（`POST /dispatch`）路由逻辑

```
用户发来一条消息
  │
  ├─ 含有 URL？
  │   ├─ 抓取页面内容
  │   ├─ 当前正在萃取对话中？ → 注入到萃取上下文，帮助萃取
  │   └─ 不在萃取中 → LLM 判断：是方法论文章还是概念参考？
  │       ├─ 方法论 → 7步学习管线（创建可执行技能）
  │       └─ 概念   → deep_digest（创建知识包）
  │
  ├─ 含有技能关键词？（技能/skill/萃取/沉淀/帮我创建...）
  │   ├─ 没在萃取中 → 开始苏格拉底对话
  │   └─ 已在萃取中 → 继续对话（每轮双输出：问题+草稿）
  │
  ├─ 含有 Playbook 关键词？（冷启动/团队手册/术语表...）
  │   └─ 启动冷启动访谈，引导创建团队 PLAYBOOK.md
  │
  └─ 都不匹配 → 普通 AI 聊天
```

---

## 6. 给 AI 编程工具的指引

> 如果你是 Claude Code、Cursor、Codex、或任何 AI 编程工具，请遵循以下约定。

### 6.1 代码风格和约定

```python
# ✅ 正确的 import 方式（使用完整包路径）
from skillos.config import get_config
from skillos.skills.skill_store import save_skill

# ❌ 错误的 import（裸 import 在包内无法解析）
from web_search import search        # 错！应该 from skillos.utils.web_search import search
import skillopt as opt               # 错！应该 from skillos.evolution import skillopt as opt

# ✅ 获取配置的正确方式
cfg = get_config()
llm_args = cfg.to_llm_args()         # 返回 (api_key, base_url, model, chat_kwargs)
model = llm_args[2]                  # model 是 tuple 第三个元素

# ❌ 获取配置的错误方式（这些函数不存在）
config.get_api_key()    # 不存在！
config.get_model()      # 不存在！
config.get_chat_kwargs() # 不存在！
```

### 6.2 关键设计约束（不要破坏这些）

| 规则 | 原因 |
|------|------|
| **Skill 输出格式必须兼容 AgentSkills.io** | `---\nYAML\n---\n\nMarkdown` 格式。YAML 必须包含 `name` 字段 |
| **认识论引擎是核心** | 不要绕过 epistemology 层直接存知识。所有声明都应该走 `record_claim()` |
| **异常必须记录日志** | 不要 `except Exception: pass`。至少 `_log.debug(...)` 或 `_log.warning(...)` |
| **API 端点返回真实数据** | 不要返回硬编码的 `{"total": 0, "items": []}`。所有端点必须接入真实引擎 |
| **保持单向依赖** | api → skills/knowledge → llm_client。不要反向引用 |
| **线程安全** | config 写操作（`save_settings`）有锁。db.py 的 `get_conn()` 是线程安全的。新增模块不要绕过这些 |
| **安全扫描** | `save_skill()` 入口处会自动扫描 10 种危险模式。新增危险模式添加到 `middleware.py` 的 `DANGEROUS_PATTERNS` |

### 6.3 测试约定

```python
# 测试文件命名：tests/test_<模块>.py
# 类命名：Test<功能>
# 方法命名：test_<具体测试点>

# 集成测试放到 tests/test_integration.py
# 不要写依赖外部服务的测试（标注 skip）
# 运行测试：python -m pytest tests/ -v
```

### 6.4 最常见的修改场景

| 场景 | 改哪个文件 | 注意什么 |
|------|-----------|---------|
| 新增 API 端点 | `api/skills.py` 等 | 保持路由注册在 `server.py` |
| 改进萃取对话 | `skills/agent.py` | Phase 枚举的状态机不要打破；双输出模式不要改 |
| 改进 URL 学习管线 | `skills/agent.py:learn_from_url` | 7 步顺序不要跳；每一步的 token 预算不要大幅变动 |
| 新增 DNA 原则 | `skills/pattern_miner.py` | 硬编码原则在 `check_dna_compliance()`；软发现由 LLM 做 |
| 新增文件格式支持 | `utils/file_ingest.py` | 新格式加到 `MARKITDOWN_FORMATS` 或 `PLAIN_TEXT_FORMATS` |
| 修改 LLM 调用 | `llm_client.py` | 所有模块都通过 `call()` 调用。新增能力如 function calling 用 `call_with_tools()` |

---

## 7. 移植记录

从 Skill Distiller 的 30+ 个文件移植到 SkillOS 的 58 个模块。以下是每个模块的移植状态。

### 忠实移植（仅改 import 路径，逻辑完全一致）

| SD 原文件 | SkillOS 位置 | 行数对比 | 备注 |
|-----------|-------------|:--:|------|
| deep_digest.py | knowledge/deep_digest.py | 692→692 | 6阶段知识包管道，完全一致 |
| dispatcher.py | skills/dispatcher.py | 515→515 | 保守路由，完全一致 |
| metaskill.py | skills/metaskill.py | 432→432 | 声明式DAG管道，完全一致 |
| pattern_miner.py | skills/pattern_miner.py | 594→595 | Skill DNA提炼，完全一致 |
| skillopt.py | evolution/skillopt.py | 1,702→1,719 | MoE+ElitePool+审计，完全一致 |
| skillhone.py | evolution/skillhone.py | 603→603 | 决策历史+回滚+隔离，完全一致 |
| learning_theory.py | evolution/learning_theory.py | 415→415 | 遗忘曲线+费曼+类比，完全一致（修 NameError） |
| learning_records.py | evolution/learning_records.py | 187→187 | ZPD追踪，完全一致 |
| skill_variants.py | skills/variants.py | 325→326 | Java风格多态，完全一致（已接入API） |
| playbook.py | knowledge/playbook.py | 283→283 | 团队共享背景，完全一致 |
| tool_registry.py | skills/tool_registry.py | 329→329 | 三层分离，完全一致 |
| conversation_store.py | skills/conversation_store.py | 106→106 | SQLite持久化，完全一致 |
| web_search.py | utils/web_search.py | 83→83 | Bing搜索，完全一致 |
| web_fetch.py | utils/web_fetch.py | 120→120 | 多编码网页抓取，完全一致 |
| file_ingest.py | utils/file_ingest.py | 275→275 | MarkItDown转换，完全一致 |
| knowledge_graph.py | knowledge/graph.py | 446→486 | 8种关系+聚类，+EvoRAG贡献追踪 |
| knowledge_lineage.py | knowledge/lineage.py | 923→923 | 数据血缘，修复2个import bug |
| evolution_engine.py | evolution/engine.py | 365→406 | 进化触发+调度器 |
| skill_evolver.py | evolution/evolver.py | 462→462 | 轨迹记录+进化执行 |

### 架构重设计

| SD 原文件 | SkillOS 位置 | 行数对比 | 说明 |
|-----------|-------------|:--:|------|
| skill_agent.py | skills/agent.py | 1,319→1,307 | 重设计：苏格拉底双输出+场景推演+质量评分+渐进草稿+外部注入+知识扩散 |

### 功能增强

| SD 原文件 | SkillOS 位置 | 变化 | 说明 |
|-----------|-------------|:--:|------|
| epistemology.py | knowledge/epistemology.py | 438→430 | +Graphiti时序模型(valid_at/invalid_at/SUPERSEDED)，完整的证伪管线 |
| skill_memory.py | knowledge/memory.py | 117→160 | 重写为双层系统（全局洞察+按技能记忆） |
| config.py | config.py | 184→175 | +Hermes配置集成+save_settings+volcano引擎 |
| llm_client.py | llm_client.py | 139→130 | +call_with_tools+自动重试+Ollama fallback |
| skill_store.py | skills/skill_store.py | 195→167 | 简化版，已加版本归档+安全扫描+变体检测 |
| session_manager.py | skills/session_manager.py | 150→130 | +SQLite持久化+重启恢复 |

### 不再需要移植

| SD 模块 | 原因 |
|---------|------|
| asr_cloud, funasr, tts, voice_input | Hermes 原生支持语音 |
| skill_server.py | 被 FastAPI 模块化路由替代 |
| skillhub_cli.py | MCP 接入后 CLI 非主要入口 |
| user_store, i18n | 被 marketplace/auth.py 替代或推迟 |
| chromadb | 从未使用，已从依赖中移除 |
| skillhub_scorer.py | 嵌入到 marketplace/scorer.py |

---

## 8. 竞品对比与定位

### 学术前沿

| 论文 | 时间 | 做了什么 | SkillOS 对比 |
|------|------|---------|------------|
| Microsoft SkillOpt | 2025.05 | 文本学习率+验证门+52/52 SOTA | 互补：SkillOpt 做优化训练，SkillOS 做创建+质量 |
| EXIF | 2025.06 | 探索Agent+目标Agent自我进化 | SkillOS 有进化但非探索驱动 |
| Anything2Skill | 2026.06 | 异构知识→统一技能格式 | SkillOS 覆盖此路径（deep_digest+URL管线） |
| SkillFlow | 2025.04 | 36K 技能库+4阶段检索 | SkillOS 有 dispatcher+pattern_miner |
| MemSkill | 2026.02 | 记忆技能自我进化 | SkillOS 有双层记忆系统 |
| Memento-Skills | 2025.03 | Agent 设计 Agent，RL 进化 | SkillOS 规则式进化 |
| Trace2Skill | 2025.03 | 轨迹→局部经验→可迁移技能 | SkillOS evolver 从 trace 诊断根因 |
| SkillFoundry | 2026.04 | 科学资源自动挖掘为技能库 | SkillOS 的 deep_digest 覆盖文档→知识包 |

### 工业平台

| 平台 | 技能创建 | 质量验证 | 自进化 | 输出标准 |
|------|:--:|:--:|:--:|:--:|
| Dify | 表单+代码 | ❌ | ❌ | 平台锁定 |
| Coze | 拖拽工作流 | ❌ | ❌ | 平台锁定 |
| LangChain | 纯代码 | ❌ | ❌ | 代码级 |
| **SkillOS** | **苏格拉底对话** | **认识论引擎** | **MoE+扩散** | **AgentSkills.io** |

### SkillOS 的独特优势

1. **认识论引擎** — 全球唯一。没有任何其他系统实现 Plato+Popper 工程化来验证技能质量
2. **苏格拉底对话萃取** — 不可替代。人机协作式知识提取 vs 全自动黑盒
3. **技能多态系统** — Java 风格 Interface/Concrete/@Override，Wittgenstein 家族相似性
4. **知识扩散** — 生成新技能 → 自动发现可改善的已有技能 → 应用改进
5. **AgentSkills.io 兼容** — 输出可在 30+ 平台直接使用

---

> **"一个好的 skill 系统不应该只是 skill 的容器——它应该比创建 skill 的人更理解 skill 的质量、关系和进化方向。"**
>
> 本设计书基于 Skill Distiller PROJECT_DESIGN.md，更新至 SkillOS 2026年6月状态。
> 58 个模块 | 17,465 行 | 111 个测试 | 0 个桩代码 | 30+ API 端点。
