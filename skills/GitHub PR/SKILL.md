---
name: GitHub PR
created_at: '2026-06-16T04:20:53Z'
updated_at: '2026-06-16T04:20:53Z'
description: Handles GitHub PR workflows with clear step-by-step instructions. Use
  when the user mentions GitHub PR or related tasks.
portable_slug: github-pr
draft: false
epistemic:
  source: session:user-sim-prreview-retry-1781583588
  source_type: conversation
  total_claims: 37
  verified: 29
  pending: 8
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781583653_2bab9c
  - ec_1781583654_9b26c2
  - ec_1781583655_c4715a
  - ec_1781583656_ee3910
  - ec_1781583657_571692
  - ec_1781583658_67c042
  - ec_1781583659_8fdd5b
  - ec_1781583660_d99611
  - ec_1781583661_9c259d
  - ec_1781583662_788336
  - ec_1781583664_62f561
  - ec_1781583664_c83282
  - ec_1781583665_c6129f
  - ec_1781583666_8aa4e9
  - ec_1781583667_321081
  - ec_1781583668_463d52
  - ec_1781583669_0e5a49
  - ec_1781583670_0b92af
  - ec_1781583671_1d1bf0
  - ec_1781583672_680b14
  - ec_1781583673_c2397d
  - ec_1781583674_927247
  - ec_1781583674_e49577
  - ec_1781583675_83bdfe
  - ec_1781583675_8e5a7f
  - ec_1781583676_99a672
  - ec_1781583677_6437ba
  - ec_1781583678_9409e8
  - ec_1781583679_1602fd
  - ec_1781583680_bf0e1d
  - ec_1781583681_401242
  - ec_1781583681_24b500
  - ec_1781583682_78ce9d
  - ec_1781583682_bd39f4
  - ec_1781583684_52c5f5
  - ec_1781583684_283cff
  - ec_1781583685_94fb72
  pending_ids:
  - ec_1781583659_8fdd5b
  - ec_1781583670_0b92af
  - ec_1781583671_1d1bf0
  - ec_1781583674_e49577
  - ec_1781583675_8e5a7f
  - ec_1781583681_24b500
  - ec_1781583682_78ce9d
  - ec_1781583684_283cff
  processed_at: 1781583688.276717
version: 1
bench_categories:
- api-design
- code-review
- documentation
domain: computer-science
domain_label: 计算机科学
methodology: engineering
methodology_label: 工程方法论
dna_lineage:
  philosophical:
  - id: reductionist
    weight: 0.48
  - id: ooda
    weight: 0.24
  - id: scientific-method
    weight: 0.16
  domain:
  - id: code-review-pr
    version: 1.0.0
    weight: 0.55
    primary: true
  - id: science-experiment-design
    version: 1.0.0
    weight: 0.27
    primary: false
  - id: design-ui-review
    version: 1.0.0
    weight: 0.18
    primary: false
  detected_at: '2026-06-16T14:37:43Z'
  conflicts:
  - 'PDCA(标准化渐进) vs OODA(快速适应): 两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。'
  domain_key: computer-science
philosophical_dna: reductionist
---

# GitHub PR

## 核心问题
确保 GitHub PR 的代码变更安全、规范、可维护，并符合团队质量标准

## When to use
- keywords: PR review, 代码审查, GitHub PR, pull request review, 审查代码
- context: 收到 PR review 请求时，需要审查代码变更
- excludes: Draft PR、带有 WIP 标签的 PR、机器人自动发起的 PR

## Instructions
Follow these steps in order. Ask the user if anything is marked [待确认].

1. 收到 PR review 请求时，检查 PR 标题是否清晰概括变更目的，描述是否说明动机（Why，如关联 Issue、Bug 修复、功能需求）
2. 检查 PR 描述是否说明变更内容（What，核心逻辑变化、新增/删除文件）和验证方式（How，自测步骤、性能对比、测试覆盖情况）
   - 若描述缺失动机或验证方式，标记为“信息不完整”（中风险），要求补充
3. 检查实际修改的文件列表是否与描述匹配，是否包含未声明的“顺便修改”
   - 若未声明但可能影响系统行为（如改配置、加依赖、改数据库结构）→ 高风险，必须说明理由
   - 若未声明但属于无害调整（如格式化、改注释）→ 低风险，仅标注
4. 检查 diff 规模：超过 500 行 → 建议拆分 PR，要求作者说明为何无法拆分；小于 500 行但涉及多个不相关模块 → 建议按功能拆分
5. 逐行审查代码逻辑：
   - 检查 SQL 注入风险（如拼接字符串构造 SQL）
   - 检查硬编码密钥、Token、密码
   - 检查 null 指针风险（如未判空直接调用 .equals()）
   - 检查异常处理（如 catch 后吞掉异常、未记录日志）
   - [待确认] 检查循环性能、递归深度、资源泄漏
   - [待确认] 检查日志泄露敏感信息（如打印密码、Token）
   - [待确认] 检查 Magic Number / 硬编码常量
   - [待确认] 检查线程安全问题
   - [待确认] 检查过时 API 使用
6. 检查测试覆盖：新增功能是否有对应单元测试/集成测试，修复 Bug 是否有回归测试，测试是否覆盖边界条件
   - 无测试覆盖的高风险变更 → 必须补充测试
   - 已有测试但覆盖不全 → 建议补充边界用例
7. [待确认] 检查 CI 是否全部通过（绿色），若 CI 失败列出失败 Job 及日志摘要，检查代码覆盖率变化
8. 输出审查评论：使用 suggestion 风格提建议，仅当存在阻塞性问题（如安全漏洞、数据丢失风险、功能破坏）时使用 request changes
9. 批准条件：所有阻塞性问题已解决或明确答复，CI 全部通过（绿色），无未解决的 request changes

## Decision routes
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| PR 描述缺失动机或验证方式 | 标记为“信息不完整”（中风险），要求补充 | 影响可理解性和可维护性 |
| 包含未声明且影响系统行为的修改（改配置、加依赖、改数据库结构） | 标记为高风险，要求说明理由 | 可能引入未预期的副作用 |
| diff 超过 500 行 | 建议拆分 PR，要求说明为何无法拆分 | 大 diff 难以全面审查 |
| 发现 SQL 注入、硬编码密钥、null 指针、异常被吞 | 使用 request changes 标记为阻塞性问题 | 安全或稳定性风险 |
| 高风险变更无测试覆盖 | 必须补充测试，使用 request changes | 无法验证变更正确性 |
| CI 未全部通过 | 暂缓批准，列出失败 Job 及日志摘要 | 确保代码质量 |
| 所有检查通过且 CI 全绿 | 批准 PR | 满足合并条件 |

## Inputs
- pr_url: string, 无默认值, PR 的 GitHub URL
- diff_threshold: number, 500, diff 行数阈值，超过此值建议拆分
- ci_required: boolean, true, 是否要求 CI 全部通过才能批准
- test_required: boolean, true, 是否要求高风险变更必须有测试覆盖

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: PR review, 代码审查, GitHub PR, pull request review, 审查代码
- ✅ context: 收到 PR review 请求时，需要审查代码变更
- ✅ excludes: Draft PR、带有 WIP 标签的 PR、机器人自动发起的 PR
- ✅ 收到 PR review 请求时，检查 PR 标题是否清晰概括变更目的，描述是否说明动机（Why，如关联 Issue、Bug 修复、功能需求）
- ✅ 检查 PR 描述是否说明变更内容（What，核心逻辑变化、新增/删除文件）和验证方式（How，自测步骤、性能对比、测试覆盖情况）
- ✅ 若描述缺失动机或验证方式，标记为“信息不完整”（中风险），要求补充
- ✅ 若未声明但可能影响系统行为（如改配置、加依赖、改数据库结构）→ 高风险，必须说明理由
- ✅ 若未声明但属于无害调整（如格式化、改注释）→ 低风险，仅标注
- ✅ 检查 diff 规模：超过 500 行 → 建议拆分 PR，要求作者说明为何无法拆分；小于 500 行但涉及多个不相关模块 → 建议按功能拆分
- ✅ 检查 SQL 注入风险（如拼接字符串构造 SQL）
- ✅ 检查硬编码密钥、Token、密码
- ✅ 检查 null 指针风险（如未判空直接调用 .equals()）
- ✅ 检查异常处理（如 catch 后吞掉异常、未记录日志）
- ✅ [待确认] 检查循环性能、递归深度、资源泄漏
- ✅ [待确认] 检查日志泄露敏感信息（如打印密码、Token）

### 待确认
- 📋 [evidence] 检查实际修改的文件列表是否与描述匹配，是否包含未声明的“顺便修改” (`ec_1781583659_8fdd5b`)
- ⏳ [待验证] [待确认] 检查线程安全问题 (`ec_1781583670_0b92af`)
- ⏳ [待验证] [待确认] 检查过时 API 使用 (`ec_1781583671_1d1bf0`)
- 📋 [evidence] [待确认] 检查 CI 是否全部通过（绿色），若 CI 失败列出失败 Job 及日志摘要，检查代码覆盖率变化 (`ec_1781583674_e49577`)
- 📋 [evidence] 批准条件：所有阻塞性问题已解决或明确答复，CI 全部通过（绿色），无未解决的 request changes (`ec_1781583675_8e5a7f`)
- 📋 [evidence] CI 未全部通过 → 暂缓批准，列出失败 Job 及日志摘要 (`ec_1781583681_24b500`)
- 📋 [evidence] 所有检查通过且 CI 全绿 → 批准 PR (`ec_1781583682_78ce9d`)
- 📋 [evidence] ci_required: boolean, true, 是否要求 CI 全部通过才能批准 (`ec_1781583684_283cff`)
