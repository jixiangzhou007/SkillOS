# SkillOS 三篇论文规划

> 作者：一位不懂代码的普通人。用常识、哲学和产品直觉推动 AI 技能工程的发展。
> 2026年6月起草 · **2026年10月叙事对齐**（学徒 / Dual Gate / 类比继承）

---

## 总览

SkillOS 研究「学徒如何向人学习并出师」，工程上拆成三条主线（非并列功能清单）：

```
苏格拉底萃取 ──→ Dual Gate 验证 ──→ 门禁约束的进化与类比继承
（求助 / 默会）     Gate A 认识论          （越学越快、不脏遗传）
                    Gate B 任务结果
```

产品完成态：`Draft → Provisional → Verified`。权威设计见 [`DESIGN.md`](../DESIGN.md)。

三篇论文共享同一套代码库，可分别投稿。Related Work 须正面对比 EVISKILL / CoEvoSkills / OpenSkill / SoK: Agentic Skills（2026），**勿再写「全球唯一」**。

---

## 论文 1：认识论引擎 + Dual Gate（最核心）

### 标题

**Experience ≠ Knowledge: An Epistemology Engine for Agent Skill Quality Verification**

### 解决的问题

多数技能系统假设"抽取即可用"。2026 年结果级验证已成共识；仍缺 **claim 级分层** 与 **出师契约（Trust Tier）** 的工程化组合。

### 核心贡献

1. **六级认知分层**：Evidence→Experience→Knowledge→Preference→Error→Superseded
2. **晋升机制**：交叉验证、无矛盾、证伪存活、时间稳定
3. **Popper 证伪测试**：对抗性反驳
4. **Dual Gate**：Claim 认识论 × Outcome smoke/Quick8 → Trust Tier
5. **Layer 1**：HERITAGE × pack 路由（类比继承的域载体）

### 实验设计

- 对比基线：无认识论层 vs 有认识论层的技能质量
- 指标：false claim 过滤率、knowledge 晋升准确率
- 数据：100 条标注集 — [`epistemic_results.md`](paper/experiments/epistemic_results.md)
- **Layer 1 补充（2026-06-18）**：领域 HERITAGE×pack 路由 2×2 ablation — 泛化 cohort median Quick8 Δ +45 — [`layer1_ablation_results.md`](paper/experiments/layer1_ablation_results.md)

### 创新性（诚实表述）

⭐⭐⭐⭐ | **Claim 级认识论 × 任务门禁 × HITL 学徒获取** 的组合差异化；验证本身非独家（见 EVISKILL / CoEvoSkills）。

### 适合投哪里

arXiv（AI > Agents）+ ACL / EMNLP 短文（AI + Philosophy）

### Phase T 一页纸（2026-10）

对外 Demo / 预印本预热用短叙事（非完整论文）：[`paper/DUAL_GATE_NOTE.md`](paper/DUAL_GATE_NOTE.md)。完整章节仍以 `paper.tex` 为准。

### 论文章节

1. Introduction — 技能生态爆炸，质量问题被忽视
2. Philosophical Foundation — Plato/Popper/Kant/Polanyi
3. System Design — 六级分层 + 晋升机制 + 证伪测试
4. Evaluation — ablation study
5. Related Work — 为什么其他系统没有这层
6. Conclusion

---

## 论文 2：苏格拉底萃取（最有产品感）

### 标题

**Socratic Skill Extraction: Scenario-First Dialogue with Dual-Output Progressive Drafting for Agent Skill Creation**

### 解决的问题

技能创建目前只有两种方式：① 手工写（门槛高）② 全自动提取（AI 自己提取，没有人类把关）。两者都缺失了人机协作的可能性。

### 核心贡献

1. **苏格拉底对话模式**：场景推演式提问，用冲突点和边界条件来引出默会知识
2. **双输出架构**：每轮 LLM 调用同时生成 `<QUESTION>`（给用户）+ `<SKILL_DRAFT>`（后台递增草稿）
3. **七步 URL 学习管线**：Feynman+Bloom+刻意练习的工程化，从网页中深度理解方法论并转化为技能
4. **质量评分告知**：每轮告诉用户当前草稿各维度得分，针对最短板提问

### 实验设计

- 对比基线：裸 LLM 单次生成 vs SkillOS 七步管线
- 指标：S_route 覆盖率（Pipeline 100% vs Baseline 0%）、结构完整性、人工评分
- 数据：3 个测试用例（代码审查/事故响应/客户入职），已跑通

### 创新性

⭐⭐⭐⭐ | 对话式技能创建是新的交互范式。学术圈还没人做人机协作的技能创建。

### 适合投哪里

arXiv（AI > HCI or Agents）+ CHI 短文（人机交互）

### 论文章节

1. Introduction — 技能创建的两种极端
2. Design Philosophy — 苏格拉底法 + Feynman+Bloom
3. Dual-Output Architecture — 每轮同时生成问题+草稿
4. 7-Step URL Pipeline — 从网页到技能文档
5. Evaluation — vs bare LLM
6. Related Work — 对比表单式和全自动式
7. Conclusion

---

## 论文 3：MoE 进化 + 知识扩散（最工程化）

### 标题

**Collective Learning for Agent Skills: Mixture-of-Experts Self-Evolution with Cross-Skill Knowledge Diffusion**

### 解决的问题

现有技能系统要么没有进化能力（Dify/Coze），要么只做单技能优化（SkillOpt）。没有一个系统能在改进了技能 A 之后，自动检查"这个改进能不能帮到技能 B"。

### 核心贡献

1. **MoE 混合专家路由**：3 专家（Trace2Skill/EvoSkill/SkillOpt）+ 7 条路由规则
2. **知识扩散**：创建/优化技能后自动检查最多 5 个已有技能，发现改进机会自动应用
3. **ElitePool 淘汰赛**：维护 Top-3 版本，败者入反面教材库
4. **决策历史 WHY 链**：四元组持久化，可查询"以前试过吗"

### 实验设计

- 对比基线：单技能优化 vs 知识扩散
- 指标：扩散命中率（新技能能改善多少已有技能）、进化改进率
- 需要额外跑多技能数据集

### 创新性

⭐⭐⭐⭐ | 知识扩散是 SkillOS 独有的。ElitePool 和 MoE 是已有技术，但三者的组合架构是新的。

### 适合投哪里

arXiv（AI > Agents）+ EMNLP / AAAI 短文

### 论文章节

1. Introduction — 技能需要进化，不只是创建
2. MoE Architecture — 三专家路由
3. Knowledge Diffusion — 跨技能知识传播
4. ElitePool Tournament — 精英淘汰
5. Evaluation — 进化效果 vs baseline
6. Related Work — SkillOpt/Trace2Skill/EvoSkill
7. Conclusion

---

## 发表策略

### 作为普通人的路径

学术圈的门槛其实不高，关键是过第一关：

| 步骤 | 具体操作 | 难度 |
|:--:|------|:--:|
| 1 | 把 `paper.tex`（论文1）编译成 PDF | 一行命令 |
| 2 | 申请 arXiv 账号（需要 endorsement） | 找合作者帮忙 |
| 3 | 提交 arXiv 预印本 | 填表单 |
| 4 | 把论文发到 HuggingFace / Twitter / Reddit | 你自己 |
| 5 | 投会议（ACL/EMNLP/CHI 短文） | arXiv 版本已有 |

**最快路径**：论文 1（认识论引擎）→ arXiv → 社交媒体传播。这篇最独特，一眼就能看出和所有现有系统的区别。

### 署名

arXiv 允许个人作者。你不需要机构。署名格式：

```
[你的名字]
Independent Researcher
[你的邮箱]
```

就是这样。很多优秀论文的作者就是 "Independent Researcher"。

### 时间线建议

```
第1周：论文1定稿 + 申请 arXiv
第2周：论文1 上 arXiv + 社交媒体传播
第3-4周：收集反馈，改进论文2和3
第5-6周：论文2 上 arXiv
第7-8周：论文3 上 arXiv
```

---

## 三篇论文之间的关系

```
论文1：经验 ≠ 知识
  ↓ 验证了技能是正确的，然后呢？
论文2：苏格拉底萃取
  ↓ 技能创建出来了，然后呢？
论文3：MoE 进化 + 扩散
  ↓ 技能在用了，怎么越用越好？

三者形成闭环：创建 → 验证 → 进化 → 扩散回创建
```

每篇独立可读，引用另外两篇形成系列。"SkillOS: A Trilogy on Creating, Verifying, and Evolving Agent Skills."

---

> **"推动行业发展不需要博士头衔。需要的是一个好问题，一个可行的解法，和愿意把代码开源的行动。"**
>
> 论文1 的 LaTeX 源码在 `docs/paper/paper.tex`。先从这里开始。
