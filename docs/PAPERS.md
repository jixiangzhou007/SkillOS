# SkillOS 三篇论文规划

> 作者：一位不懂代码的普通人。用常识、哲学和产品直觉推动 AI 技能工程的发展。
> 2026年6月

---

## 总览

SkillOS 的三个核心创新可以拆成三篇独立论文，覆盖技能全生命周期：

```
创建 ────────────→ 验证 ────────────→ 进化
(论文2)           (论文1)            (论文3)
苏格拉底萃取       认识论引擎          MoE + 扩散
```

三篇论文共享同一套代码库（SkillOS 开源项目），但每篇解决一个独立的学术问题。可以分别投稿，也可以先发一篇再陆续发另外两篇。

---

## 论文 1：认识论引擎（最核心、最独特）

### 标题

**Experience ≠ Knowledge: An Epistemology Engine for Agent Skill Quality Verification**

### 解决的问题

目前所有 AI 技能系统（SkillOpt、EXIF、Anything2Skill、Dify、Coze）都假设"AI 提取的内容可以直接用"。没有一个系统会问："这段内容是知识还是幻觉？"

### 核心贡献

1. **六级认知分层**：将 Plato/Popper/Kant/Polanyi 哲学工程化为可运行的代码（Evidence→Experience→Knowledge→Preference→Error→Superseded）
2. **晋升机制**：Experience→Knowledge 的四条件验证（多源交叉、无矛盾、证伪存活、时间稳定）
3. **Popper 证伪测试**：让 LLM 扮演攻击者主动反驳每条声明
4. **Graphiti 时序模型**：双时间轴跟踪每段知识的有效期

### 实验设计

- 对比基线：无认识论层 vs 有认识论层的技能质量
- 指标：false claim 过滤率、knowledge 晋升准确率
- 数据：100 条标注集 — [`epistemic_results.md`](paper/experiments/epistemic_results.md)
- **Layer 1 补充（2026-06-18）**：领域 HERITAGE×pack 路由 2×2 ablation — 泛化 cohort median Quick8 Δ +45 — [`layer1_ablation_results.md`](paper/experiments/layer1_ablation_results.md)

### 创新性

⭐⭐⭐⭐⭐ | 全球唯一。没有任何学术论文或工业系统实现过认识论驱动的技能质量验证。

### 适合投哪里

arXiv（AI > Agents）+ ACL / EMNLP 短文（AI + Philosophy）

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
