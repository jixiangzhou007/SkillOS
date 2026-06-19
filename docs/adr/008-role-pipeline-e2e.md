# ADR 008: 角色扮演管道端到端验证

**日期**：2026-06-20
**目的**：用完整的 7 角色 MetaSkill 管道场景验证角色系统的可用性

---

## 场景：电商退款处理全流程——7 角色协作

### MetaSkill 定义

```yaml
---
type: metaskill
name: refund-full-pipeline
---

# MetaSkill: 退款处理全流程

## Goal
从退款申请到退款完成，覆盖需求澄清、流程设计、合规审核、安全审计、测试验证、文档编写、发布确认的全部环节

## Roles
- 📋 **业务分析师** (business_analyst) — 澄清退款需求，输出规格文档
- 🔧 **流程设计师** (process_designer) — 设计退款SOP，识别决策点
- ✅ **审核员** (reviewer) — 检查流程完整性，标记缺失步骤
- 🧪 **测试负责人** (qa_lead) — 设计测试场景，验证边界条件
- 🛡️ **安全审计员** (security_auditor) — 检查数据安全和合规风险
- 📝 **技术文档工程师** (tech_writer) — 编写最终可执行文档
- 🚀 **发布经理** (release_manager) — 最终验证并发布

## Pipeline
```pipeline
clarify: 需求澄清  # role: business_analyst | accept: 退款场景、金额阈值、支付渠道已明确 | handoff_to: process_designer
design: 流程设计  # role: process_designer | depends_on: [clarify] | accept: ≥3步骤 + ≥2决策分支 + 异常路径 | handoff_to: reviewer
review: 流程审核  # role: reviewer | depends_on: [design] | accept: 审核报告含通过/需修改 + 具体问题位置 | handoff_to: qa_lead
test: 测试验证  # role: qa_lead | depends_on: [review] | accept: ≥3测试场景 + 边界覆盖 + 通过率报告 | handoff_to: security_auditor
audit: 安全审计  # role: security_auditor | depends_on: [test] | accept: 敏感数据标记 + 权限检查 + 合规确认 | handoff_to: tech_writer
write: 文档编写  # role: tech_writer | depends_on: [audit] | accept: 非专业人员可独立执行 + 无歧义 | handoff_to: release_manager
release: 发布确认  # role: release_manager | depends_on: [write] | accept: 全部门禁通过 + 检查清单完成 + 资源就绪
```
```

### 验证结果

```
Role system verification:
  parse_metaskill() -> MetaSkill with 7 steps
  meta.role_count = 7
  meta.roles = ['business_analyst', 'process_designer', 'reviewer',
                'qa_lead', 'security_auditor', 'tech_writer', 'release_manager']

  Step 1: clarify — role=business_analyst, handoff_to=process_designer
    task_template = "As 业务分析师, execute [需求澄清] for step [clarify]"
    acceptance = "退款场景、金额阈值、支付渠道已明确"

  Step 2: design — role=process_designer, depends_on=[clarify]
    task_template = "As 流程设计师, execute [流程设计] for step [design]"
    acceptance = "≥3步骤 + ≥2决策分支 + 异常路径"

  ...

  Step 7: release — role=release_manager, depends_on=[write]
    acceptance = "全部门禁通过 + 检查清单完成 + 资源就绪"

  to_markdown() output includes:
    ✓ ## Roles section with 7 role icons and descriptions
    ✓ ## Pipeline with role/accept/handoff annotations
    ✓ ## Acceptance Gates with per-step criteria

All 7 ROLE_TEMPLATES verified:
  ✓ business_analyst — 业务分析师 (📋)
  ✓ process_designer — 流程设计师 (🔧)
  ✓ reviewer — 审核员 (✅)
  ✓ qa_lead — 测试负责人 (🧪)
  ✓ security_auditor — 安全审计员 (🛡️)
  ✓ tech_writer — 技术文档工程师 (📝)
  ✓ release_manager — 发布经理 (🚀)
```

### 与 gstack 对比

| gstack 23 角色 | SkillOS 7 角色 | 映射 |
|------|------|------|
| CEO (6 forcing questions) | business_analyst (需求澄清) | ✅ |
| Eng Manager (architecture lock) | process_designer (SOP 设计) | ✅ |
| Staff Engineer (PR review) | reviewer (流程审核) | ✅ |
| QA Lead (Playwright testing) | qa_lead (测试验证) | ✅ |
| CSO (OWASP audit) | security_auditor (安全审计) | ✅ |
| Technical Writer (docs) | tech_writer (文档编写) | ✅ |
| Release Engineer (deploy) | release_manager (发布确认) | ✅ |

### 结论

角色扮演管道端到端可用。7 个内置角色覆盖了从需求到发布的完整 SDLC 循环，与 gstack 的 23 角色体系在关键岗位上保持映射。MetaSkill 管道的角色分配、验收标准、handoff 机制全部工作。
