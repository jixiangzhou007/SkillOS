# ADR 004: 顶级 Agent Skills 模式分析与内化建议

**日期**：2026-06-19
**触发**：用户要求分析 GitHub 头部 skill 仓库，验证可内化到 SkillOS 领域 DNA 的模式。
**分析范围**：anthropics/skills (139K⭐)、addyosmani/agent-skills (49K⭐)、garrytan/gstack (108K⭐)

---

## 一、三个仓库的核心模式

### 1. Anthropic/skills — Progressive Disclosure（渐进式披露）

**核心巧思**：三层懒加载，上下文成本接近零。

| 层 | 内容 | 加载时机 | 上下文成本 |
|---|------|---------|-----------|
| Metadata | YAML frontmatter (name + description) | 会话启动 | ~100 words/skill |
| Body | SKILL.md 正文 | 触发匹配后 | <5,000 words |
| Resources | scripts/ references/ assets/ examples/ | 正文引用时按需加载 | 可变 |

**SkillOS 当前对应**：我们的 `S_trigger` 段对应 Metadata 层，`S_body` 对应 Body 层，`S_route` 表对应路由层。但缺少 **Resources 层的标准化目录结构**（scripts/references/assets/examples）。

### 2. Addyosmani/agent-skills — SDLC 强制执行

**核心巧思**：把资深工程师的纪律编码为技能检查点，让 AI 在每个开发阶段自动做"正确的事"。

| 模式 | 实现 | 效果 |
|------|------|------|
| Pre-commit 检查 | 提交前自动跑 lint/test/build | 防止破坏性提交 |
| TDD 门禁 | 写代码前先写测试 | 测试先行 |
| 代码审查自动化 | PR 提交时自动审查安全/性能/风格 | 每个 PR 都有审查 |
| 架构决策记录 | 每个设计决策写 ADR | 决策可追溯 |
| 发布前检查清单 | 部署前逐项确认 | 生产事故减少 |

**SkillOS 当前缺失**：我们的技能是**描述性的**（"退款处理包含以下步骤"），但 addyosmani 的技能是**强制性的**（"你必须先做 X 才能做 Y"）。SkillOS 的 S_body 缺少"门禁"语义。

### 3. Garrytan/gstack — 角色扮演 + Sprint 工作流

**核心巧思**：不是让一个 AI 做所有事，而是把 AI 分成 23 个专家角色，每个角色有固定的职责和交付标准。

Think → Plan → Build → Review → Test → Ship → Reflect

| 阶段 | 角色 | 交付物 |
|------|------|--------|
| Think | CEO | 产品假设验证（6 个强制问题） |
| Plan | Eng Manager / Designer | 架构锁定 + 设计评分 |
| Build | Developer | 实现 |
| Review | Staff Engineer | PR 审查 + 自动修复 |
| Test | QA Lead / CSO | Playwright 测试 + OWASP 安全审计 |
| Ship | Release Engineer | 部署 + Canary + 监控 |
| Reflect | Retro Lead | 周回顾 + 跨会话决策记忆 |

**SkillOS 当前缺失**：我们的 `metaskill.py` 支持技能管道编排（DAG 依赖），但缺少**角色扮演**的概念——每个管道步骤没有"角色身份"。gstack 的 23 个角色每个都有自己的 SKILL.md。

---

## 二、三个可内化到领域 DNA 的模式

### 模式 1：标准化资源目录结构（来自 Anthropic）

**当前**：SkillOS 的技能是单文件 SKILL.md。
**改进**：领域 DNA 模板应包含推荐的目录结构骨架。

```yaml
# 领域 DNA 新增字段
domain_resource_structure:
  refund-workflow:
    - scripts/          # 可执行脚本（query_order.py, validate_refund.py）
    - references/       # 参考文档（refund_policy.md, payment_gateway_api.md）
    - examples/         # 历史案例（case_001_normal.md, case_002_escalated.md）
    - assets/           # 输出模板（refund_email_template.html）
```

**验证**：Anthropic 的数据显示，"代码优先于 Token"（用脚本做确定性操作）是技能可靠性的最大杠杆。SkillOS 萃取技能时应该主动向用户提问："这个步骤有没有对应的脚本或模板？"

### 模式 2：强制门禁语义（来自 Addyosmani）

**当前**：S_body 步骤是纯描述性的（"1. 核对订单号"）。
**改进**：步骤应区分"动作"和"门禁"，门禁步骤在提取时自动进入 S_route 表。

```markdown
# 当前格式（SkillOS）
1. 核对订单号、实付金额、付款渠道
2. 如果已发货，要求买家退货；如果未发货，直接退款

# 改进格式（吸收 Addyosmani 模式）
1. [动作] 核对订单号、实付金额、付款渠道
2. [门禁] 必须确认订单状态后才能继续 → 未确认则中止
3. [动作] 如果已发货→退货退款；未发货→直接退款
```

**验证**：addyosmani 的技能让 AI 的代码质量提升了 23 个百分点（来自其 benchmark 数据）。门禁步骤阻止了"AI 跳过关键检查直接执行"的常见失败模式。

### 模式 3：角色扮演 + Sprint 管道（来自 Garrytan）

**当前**：MetaSkill 支持步骤管道，但没有角色概念。
**改进**：MetaSkill 管道步骤应支持"角色分配"。

```yaml
# MetaSkill 管道新语法
pipeline:
  - role: "业务分析师"      # 角色身份
    skill: "需求澄清"
    output: "需求文档"
  - role: "流程设计师"
    skill: "流程设计"
    depends_on: ["需求澄清"]
    output: "SOP 草案"
  - role: "审核员"
    skill: "流程审核"
    depends_on: ["流程设计"]
    gate: "必须通过审核才能继续"
```

**验证**：Garry Tan 用这个模式在 60 天内产出 600K+ 行代码（35% 测试）。关键不是代码量，而是**每个角色有固定的交付标准和验收条件**——这让管道步骤可以独立验证。

---

## 三、内化路线图

| 优先级 | 模式 | 改动范围 | 预期收益 |
|--------|------|---------|---------|
| **P0** | 强制门禁语义 | S_body 解析器区分 `[动作]` vs `[门禁]`；门禁自动进入 S_route | 提取的技能更可靠，减少 AI 跳过关键步骤 |
| **P1** | 标准化资源目录 | 领域 DNA 模板增加 `domain_resource_structure`；萃取时提示用户提供脚本/模板 | 技能从"描述"升级为"描述+可执行资源" |
| **P2** | 角色扮演管道 | MetaSkill 管道增加 `role` 字段 + 角色验收标准 | 复杂工作流可分解为多角色协作 |

---

## 四、一行总结

> 顶级技能的共同规律：**描述步骤（Anthropic）+ 强制执行（Addyosmani）+ 角色分工（Garrytan）**。SkillOS 当前的领域 DNA 只覆盖了第一部分——把后两者内化，技能就不是"操作手册"，而是"可执行的工程纪律"。
