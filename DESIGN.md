# SkillOS 设计书

> **写给三类读者**：AI 编程工具（理解架构贡献代码）、人类开发者（理解设计思路）、非技术决策者（理解产品价值）。
>
> **2026年10月 · 叙事重订（工程基线仍为 v0.3.x）**
> 本文档整合：学徒隐喻 · 陌生环境探索 · 跨域类比继承 · Dual Gate 双门禁。
> 工程规模与模块清单以仓库现状为准；路线执行见 [`docs/ARCH_OPTIMIZATION_PLAN.md`](docs/ARCH_OPTIMIZATION_PLAN.md)。

---

## 目录

1. [产品定位](#1-产品定位)
2. [核心设计思想](#2-核心设计思想)
3. [系统架构](#3-系统架构)
4. [模块详解](#4-模块详解)
5. [API 接口清单](#5-api-接口清单)
6. [开发者指引](#6-开发者指引)
7. [基础设施与质量](#7-基础设施与质量)
8. [竞品与相关工作](#8-竞品与相关工作)
9. [附录](#9-附录)

---

## 1. 产品定位

### 1.1 要解决的问题

Agent Skills 生态在 2025–2026 年爆发——Anthropic 推动 AgentSkills.io 开放标准，公开技能与兼容平台快速增长。**分发问题基本被解决**；真正空缺的是：

1. **技能从哪来？** 专家脑子里的默会流程，不是填表就能写清的。
2. **技能对不对？** 抽取与生成很容易；「经验」和「已验证知识」却常被混为一谈。
3. **技能能否越学越强？** 用多了会发现边界；改进能否在**门禁下**遗传到相关技能，而不是污染整个库？

多数系统（含部分物理 AI 演示）擅长在**预先给定的地图 / 点云 / 脚本**里把任务做完。人却经常要在**没有完整地图**时办事：换一栋楼、换一座城、换一张游戏图——靠观察、求助、试错，再把活下来的经验收成本事。

### 1.2 核心隐喻：AI 是学徒，不是点云执行器

> **SkillOS：让 AI 像学徒一样向人学习，把多源经验炼成适合自己调用的、可验证的 Agent Skills。**

| | 预置地图上的执行（常见 AI / 展会机器人） | 学徒式能力（SkillOS 追求） |
|--|------------------------------------------|----------------------------|
| 世界 | 事先给好的点云 / SOP / 封闭脚本 | 信息不完备的陌生任务 |
| 失败 | 出图即僵，或仅重规划 | 问人、看线索、再试 |
| 知识 | 几何与路径预先嵌入 | 经验临时生成，可修正、可晋升 |
| 成功后 | 轨迹未必变成可迁移技能 | 「下次少迷路」写进 Verified Skill |

**「给王总送资料」**：去隔壁楼 7 楼——先找楼，再找电梯，看门牌，找不到就问人，根据指示继续。
**联程出行 / 游戏开图** 是同一套底层能力：在陌生环境里推进，并把经验沉淀为策略。
SkillOS 的试验田是 **Agent Skills 域**（办公与专业流程），不是先造会坐飞机的机器人；研究的是同一套 **探索 → 出师** 协议。

### 1.3 SkillOS 的回答（黄金路径）

```
人（师傅）用对话 / 链接 / 文件传授
        ↓
    学徒 SkillOS：
    ① 苏格拉底式追问（敢问、会问边界）
    ② 双门禁验货（声明级认识论 + 任务级 bench）
    ③ 炼成 AgentSkills.io 标准技能
    ④ 受门禁的进化与跨域类比继承（越学越快，不脏遗传）
        ↓
Draft → Provisional → Verified → 安装到 Cursor / Claude Code / Codex
```

### 1.4 一句话定位

> SkillOS：在对话中把专家经验沉淀为 **可验证、可安装、可继承** 的 Agent Skills。
> 不是又一份 AI 生成的 markdown——是学徒出师后的本事。

---

## 2. 核心设计思想

三条研究主线不是并列功能清单，而是学徒能力的三个工程切片：

| 主线 | 学徒行为 | 工程含义 |
|------|----------|----------|
| **苏格拉底萃取** | 向师傅追问、澄清默会知识 | HITL 获取前端 |
| **认识论** | 分清听说 / 试过 / 已确认 | Claim 级信任 |
| **门禁约束的进化与继承** | 改招、把本事迁到新域 | Outcome 门禁 + 类比迁移 |

### 2.1 陌生环境探索协议（元能力）

送王总、坐地铁、打游戏看图——表层任务不同，认知结构同构：

```
目标 → 局部观察 → 不确定则求助 → 尝试 → 失败则修正 → 沉淀可再用策略
```

换的是环境模态；不变的是：**信息不完备时仍能推进，并把经验晋升为可迁移本事。**

SkillOS 在技能沉淀域实现该协议的第一块试验田：

- 观察 / 求助 → 苏格拉底选项与冲突题
- 尝试 / 失败 → 允许 **Provisional**，不假装已验证
- 沉淀 → 仅过门禁者写入 **Verified** 并可导出、可遗传

### 2.2 经验 ≠ 知识（认识论引擎 · Gate A）

从对话、网页、文件抽出的内容默认是 **Experience（经验）**——可能对，可能错。晋升为 **Knowledge** 须同时满足：

1. **交叉验证**：≥2 个独立来源支持
2. **无矛盾**：不与已验证知识冲突
3. **证伪存活**：对抗性反驳未成立
4. **时间稳定**：在观察期内仍然有效

六级分层：Evidence → Experience → Knowledge → Preference；另有 Error、Superseded。

理论基础：Plato（justified true belief）、Popper（证伪）、Polanyi（默会知识）。
**表述纪律（2026）**：不做「全球唯一」宣称。2026 年 EVISKILL / CoEvoSkills / OpenSkill 等已在做**结果级 / 证据级**验证；SkillOS 的差异化是 **claim 级分层 + 与 Gate B 并列的双门禁**，而非垄断「验证」一词。

### 2.3 苏格拉底对话萃取（求助通道）

默会知识填不出完整表单。用场景推演与冲突点提问：

```
❌ 表单式：这个流程有哪些步骤？
✅ 苏格拉底式：假设合同第7条把「北京仲裁」改成「上海仲裁」——
             按你的规矩，第一步做什么？风险等级是什么？
```

每轮双输出：① 给用户的问题/选项 ② 后台渐进生长的技能草稿。
获取路径：对话 · URL 七步学习 · 文件摄入——殊途同归到草稿与门禁。

### 2.4 Dual Gate 与 Trust Tier（出师仪式）

```
Socratic Draft
      ↓
┌──────── Dual Gate ────────┐
│ Gate A  Claim Epistemology │  经验能否晋升为知识
│ Gate B  Outcome Verify     │  smoke / Quick8 Δ（官方 SkillsBench 另计口径）
└────────────┬──────────────┘
             ↓
   Draft | Provisional | Verified
             ↓
   Export（Cursor 优先）
```

| 等级 | 含义 |
|------|------|
| **Draft** | 萃取中 / 结构未闭合 |
| **Provisional** | 可安装试用；门禁未双过（学徒「会一点但未出师」） |
| **Verified** | 推荐：**Gate A ∧ Gate B**；可扩散、可标为已验证遗产 |

Gate B 与 Gate A **平级**：不能只靠文案或 ✅ 列表宣布「已验证」。
本地 Quick8 是日常代理指标，**不等于**官方 BenchFlow pass rate；对外须诚实标注。

### 2.5 跨域类比继承（Skill Inheritance）

人类面对未知领域，习惯从**已知学科举例子**，按相似情况尝试——这是跨学科知识迁移，不是基因复印。

Skill 继承应长成 **Analogical Inheritance**：

| 人类 | SkillOS |
|------|---------|
| 已知学科 | 已有 Verified 技能 / 域 DNA / HERITAGE |
| 举例子 | 显式类比：源域情境 → 目标域假设 |
| 按类似情况试 | 在新任务上探查 / smoke（允许失败） |
| 不像则改 | 类比默认 Experience；过双门禁才升 Knowledge |
| 下次更快 | 只扩散「迁移后仍成立」的结构 |

**Scale 的双刃剑**：

- **红利**：库越大，可调用的源域图式越多，陌生任务探索成本越低。
- **负累**：错误经验也会被继承与扩散；库越大，污染面越大。

因此：扩散与遗传必须过认识论门控（及结果门禁）；**禁止无门禁的全库改写**。
Layer 1（HERITAGE + pack 路由）已有 ablation：泛化 cohort 中位 Quick8 Δ **+45**（heritage / pack 均有正边际）——说明「域继承」有效，且必须与路由一起设计。

### 2.6 门禁约束的进化（原 MoE 进化 · 改表述）

执行 → trace → 归因 → 候选修订 → **验证门** → 新版本。

三种策略（实现上仍可路由，叙事上统称「受门禁的进化」）：

| 策略 | 适用 | 方法 |
|------|------|------|
| Trace2Skill | 新技能、失败轨迹多 | 批量诊断 + 合并 |
| EvoSkill | 分数不稳 | 多候选 + 淘汰 |
| SkillOpt | 成熟技能 | 小步精准编辑 |

**研究主张**：值得研究的是「何种编辑在门禁下稳定提分且可安全扩散」；MoE 是可选实现，不是成立前提。
与 Microsoft SkillOpt 等互补：对方强在优化训练环，SkillOS 强在 **获取 + claim 认识论 + 可安装交付**。

### 2.7 技能多态（求同存异）

同一问题不同角色可有不同解法：

- **求同**：Skill DNA（必须遵守的核心原则）
- **存异**：@Override 标明差异步骤
- **竞争**：执行与 bench 数据决定保留哪一变体

### 2.8 AgentSkills.io 与渐进披露

- 输出兼容 `SKILL.md`（YAML frontmatter + Markdown）
- Context engineering：主文件是导航；references / scripts 按需加载
- Description 是路由规则；Gotchas（隐性坑）优先于常识复述
- Injection（`skill_injection_payload`）优先 S_body / 应答速查 / S_route，控制 token

### 2.9 评估维度（SkillsBench 对齐）

| 维度 | 问题 |
|------|------|
| 边界 | 触发与排除是否清晰？ |
| 过程 | 是否有检查点与中间格式？ |
| 增益 | 相对无 skill 基线是否稳定提升？ |
| 稳定性 | 换模型 / 环境是否仍有效？ |
| 成本 | 上下文与维护成本是否值得？ |

---

## 3. 系统架构

### 3.1 逻辑视图（学徒协议）

```
┌────────────────── Product Surface ──────────────────┐
│ Workspace（对话/链接/文件）· Trust Tier 结果卡        │
│ Export Channel（Cursor / Zip / SKILL.md）           │
└─────────────────────┬───────────────────────────────┘
                      │ precipitation / dispatch
┌─────────────────────▼───────────────────────────────┐
│ Extraction Core                                      │
│ Socratic Agent · URL 七步 · 文件摄入 · 类比提示       │
└─────────────┬─────────────────────┬─────────────────┘
              │                     │
┌─────────────▼─────────┐ ┌─────────▼─────────────────┐
│ Epistemic Kernel      │ │ Outcome Kernel              │
│ classify / falsify    │ │ smoke · Quick8 · pack sync  │
│ promote / lineage     │ │ Δ 门禁 · domain packs       │
└─────────────┬─────────┘ └─────────┬─────────────────┘
              └──────────┬──────────┘
┌────────────────────────▼────────────────────────────┐
│ Skill Artifact（SKILL.md · DNA · heritage · meta）   │
│ trust_tier · bench_quality · epistemic YAML          │
│ Analogical inheritance / gated diffusion             │
└─────────────────────────────────────────────────────┘
```

### 3.2 接入与分层（实现视图）

```
┌─────────────────────────────────────────────────────────────┐
│ 接入层：Web (Alpine.js) · MCP · 桌面 · IM (Hermes)           │
├─────────────────────────────────────────────────────────────┤
│ 智能体层：SkillAgent · learn_from_url · Dispatcher           │
├─────────────────────────────────────────────────────────────┤
│ Dual Gate：认识论引擎 + Outcome（save_gate / Quick8）         │
├─────────────────────────────────────────────────────────────┤
│ 知识层：图谱 · 血缘 · DNA · Playbook · 记忆                   │
├─────────────────────────────────────────────────────────────┤
│ 进化层：门禁约束优化（SkillOpt/EvoSkill/Trace2Skill）· 扩散   │
├─────────────────────────────────────────────────────────────┤
│ 存储：skills/ · knowledge/ · data/ · configs/reference_*    │
└─────────────────────────────────────────────────────────────┘
```

**依赖纪律**：`api` → `skills` / `knowledge` / `evaluation` → `llm_client`；禁止绕过 Epistemic / Outcome kernel 写入 Verified。

### 3.3 文件组织

```
skillos/
  api/           — REST
  skills/        — 萃取、存储、调度、变体、DNA、cold_start、domain_pack
  knowledge/     — 认识论、图谱、血缘、消化、记忆
  evolution/     — 进化引擎、优化器、学习理论、SkillOpt 导出
  evaluation/    — save_gate、ablation、MoE 评价
  marketplace/ · identity/ · security/ · channels/ · billing/ …
  official_skillsbench/ — 官方 CI 集成
  mcp_server.py · llm_client.py · config.py · db.py
frontend/        — Alpine.js + vanilla JS（Verified 结果卡、知识透镜）
configs/reference_domain_packs/ — 可版本化 reference pack 快照
skills/          — AgentSkills.io 技能文档
docs/            — ARCH_OPTIMIZATION_PLAN · BENCHMARK_LOCAL · PAPERS …
```

运行时 `data/domain_packs/` 可被 gitignore；权威快照以 `configs/` 为准，回归前 `scripts/repair_reference_packs.py` 同步。

---

## 4. 模块详解

### 4.1 知识质量控制层（Gate A 与血缘）

| 模块 | 一句话 | 核心机制 |
|------|------|------|
| `knowledge/epistemology.py` | 这段话是经验还是可晋升知识？ | 分层 + `promote_to_knowledge` + 证伪 |
| `knowledge/graph.py` | 知识关联 | 关系类型、权重、聚类 |
| `knowledge/lineage.py` | 从哪来、如何处理 | 来源→提取→引用→状态（已拆子模块） |
| `knowledge/deep_digest.py` | 文章→结构化知识包 | 扫描→论点→术语→模式→速查 |
| `knowledge/playbook.py` | 团队共享背景 | PLAYBOOK.md 约束输出 |
| `knowledge/memory.py` | 双层记忆 | 全局洞察 + 按技能记忆 |
| `knowledge/extractor.py` | 文本抽知识 | 来源权威权重 |
| `knowledge/skill_kb.py` | 技能私有 KB | 可跨技能分享 |
| `knowledge/refresher.py` | 源变更检测 | SHA256 → 再消化 |
| `knowledge/taxonomy.py` | 领域 / 方法论 | 域决定标准，方法决定思考方式 |
| `knowledge/skill_routing.py` | 技能↔任务路由 | bench_categories、injection、overlap |
| `knowledge/ingestion_queue.py` | 摄入队列 | 磁盘队列 + 重启恢复 |

### 4.2 技能引擎（获取与继承载体）

| 模块 | 一句话 | 关键设计 |
|------|------|------|
| `skills/agent.py` | 萃取大脑 | 苏格拉底双输出、URL 管线、扩散入口 |
| `skills/skill_store.py` | CRUD | 版本归档、安全扫描、变体检测 |
| `skills/dispatcher.py` | 意图路由 | 不确定则不硬匹配 |
| `skills/pattern_miner.py` | DNA 挖掘 | 结构原型→成功因子→反模式→原则 |
| `skills/variants.py` | 多态 | Archetype + Variant + @Override |
| `skills/cold_start.py` | Path B 冷启动 | rubric → HERITAGE → 复测 |
| `skills/domain_pack.py` | 域 pack | 应答速查 + pack-scoped inject（类比继承的域载体） |
| `skills/domain_templates.py` | 域模板 | 骨架与关键词 |
| `skills/session_manager.py` | 会话 | 过期与持久化 |
| `skills/bench_cohorts.py` | 回归 cohort | reference / generalize 门槛 |

### 4.3 进化引擎（Gate 后修订）

| 模块 | 一句话 | 核心机制 |
|------|------|------|
| `evolution/skillopt*` | 优化核心 | 路由 + 精英池 + 审计 + 编辑预算（已拆分） |
| `evolution/skillhone.py` | 决策与回滚 | WHY 链、定向回滚 |
| `evolution/engine.py` / `evolver.py` | 触发与执行 | 轨迹→实质性改进判断 |
| `evolution/learning_theory.py` | 学习理论 | 遗忘曲线、费曼、**类比迁移** |
| `evolution/skillopt_export.py` | 外部 SkillOpt 导出 | best_skill + traces + manifest |

### 4.4 Outcome Kernel（Gate B）

| 模块 | 一句话 |
|------|------|
| `evaluation/save_gate.py` | 保存前域内 smoke；未过则不得冒充 Verified |
| `benchmark_local.py` | Quick8 选题、对比、摘要 |
| `skillsbench_tasks.py` | 任务集与 `run_task_evaluation` |
| `evaluation/ablation.py` | HERITAGE × pack 2×2 |
| `scripts/run_bench_regression.py` | 参考 + 泛化 + smoke；跑前 sync reference packs |
| `scripts/repair_reference_packs.py` | `configs/` → `data/domain_packs/` |

### 4.5 前端（验货控制台）

| 职责 | 主要文件 |
|------|----------|
| 三路径沉淀 + 顶栏 | `workspace.js` |
| 对话 / 草稿 | `chat.js` · `socratic-ui.js` |
| Verified 结果卡 | `precipitation-result.js` |
| Cursor 导出引导 | `export-channel.js` |
| 知识透镜 | `knowledge.js` |
| 设计系统 | `style.css` · `index.html` |

产品完成态应对齐 Trust Tier：**Draft / Provisional / Verified**（见架构优化计划 Phase V）。

### 4.6 API / 工具 / 身份（摘要）

- **核心**：`POST /api/skills/dispatch`（对话/URL/文件路由）、finalize、ingest、export
- **知识**：lineage / graph / review / cycle
- **进化**：optimize / export-skillopt
- **评测**：`api/bench_official.py`
- **MCP**：`mcp_server.py`
- **身份与安全**：`identity/` · `security/` · JWT / 租户隔离

详细路由表见下文 §5；认证模式见 §6.5。

---

## 5. API 接口清单

### 5.1 核心端点

| 路由 | 方法 | 说明 | 认证 |
|------|:--:|------|:--:|
| `/api/skills/` | GET | 列出技能 | optional |
| `/api/skills/{name}` | GET / DELETE | 详情 / 删除 | DELETE required |
| `/api/skills/dispatch` | POST | **核心**自动路由 | optional |
| `/api/skills/dispatch/stream` | POST | 流式 dispatch | optional |
| `/api/skills/create` | POST | 从文本创建 | optional |
| `/api/skills/finalize` | POST | 完成萃取 | optional |
| `/api/skills/ingest` | POST | 文件上传 | optional |
| `/api/skills/resume` | POST | 恢复会话 | optional |
| `/api/skills/{name}/export` | GET | 导出 | optional |
| `/api/skills/{name}/dna-lineage` | GET | DNA 血缘 | optional |
| `/api/knowledge/*` | GET/POST | 知识/血缘/图谱/审核/cycle | 见实现 |
| `/api/evolution/{name}/optimize` | POST | 触发优化 | required |
| `/api/evolution/{name}/export-skillopt` | POST | SkillOpt 导出 | required |
| `/api/marketplace/*` | — | 目录/发布/订阅（非当前主航道） | — |
| `/api/auth/*` | — | 登录注册 OAuth | public / JWT |
| `/api/bench/*` | — | 官方/本地评测相关 | 见实现 |

### 5.2 Dispatch 路由逻辑

```
用户消息
  ├─ 含 URL？ → 抓取 → 方法论（七步）/ 概念（digest）
  ├─ 萃取意图？ → 苏格拉底对话（问题 + 草稿）
  ├─ Playbook？ → 冷启动访谈
  └─ 其他 → 普通对话
```

完成后应进入 Dual Gate，再标注 Trust Tier（产品契约演进中）。

---

## 6. 开发者指引

### 6.1 环境搭建

```bash
pip install -e ".[all]"
# .env 中配置 DEEPSEEK_API_KEY（可选；无 key 时可走 Ollama）
skillos --server-only          # 默认 API 见 README
python -m skillos.mcp_server   # MCP
```

### 6.2 代码约定

```python
from skillos.config import get_config
from skillos.skills.skill_store import save_skill
from skillos.llm_client import call

cfg = get_config()
reply = call("prompt", max_tokens=600, temperature=0.2)
```

使用 `skillos.*` 包路径；禁止裸 `except: pass`。

### 6.3 设计约束（不可破坏）

| 规则 | 原因 |
|------|------|
| **Skill 兼容 AgentSkills.io** | `---\nYAML\n---\nMarkdown`，含 `name` |
| **不得绕过认识论写 Knowledge** | 声明走 `record_claim` / 晋升路径 |
| **不得绕过 Outcome 冒充 Verified** | save_gate / smoke / 回归门槛 |
| **扩散须过认识论门控** | 含 ERROR 或全 pending 不得自动改写他技 |
| **异常必须打日志** | 至少 `_log.debug` / `_log.warning` |
| **API 返回真实数据** | 禁止硬编码空桩 |
| **单向依赖** | 禁止底层反向依赖 api |
| **安全扫描** | `save_skill` 入口危险模式检测 |

### 6.4 常见修改场景

| 场景 | 位置 | 注意 |
|------|------|------|
| 萃取对话 | `skills/agent.py` | Phase 状态机、双输出 |
| URL 学习 | agent 学习管线 | 步骤顺序与 token 预算 |
| 路由 / 注入 | `knowledge/skill_routing.py` | overlap 与 pack 作用域 |
| 域继承 | `domain_pack` + `configs/reference_*` | 改 pack 后跑回归 |
| 门禁 | `evaluation/save_gate.py` | 与 Trust Tier 语义一致 |
| 前端完成态 | `precipitation-result.js` | Draft/Provisional/Verified |

### 6.5 认证模式

可选认证：`get_optional_auth`；写操作优先 `require_auth`。租户数据按 `tenant_id` 过滤。

### 6.6 AI 协作

遵守 [`AGENTS.md`](AGENTS.md)：改代码前读 `docs/AI_DEV_LOG.md` 最新条，改后追加。
Claude Code hooks / skills 见 `.claude/`。

---

## 7. 基础设施与质量

### 7.1 测试与 CI

```bash
python -m pytest tests/ -v
python scripts/run_bench_regression.py   # 需 DEEPSEEK_API_KEY；先 sync reference packs
```

GitHub Actions：lint → 核心环 → knowledge → bench gates → 全量测试（见 `.github/workflows/`）。

### 7.2 SkillsBench 口径

| 口径 | 用途 |
|------|------|
| 本地 Quick8 + smoke | 日常回归、门禁、ablation |
| 官方 SkillsBench / Linux CI | 对外权威数字 |

文档：[`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) · [`docs/SKILLSBENCH_CI.md`](docs/SKILLSBENCH_CI.md)。

### 7.3 安全

JWT、租户隔离、参数化 SQL、SSRF/路径限制、技能危险模式扫描、脱敏。

---

## 8. 竞品与相关工作

### 8.1 学术（2025–2026 对齐表述）

| 工作 | 做了什么 | 与 SkillOS |
|------|----------|------------|
| EVISKILL | 可回放证据驱动技能修订 | 同轴；我们另有 claim 分层与 HITL |
| CoEvoSkills | 生成器 + Surrogate Verifier | Outcome 门禁同族；我们强调学徒获取 |
| OpenSkill / VeriSkill | 开放世界自进化 / 验证技能 | 进化同题；我们绑双门禁与可安装标准 |
| SoK: Agentic Skills | 技能生命周期与信任/安全 | Trust Tier、反脏遗传与之对齐 |
| Anything2Skill | 外部知识→技能合约 | 覆盖部分路径；缺苏格拉底默会萃取 |
| SkillOpt (MSR) | 文本学习率 + 验证门优化 | 互补导出已支持 |
| SkillFlow 等 | 检索 skill | 检索≠验证；我们做验货与出师 |

### 8.2 工业

| 平台 | 创建 | 验证 | 进化 | 标准输出 |
|------|:--:|:--:|:--:|:--:|
| Dify / Coze | 表单/拖拽 | 弱 | 弱 | 平台锁 |
| 纯 Agent 编排 | 代码 | 自定 | 少 | 非 Skills 标准 |
| **SkillOS** | **苏格拉底学徒** | **Dual Gate** | **门禁进化+类比继承** | **AgentSkills.io** |

### 8.3 我们主张的差异化（诚实版）

1. **学徒协议**：向人学习 → 探索式澄清 → 出师（Verified），而非预置地图执行。
2. **Dual Gate**：claim 认识论 × 任务结果，Trust Tier 可见。
3. **Analogical Inheritance**：跨域类比迁移 + scale 负累滤网（门控扩散）。
4. **标准交付**：可安装 SKILL.md，Cursor/Claude 优先通道。

不主张：已具备通用具身导航；不主张垄断「验证」或「进化」概念。

---

## 9. 附录

### 9.1 版本与叙事

| 标记 | 日期 | 说明 |
|------|------|------|
| v0.3.0–v0.3.5 | 2026-06 | 认识论主链路、前端 M0–M5、bench 修复、工程治理 |
| 设计书叙事重订 | 2026-10 | 学徒 / 探索 / 类比继承 / Dual Gate；工程实现按 Phase V 演进 |

版本细节：[`CHANGELOG.md`](CHANGELOG.md)。协作过程：[`docs/AI_DEV_LOG.md`](docs/AI_DEV_LOG.md)。

### 9.2 相关文档

| 文档 | 用途 |
|------|------|
| [`docs/ARCH_OPTIMIZATION_PLAN.md`](docs/ARCH_OPTIMIZATION_PLAN.md) | **当前架构优化与 Phase V/T 冲刺** |
| [`AGENTS.md`](AGENTS.md) | AI 协作强制协议 |
| [`docs/IMPROVEMENT_PLAN.md`](docs/IMPROVEMENT_PLAN.md) | Phase 0–7 历史路线 |
| [`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md) | 本地 bench |
| [`docs/PAPERS.md`](docs/PAPERS.md) | 论文规划（须随 Related Work 改写） |
| [`docs/paper/paper.tex`](docs/paper/paper.tex) | 认识论论文草稿 |
| [`docs/paper/experiments/layer1_ablation_results.md`](docs/paper/experiments/layer1_ablation_results.md) | Layer 1 数据 |

### 9.3 给实现者的优先级提醒

1. **先稳黄金路径**：对话 → Dual Gate → Trust Tier → 导出。
2. **再强化继承**：类比假设可见 + 门控扩散。
3. **MoE / 市场 / 多通道**：不阻塞主叙事时再开。

---

> **机器人用点云保证「这次接水成功」；
> SkillOS 让学徒在陌生任务里向人学习，并把活下来的经验炼成可验证的技能——
> 这样换一栋楼、换一个域，不必重新发一整张地图。**

本设计书取代此前「兵工厂 + 三创新并列 + 全球唯一认识论」的主叙事；模块与 API 细节随仓库演进，以代码与 `AI_DEV_LOG` 为准。
