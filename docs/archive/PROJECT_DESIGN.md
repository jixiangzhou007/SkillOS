# SkillOS — 项目设计与巧思

> "不是又一个 Agent 平台——是给 Agent 造子弹的兵工厂。"
>
> Skill Distiller 的完全体。基于 Hermes Agent 底座，通过 MCP 协议接入任何 AI 客户端。

---

## 一、架构哲学

### 1.1 Hermes 做底座，SkillOS 做上层

```
微信/飞书/WhatsApp ──→ Hermes Gateway ──→ Hermes Agent ──MCP──→ SkillOS
Claude Code ────────────────────────────→                          │
Cursor ─────────────────────────────────→                          │
任何 MCP 客户端 ────────────────────────→                    技能工程引擎
                                                             知识内化管线
                                                             进化优化系统
                                                             市场分发网络
```

**Hermes 管执行，SkillOS 管创造。** Hermes 升级不影响 SkillOS——两者通过 `~/.hermes/skills/` 目录和 MCP 协议通信。

### 1.2 MCP 通用协议——一次开发，全平台可用

| 客户端 | 接入方式 |
|--------|---------|
| Claude Code | `mcpServers.skillos` 配置 |
| Hermes Agent | `hermes mcp add skillos` |
| Cursor | 同 Claude Code 配置 |
| 任何 MCP 客户端 | 标准 MCP stdio 协议 |

### 1.3 小模型写规则，大模型用规则

```
SKILLOS_EVOLVER_MODEL=deepseek-v4-flash   # 便宜，专门优化 Skill
SKILLOS_EXECUTOR_MODEL=deepseek-v4-pro    # 强，专门执行萃取
```

进化引擎每天跑几十轮优化只花几分钱。这和论文结论一致：Harness-Updating（写规则）可以用小模型，Harness-Benefit（用规则）需要大模型。

---

## 二、知识工程核心

### 2.1 七步认知学习流水线

```
初识 → 理解 → 拆解 → 重构 → 验证 → 内化 → 沉淀 → 扩散
```

不是机械提取，而是模拟人类深度学习：先理解"为什么"，再拆解"怎么做"，费曼重构时主动暴露理解边界，验证阶段对抗性测试找弱点。

### 2.2 认识论四层分级

```
Evidence → Experience → Knowledge → Preference → Error → Superseded
```

- **Plato**: justified true belief → Experience 升 Knowledge 需 ≥2 独立来源
- **Popper**: 证伪主义 → 通过证伪测试比找支持证据更强
- **Graphiti**: 时序模型 → 每条知识有 valid_at/invalid_at，矛盾时标记失效而非删除

### 2.3 知识图谱——8 种类型化关系

```
is_a / part_of / depends_on / contradicts / generalizes / analogous_to / derived_from / evolved_to
```

卢曼 Zettelkasten 哲学：结构从链接中涌现，不从预设分类中定义。标签传播算法自动聚类。

### 2.4 数据血缘——从源头到智慧的完整链路

```
Source URL → ExtractStep(初识) → ExtractStep(理解) → ... → KnowledgeItem
                                                              ├─ graph_node
                                                              ├─ affected_skills
                                                              └─ confidence_chain
```

每个知识项携带完整的历史：从哪个段落提取、经过哪些管道步骤、影响了哪些 Skill、当前还有效吗。

### 2.5 双层检索

```
低层检索: 关键词匹配 → 文档块 (精确)
高层检索: 关键词 → 图谱遍历邻居 → 聚合主题 (宏观)
```

LightRAG 启发：不在索引阶段死磕全局结构，查询时动态拼出全局视野。

---

## 三、进化引擎

### 3.1 MoE 混合专家路由

```
                    ┌─────────────────┐
                    │  Gating Network │
                    │ (trace_count,    │
                    │  score_variance, │
                    │  maturity, ...)  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  Trace2Skill           EvoSkill             SkillOpt
  批量发现              擂台筛选              精细调优
 "先看够多，            "生成候选，            "小步编辑，
  再一次写成"            打擂存活"             核心焊死"
```

根据技能状态自动选择优化策略：新技能→批量诊断，波动大→打擂筛选，稳定→精细优化。

### 3.2 10 维独立审计

每次优化后自动跑 10 维度检查：

| # | 维度 | 检查内容 |
|---|------|---------|
| 1 | self_contained | 独立可用，不依赖外部魔法文件 |
| 2 | entry_visibility | 5 秒内找到入口 |
| 3 | hardcoded_constants | 具体值→抽象参数 |
| 4 | silent_bypass | 跳过关键步骤不报错 |
| 5 | overfitting | 规则只适用训练样例 |
| 6 | param_abstraction | 决策轴在 S_params 中暴露 |
| 7 | description_quality | 触发词+边界条件 |
| 8 | decision_table | 路由覆盖所有分支 |
| 9 | portability | Claude/Codex/Hermes 跨平台兼容 |
| 10 | brevity | LLM 越强，Skill 越短 |

### 3.3 持久决策历史——WHY 链

```
每次修改记录四元组: (诊断 → 候选修订 → 评估证据 → 结果)

不是版本 diff——diff 告诉你文件怎么变，
决策历史告诉你: 为什么变、靠什么判断、变完效果如何。
```

后续 Agent 可以查阅历史判断"这个修复以前试过没""那个方案为什么被否决"。

### 3.4 定向回滚

```
整版改完 → 某维度退步 → 不是全部拒绝
                     → 只回滚退步的段落
                     → 保留其他有益的修改
```

### 3.5 角色隔离

```
Optimizer: 只看脱敏报告，不能碰测试题和评分器
Evaluator: 跑测试但不能碰技能库
```

权限边界是结构性（不同 Agent、不同权限），不是 prompt 级别的约束。

---

## 四、技能多态——求同存异

### 4.1 哲学根基

| 哲学家 | 理论 | 工程化 |
|--------|------|--------|
| **Plato** | 理型论 (Theory of Forms) | Archetype 是理想 Form——所有变体共享的共性原则。每个 Variant 是对这个理型的具象化 |
| **Wittgenstein** | 家族相似性 | 技能之间不共享一个本质，而是重叠相似性的网络。同一 Archetype 下的 Variants 不需要在所有维度一致 |
| **Java 多态** | Interface/Concrete/@Override | 工程实现：Interface = Skill DNA, Concrete = Skill Variant |

### 4.2 架构

```
Archetype: "客服回复"  (DNA — 所有变体必须满足的共性)

Variant A: 客服主管    @Override S_body.步骤2: 关键词匹配 → 语义理解
Variant B: NLP工程师   @Override S_body.步骤2: 关键词匹配 → 意图识别+实体提取
Variant C: 一线客服    @Override S_body.步骤2: 关键词匹配 → 先看最近3条记录再匹配
```

### 4.3 为什么不是"统一成一套"

```
统一成一套 → 必须有人拍板"哪个做法是对的" → 拍板的人可能是错的
求同存异   → 不同做法共存、竞争、比较 → 得分高的自然胜出
```

每个 Variant 附带认识论标注（来源、置信度、验证得分、被谁证实），差异可见、可比较、可进化。这和 **Popper** 的证伪主义一致：不是找"最正确的那个"，而是让它们在竞争中淘汰。

## 五、SkillHub 市场

### 4.1 信任基础设施

```
Publish → 生成 3-5 测试任务 (作者看不到)
       → Fresh Agent 加载 Skill 执行 → 调用率 + 均分 → 执行分
       → Auditor 10 维检查 → 审计分
       → overall = 执行分 × 0.6 + 审计分 × 0.4
       → Gate: ≥70 自动通过 | 50-69 待审核 | <50 自动拒绝
```

### 4.2 精英池淘汰赛

```
维护 Top-3 版本。新候选必须打赢池底才能入池。
败者进淘汰历史库 → 喂给提案者当反面教材。
```

### 4.3 完整市场管线

```
Publish → Score → Gate → Subscribe → Purchase → Revenue → Sync → Update
```

---

## 六、工程特色

### 5.1 零依赖 Hermes 也能独立运行

```
云端模式: DEEPSEEK_API_KEY → 全功能
本地模式: Ollama → llama3.2 → 全功能，不花 API 费
```

### 5.2 文件系统自动监控

```
~/.skillos/inbox/ 丢文件 → 自动检测 → MarkItDown 转 Markdown
→ Deep Digest 生成知识包 → 移入 .processed/ 归档
```

### 5.3 源变化自动刷新

```
SHA256 检测源内容变化 → 自动重新消化 → 更新知识包
后台定期巡检 (默认 24h)
```

### 5.4 对话记忆持久化

```
AI 对话 → Session 结束时 LLM 提取洞察
→ 分类 (preference/fact/decision/insight)
→ 存入 ~/.skillos/memories/
```

HereVault 启发：对话中有价值的知识不应该用完就丢。

### 5.5 微信公众号 / 小红书 CDP 抓取

```
微信公众号 (反爬) → CDP 浏览器 → 真实渲染 → 提取正文
常规网站 → HTTP → 直接抓取
```

### 5.6 模块化架构

```
42 个 Python 模块，按功能域分离:
  api/      FastAPI 路由 (6 文件)
  skills/   技能引擎 (8 文件)
  knowledge/ 知识引擎 (9 文件)
  evolution/ 进化引擎 (8 文件)
  marketplace/ 市场 (4 文件)
  utils/    工具 (5 文件)
```

对照 Skill Distiller 的痛点：不再有 3200 行单文件、不再有类边界 bug、从第一天起就有测试。

---

## 七、借鉴清单

| 来源 | 借鉴的设计 | 落地位置 |
|------|-----------|---------|
| Graphiti | 双时态模型 + 边失效 | epistemology, lineage |
| LightRAG | 增量图更新 + 双层检索 | lineage, store |
| LLM Wiki | 4 信号关联 + SHA256 缓存 + 文件监控 | lineage, file_ingest, watcher |
| SkillHone | 决策历史 + 定向回滚 + 角色隔离 | skillhone |
| EvoSkill | 精英池淘汰赛 | skillopt |
| Trace2Skill | 批量集体诊断 | skillopt |
| SkillOpt | 有界编辑 + 验证门 + 保护区域 | skillopt |
| Crawl4AI | 自适应提取 + 源变化刷新 | refresher |
| HereVault | 对话记忆持久化 | memory |
| SkillsBench | 跨平台可移植性验证 | skillopt (portability) |
| Claude for Legal | Cold-start interview + Playbook | playbook |
| book-to-skill | 结构化知识包 (glossary/patterns/cheatsheet) | deep_digest |

---

## 九、本次 Gap 分析结果（vs Skill Distiller）

对照 SD 的 `PROJECT_DESIGN.md` 逐模块核对后：

### 已完整移植（50/54 模块）

所有设计文档中列为核心巧思的模块已全部到位。

### 本次补移植（4 个遗漏模块）

| SD 模块 | SkillOS 位置 | 核心巧思 |
|---------|-------------|---------|
| `metaskill.py` | `skills/metaskill.py` | "卷 Harness 不卷模型"——MetaSkill 管道编排，声明式 DAG，循环检测 |
| `dispatcher.py` | `skills/dispatcher.py` | "不确定就不匹配"保守路由——宁可漏匹配也不错匹配 |
| `tool_registry.py` | `skills/tool_registry.py` | Knowledge/Tools/Skills 三层分离——删工具前能评估影响面 |
| `conversation_store.py` | `skills/conversation_store.py` | SQLite WAL 模式对话持久化——线程安全，30 天自动清理 |

### 未移植（合理省略）

| SD 模块 | 原因 |
|---------|------|
| `voice_input.py` / `asr_cloud.py` / `funasr_engine.py` / `tts_engine.py` / `tts_backends/` | Hermes 原生支持语音，无需重复 |
| `skill_server.py` | 已被 FastAPI 模块化路由替代 |
| `i18n.py` | 前端国际化，UI 重构时再做 |
| `user_store.py` | 已被 marketplace/auth.py 替代 |
| `skillhub_cli.py` | MCP 接入后 CLI 不再是主要入口 |

---

## 八、一行总结

> **SkillOS 不是 AI 工具，是 AI 技能的工厂。它创造技能、验证技能、进化技能、分发技能——然后通过 MCP 接入任何 AI 客户端去执行。Hermes 是它的引擎底座，Claude Code 是它的一个用户。**
