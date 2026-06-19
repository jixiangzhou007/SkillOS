---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-18T17:33:56Z'
description: 审核销售合同中的关键条款（价格、质保、责任、知识产权、违约金），识别风险并给出修改建议。
portable_slug: skill-aecb7055
draft: false
domain: law
domain_label: 法学
philosophical_dna: pdca
philosophical_dna_label: PDCA 循环
methodology: business-process
methodology_label: PDCA 循环
dna_lineage:
  philosophical:
  - id: pdca
    weight: 1.0
  domain:
  - id: law-contract-review
    version: 1.5.0
    weight: 0.71
    primary: true
  - id: code-review-pr
    version: 1.4.0
    weight: 0.14
    primary: false
  - id: design-ui-review
    version: 1.0.0
    weight: 0.14
    primary: false
  detected_at: '2026-06-18T17:33:56Z'
  domain_key: law
  conflicts:
  - 代码审查 vs UI 设计评审：请确认评审对象是代码变更还是设计稿。
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1781804036
  dna_compliance:
    before: 5/6
    after: 5/6
    passed: 5
    total: 6
    all_passed: false
  save_gate:
    gate_enabled: true
    domain_smoke_suite:
    - &id001
      task_id: workflow-080
      category: workflow
      without_score: 100
      with_score: 100
      max_score: 100
      passed: true
      delta: 0
    domain_smoke: *id001
  moe:
    overall_score: 85
    passed: true
    confidence: 0.7
    dimensions:
      structure: 92
      security: 100
      params: 88
      routing: 60
      content: 88
      brevity: 78
    boost_rounds:
    - boosted: true
      expert_key: params
      before_score: 35
      section: S_params
      round: 1
      score_before: 78
      soft_boost: true
      score_after: 85
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 40
  verified: 33
  pending: 7
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781804037_b9e5e2
  - ec_1781804038_a9f78f
  - ec_1781804040_9dc61c
  - ec_1781804041_092560
  - ec_1781804042_93f773
  - ec_1781804043_82f65d
  - ec_1781804044_d5349e
  - ec_1781804045_2db6b7
  - ec_1781804046_a45b0c
  - ec_1781804047_d08ad3
  - ec_1781804048_730b05
  - ec_1781804050_d5fcb3
  - ec_1781804051_8ebb0c
  - ec_1781804052_ad95ed
  - ec_1781804053_d765ac
  - ec_1781804054_a972db
  - ec_1781804055_7b8268
  - ec_1781804056_43cea9
  - ec_1781804057_7e380b
  - ec_1781804058_ae9a9e
  - ec_1781804059_e38eaf
  - ec_1781804060_cc35a5
  - ec_1781804061_c57d1a
  - ec_1781804061_0dcf0c
  - ec_1781804061_ff1fba
  - ec_1781804062_ae04d0
  - ec_1781804063_27d537
  - ec_1781804064_f1b700
  - ec_1781804065_624926
  - ec_1781804066_0ced20
  - ec_1781804067_fd63fc
  - ec_1781804068_b5b9d0
  - ec_1781804069_0b9b27
  - ec_1781804070_31637b
  - ec_1781804071_c63d85
  - ec_1781804072_abd632
  - ec_1781804073_adfbf0
  - ec_1781804073_f80f08
  - ec_1781804074_46a25a
  - ec_1781804075_526337
  pending_ids:
  - ec_1781804061_0dcf0c
  - ec_1781804061_ff1fba
  - ec_1781804065_624926
  - ec_1781804067_fd63fc
  - ec_1781804068_b5b9d0
  - ec_1781804069_0b9b27
  - ec_1781804073_f80f08
  processed_at: 1781804080.8640115
version: 15
---

# 合同审核

## 核心问题
审核销售合同中的关键条款（价格、质保、责任、知识产权、违约金），识别风险并给出修改建议。

## When to use
- keywords: contract, 合同, 审核, 审阅, 条款, 风险
- context: 用户上传或提及销售合同文件，需要分析合同条款风险并提出修改建议时
- excludes: 用户仅询问合同模板或合同范本，不涉及具体合同审核；用户上传的是非合同类文件（如发票、订单）

## S_params

### 参数化设计原则
本技能所有业务规则、风险阈值、审核范围及触发条件均需通过参数配置实现，禁止硬编码。参数分为三级：**全局默认参数**（适用于所有合同）、**企业级覆盖参数**（按客户/企业定制）、**单次调用参数**（用户临时指定）。参数优先级：单次调用 > 企业级覆盖 > 全局默认。

### 参数列表

| 参数名 | 类型 | 默认值 | 说明 | 覆盖层级 |
|--------|------|--------|------|----------|
| `risk_thresholds.liability_cap_min` | float | 1.0 | 责任限制条款中，责任上限占合同总价的最低比例（如1.0表示100%），低于此值标记为高风险 | 全局/企业/单次 |
| `risk_thresholds.liquidated_damages_max` | float | 0.3 | 违约金占合同总价的最高比例（如0.3表示30%），超过此值标记为高风险 | 全局/企业/单次 |
| `risk_thresholds.warranty_period_min_days` | int | 365 | 质保期最短天数，低于此值标记为中风险 | 全局/企业/单次 |
| `risk_thresholds.payment_term_max_days` | int | 90 | 最长账期天数，超过此值标记为中风险 | 全局/企业/单次 |
| `review_scope.required_clauses` | list[string] | ["价格与付款", "质保", "责任限制", "知识产权", "违约金"] | 必须审核的核心条款列表，可增删 | 全局/企业/单次 |
| `review_scope.optional_clauses` | list[string] | ["保密", "终止", "不可抗力", "争议解决"] | 可选审核的附加条款列表 | 全局/企业/单次 |
| `trigger_conditions.file_keywords` | list[string] | ["contract", "合同", "销售合同", "采购合同"] | 自动触发审核的文件名关键词列表 | 全局/企业/单次 |
| `trigger_conditions.auto_trigger_enabled` | bool | true | 是否启用文件名关键词自动触发 | 全局/企业/单次 |
| `risk_levels.high` | dict | {"label": "高风险", "color": "red", "priority": 1} | 高风险等级的定义（标签、颜色、优先级） | 全局/企业 |
| `risk_levels.medium` | dict | {"label": "中风险", "color": "yellow", "priority": 2} | 中风险等级的定义 | 全局/企业 |
| `risk_levels.low` | dict | {"label": "低风险", "color": "green", "priority": 3} | 低风险等级的定义 | 全局/企业 |
| `output.default_format` | string | "详细报告" | 默认输出格式，可选值：["详细报告", "摘要", "表格"] | 全局/企业/单次 |
| `output.include_negotiation_priority` | bool | true | 是否在报告中包含谈判优先级建议 | 全局/企业/单次 |
| `enterprise_config` | dict | {} | 企业级配置对象，包含企业名称、自定义阈值、审核范围覆盖等 | 企业 |

### 参数使用规则

1. **风险阈值参数**：在步骤3「逐条风险评估」中，所有比较判断必须引用对应参数值，不得使用硬编码数字。例如：
   - 判断违约金比例时，使用 `risk_thresholds.liquidated_damages_max` 而非固定值30%
   - 判断责任上限时，使用 `risk_thresholds.liability_cap_min` 而非固定值100%

2. **审核范围参数**：在步骤2「提取并解析合同关键条款」中，`required_clauses` 决定必须提取的条款，`optional_clauses` 决定可选提取的条款。若企业配置中增删了条款，则按企业配置执行。

3. **触发条件参数**：在步骤1「识别合同类型与触发条件」中，`file_keywords` 决定自动触发的文件名匹配规则。若 `auto_trigger_enabled` 为 false，则所有文件上传均需用户确认。

4. **企业级覆盖**：当系统识别到用户所属企业（如通过用户上下文或显式指定），应加载该企业的 `enterprise_config`，将其中的参数值覆盖全局默认值。企业配置可通过外部接口或配置文件动态加载。

5. **单次调用覆盖**：用户可在本次审核请求中通过输入参数临时指定某些参数值（如 `risk_thresholds.liquidated_damages_max = 0.2`），该值仅本次生效，优先级最高。

### 参数配置示例

```json
{
  "risk_thresholds": {
    "liability_cap_min": 1.0,
    "liquidated_damages_max": 0.3,
    "warranty_period_min_days": 365,
    "payment_term_max_days": 90
  },
  "review_scope": {
    "required_clauses": ["价格与付款", "质保", "责任限制", "知识产权", "违约金"],
    "optional_clauses": ["保密", "终止", "不可抗力", "争议解决"]
  },
  "trigger_conditions": {
    "file_keywords": ["contract", "合同

## Instructions
Follow these steps in order. Ask the user if anything is marked [待确认].

1.  **识别合同类型与触发条件**
    -   **if** 用户上传文件，且文件名包含 "contract" → 进入步骤2。
    -   **if** 用户上传文件，但文件名不包含 "contract" → 询问用户是否仍要执行合同审核流程，等待用户确认。
    -   **if** 用户未上传文件，但提出审核合同的需求 → 要求用户上传合同文件。

2.  **提取并解析合同关键条款**
    -   读取合同全文，提取以下五个核心条款的原文内容：
        -   a. 价格与付款条款
        -   b. 质保条款
        -   c. 责任限制条款
        -   d. 知识产权条款
        -   e. 违约金条款
    -   **if** 合同中缺少上述任一核心条款 → 在步骤4的风险报告中标记为「缺失条款，存在重大风险」。

3.  **逐条风险评估**
    -   对步骤2提取的每个条款，按以下标准进行风险判断：
        -   **价格与付款**：是否存在模糊的付款节点、过长的账期、或与市场惯例不符的定价机制？
        -   **质保**：质保期是否过短？质保范围是否排除了关键部件或服务？
        -   **责任限制**：责任上限是否过低（如低于合同总价的100%）？是否存在排除间接损失的条款？
        -   **知识产权**：知识产权归属是否清晰？是否有对己方不利的授权或保证条款？
        -   **违约金**：违约金比例是否过高（如超过合同总价的30%）？是否存在单方面惩罚性条款？
    -   **if** 条款存在风险 → 记录风险等级（高/中/低）并给出修改建议。
    -   **if** 条款无风险 → 标记为「通过」。

4.  **生成审核报告**
    -   汇总步骤3的结果，生成结构化报告，包含：
        -   **合同基本信息**：合同名称、签约方。
        -   **风险总览**：高风险项数量、中风险项数量、低风险项数量。
        -   **条款详情**：逐条列出风险等级、风险描述、修改建议。
        -   **谈判优先级**：建议优先谈判的高风险条款。
    -   **if** 用户要求修改报告格式（如导出为表格或摘要）→ 根据用户要求调整输出格式。

## Decision routes
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 用户上传文件，文件名包含 "contract" | 自动触发合同审核流程，从步骤2开始执行 | 主要触发路径 |
| 用户上传文件，文件名不包含 "contract" | 询问用户是否确认执行合同审核 | 防止误触发 |
| 用户未上传文件，但要求审核合同 | 要求用户上传合同文件 | 前置条件不满足 |
| 用户要求调整报告格式 | 根据用户要求重新组织报告输出 | 灵活响应 |

## Inputs
- contract_file: file, 必填，待审核的合同文件（支持 .docx, .pdf, .txt 格式）
- output_format: string, 默认值 "详细报告"，可选值 ["详细报告", "摘要", "表格"]，控制审核报告的呈现格式

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: contract, 合同, 审核, 审阅, 条款, 风险
- ✅ context: 用户上传或提及销售合同文件，需要分析合同条款风险并提出修改建议时
- ✅ excludes: 用户仅询问合同模板或合同范本，不涉及具体合同审核；用户上传的是非合同类文件（如发票、订单）
- ✅ 参数名 → 类型
- ✅ `risk_thresholds.liability_cap_min` → float
- ✅ `risk_thresholds.liquidated_damages_max` → float
- ✅ `risk_thresholds.warranty_period_min_days` → int
- ✅ `risk_thresholds.payment_term_max_days` → int
- ✅ `review_scope.required_clauses` → list[string]
- ✅ `review_scope.optional_clauses` → list[string]
- ✅ `trigger_conditions.file_keywords` → list[string]
- ✅ `trigger_conditions.auto_trigger_enabled` → bool
- ✅ `risk_levels.high` → dict
- ✅ `risk_levels.medium` → dict
- ✅ `risk_levels.low` → dict

### 待确认
- 📋 [evidence] 企业级覆盖：当系统识别到用户所属企业（如通过用户上下文或显式指定），应加载该企业的 enterprise_config，将其中的参数值覆盖全局默认值。企业配置可通过外部接口或配置文件动态加载。 (`ec_1781804061_0dcf0c`)
- 📋 [evidence] 单次调用覆盖：用户可在本次审核请求中通过输入参数临时指定某些参数值（如 risk_thresholds.liquidated_damages_max = 0.2），该值仅本次生效，优先级最高。 (`ec_1781804061_ff1fba`)
- 📋 [evidence] 读取合同全文，提取以下五个核心条款的原文内容： (`ec_1781804065_624926`)
- ⏳ [待验证] 对步骤2提取的每个条款，按以下标准进行风险判断： (`ec_1781804067_fd63fc`)
- ⏳ [待验证] 价格与付款：是否存在模糊的付款节点、过长的账期、或与市场惯例不符的定价机制？ (`ec_1781804068_b5b9d0`)
- ⏳ [待验证] 质保：质保期是否过短？质保范围是否排除了关键部件或服务？ (`ec_1781804069_0b9b27`)
- 📋 [evidence] if 条款无风险 → 标记为「通过」。 (`ec_1781804073_f80f08`)
