---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-19T03:08:18Z'
description: Handles 合同审核 workflows with step-by-step instructions. Use when the user
  mentions 合同审核 or related tasks.
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
    version: 1.7.0
    weight: 0.83
    primary: true
  - id: code-review-pr
    version: 1.9.0
    weight: 0.17
    primary: false
  detected_at: '2026-06-19T03:08:18Z'
  domain_key: law
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1781838559
  dna_compliance:
    score: 5/6
    passed: 5
    total: 6
    all_passed: false
  save_gate:
    smoke_pass: false
    min_with_score: 73
    tasks:
    - workflow-080
  moe:
    overall_score: 78
    passed: true
    confidence: 0.7
    dimensions:
      structure: 92
      security: 100
      params: 38
      routing: 72
      content: 82
      brevity: 78
    boost_rounds:
    - boosted: true
      expert_key: params
      before_score: 35
      section: S_params
      round: 1
      score_before: 73
      soft_boost: true
      score_after: 78
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 40
  verified: 33
  pending: 7
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781838499_e32bb1
  - ec_1781838499_b9a9c5
  - ec_1781838500_e89570
  - ec_1781838501_dfa7de
  - ec_1781838501_d084cb
  - ec_1781838502_bebab4
  - ec_1781838503_56231d
  - ec_1781838504_3c1b0d
  - ec_1781838504_f804c5
  - ec_1781838505_b0a73f
  - ec_1781838506_a7bb84
  - ec_1781838506_7c3681
  - ec_1781838507_928519
  - ec_1781838507_6ac386
  - ec_1781838507_85369c
  - ec_1781838508_2e4813
  - ec_1781838508_fc1cc5
  - ec_1781838509_efab5a
  - ec_1781838509_557576
  - ec_1781838510_7d8d9c
  - ec_1781838511_fe38ff
  - ec_1781838511_e3f2f1
  - ec_1781838512_0ab766
  - ec_1781838513_74887d
  - ec_1781838513_6d772e
  - ec_1781838514_3a4db3
  - ec_1781838514_1ccd49
  - ec_1781838515_2cba96
  - ec_1781838516_4a2838
  - ec_1781838517_d80563
  - ec_1781838517_3581fc
  - ec_1781838518_805ec6
  - ec_1781838518_f4027b
  - ec_1781838519_6daba0
  - ec_1781838520_cfd28b
  - ec_1781838521_e534b0
  - ec_1781838522_89a58c
  - ec_1781838522_b267bb
  - ec_1781838523_54aaba
  - ec_1781838524_2f9664
  pending_ids:
  - ec_1781838507_928519
  - ec_1781838507_6ac386
  - ec_1781838508_2e4813
  - ec_1781838508_fc1cc5
  - ec_1781838509_557576
  - ec_1781838513_6d772e
  - ec_1781838515_2cba96
  processed_at: 1781838527.118572
version: 17
---

---
name: skill-aecb7055
description: Handles 合同审核 workflows with step-by-step instructions. Use when the user
  mentions 合同审核 or related tasks.
metadata:
  skillos_version: 0.3.0
  display_name: 合同审核
  generated_by: SkillOS
  skillos_slug: skill-aecb7055
---

# 合同审核

## 核心问题
快速识别销售合同中的关键风险条款，确保合同条款符合公司利益和行业惯例。

## S_trigger
当用户上传合同文件、要求审核合同条款、或提及合同风险时触发本技能。触发上下文包括：用户发送包含“合同”、“条款”、“审核”、“风险”等关键词的消息，或直接上传合同文件。

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1. 识别合同类型并提取条款
   - IF 文件名包含 "contract" 或用户明确要求审核销售合同 → 扫描合同全文，提取价格、保修、责任、知识产权、违约五个核心条款区域
   - ELSE → 提示用户提供销售合同文件，并说明本技能仅处理销售合同审核
   - IF 任一核心条款缺失 → 标记为「待确认条款」并在输出中提示用户补充

2. 逐项审核条款风险并生成报告
   - 对每个核心条款执行以下检查：
     - 价格条款：检查是否有明确的价格调整机制、付款节点是否合理
     - 保修条款：检查保修期是否过长（超过行业标准3年）、保修范围是否包含非正常使用
     - 责任条款：检查赔偿上限是否低于合同金额的100%、是否排除了重大过失责任
     - 知识产权条款：检查是否将背景知识产权也归属给对方、许可范围是否超出业务需要
     - 违约条款：检查违约金是否超过合同金额的30%（可能被法院调减）
   - IF 发现高风险条款（如赔偿上限过低、知识产权归属不合理） → 标记为「高风险」并给出修改建议
   - IF 发现中风险条款（如保修期略长、付款节点模糊） → 标记为「中风险」并给出谈判建议
   - IF 条款无异常 → 标记为「通过」
   - IF API超时或解析失败 → 重试最多3次，若仍失败则返回错误信息并提示用户重新上传

3. 输出审核报告
   - 汇总所有条款的审核结果，按以下格式输出：
     - 合同类型：[销售合同/其他]
     - 条款审核结果：逐条列出条款名称、风险等级（高风险/中风险/通过）、具体问题及建议
     - 待确认条款：列出缺失条款名称
     - 异常说明：如有重试失败或解析错误，在此说明

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 文件名包含 "contract" 或用户明确要求审核销售合同 | 继续执行合同审核流程 | 触发条件满足后进入条款提取阶段 |
| 任一核心条款缺失 | 标记为「待确认条款」并在输出中提示用户补充 | 确保合同完整性 |
| 发现高风险条款（如赔偿上限过低、知识产权归属不合理） | 标记为「高风险」并给出修改建议 | 需重点提示用户规避风险 |
| 发现中风险条款（如保修期略长、付款节点模糊） | 标记为「中风险」并给出谈判建议 | 提示用户可协商优化 |
| API超时或解析失败 | 重试最多3次，若仍失败则返回错误信息 | 异常处理分支，确保系统鲁棒性 |

## S_params
```markdown

## S_params
| 参数名 | 类型 | 取值范围 | 默认值 | 说明 |
|--------|------|----------|--------|------|
| contract_file | string | 文件路径或URL | 无 | 用户上传的合同文件，必填 |
| review_mode | string | "standard", "quick", "deep" | "standard" | 审核模式：standard标准审核，quick快速审核，deep深度审核 |
| max_retries | integer | 0-5 | 3 | API超时或解析失败时的最大重试次数 |
| industry_type | string | "general", "software", "manufacturing", "construction", "finance" | "general" | 行业类型，用于匹配行业特定的合同审核标准与阈值 |
| company_risk_tolerance | string | "low", "medium", "high" | "medium" | 公司风险偏好等级，影响风险条款的判定阈值（如赔偿上限比例、保修期上限） |
| price_adjustment_threshold | float | 0-100 | 10.0 | 价格条款中，允许的价格浮动百分比上限，超过此值标记为中风险 |
| warranty_period_max_months | integer | 0-60 | 36 | 保修条款中，允许的最大保修月数，超过此值标记为中风险（行业标准3年=36个月） |
| liability_cap_min_percent | float | 0-200 | 100.0 | 责任条款中，赔偿上限占合同金额的最低百分比，低于此值标记为高风险 |
| penalty_cap_percent | float | 0-100 | 30.0 | 违约条款中，违约金占合同金额的最高百分比，超过此值标记为高风险（可能被法院调减） |
| ip_background_ownership | string | "retain", "transfer", "shared" | "retain" | 知识产权条款中，背景知识产权的默认归属方式，用于判断条款是否合理 |
| ip_license_scope_limit | string | "business_necessary", "all_fields", "unlimited" | "business_necessary" | 知识产权许可范围的默认限制，超出此范围标记为中风险 |
| exclude_gross_negligence | boolean | true, false | false | 责任条款中，是否允许排除重大过失责任，true表示允许排除（高风险），false表示不允许 |
| missing_clause_action | string | "prompt", "auto_fill", "reject" | "prompt" | 当核心条款缺失时的处理方式：prompt提示用户，auto_fill自动填充默认条款，reject拒绝审核 |
```

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ IF 文件名包含 "contract" 或用户明确要求审核销售合同 → 扫描合同全文，提取价格、保修、责任、知识产权、违约五个核心条款区域
- ✅ ELSE → 提示用户提供销售合同文件，并说明本技能仅处理销售合同审核
- ✅ IF 任一核心条款缺失 → 标记为「待确认条款」并在输出中提示用户补充
- ✅ 逐项审核条款风险并生成报告
- ✅ 对每个核心条款执行以下检查：
- ✅ 价格条款：检查是否有明确的价格调整机制、付款节点是否合理
- ✅ 保修条款：检查保修期是否过长（超过行业标准3年）、保修范围是否包含非正常使用
- ✅ 责任条款：检查赔偿上限是否低于合同金额的100%、是否排除了重大过失责任
- ✅ 知识产权条款：检查是否将背景知识产权也归属给对方、许可范围是否超出业务需要
- ✅ 违约条款：检查违约金是否超过合同金额的30%（可能被法院调减）
- ✅ IF 发现高风险条款（如赔偿上限过低、知识产权归属不合理） → 标记为「高风险」并给出修改建议
- ✅ IF 发现中风险条款（如保修期略长、付款节点模糊） → 标记为「中风险」并给出谈判建议
- ✅ 汇总所有条款的审核结果，按以下格式输出：
- ✅ 待确认条款：列出缺失条款名称
- ✅ 用户意图/条件 → 执行动作

### 待确认
- 📋 [evidence] IF 条款无异常 → 标记为「通过」 (`ec_1781838507_928519`)
- 📋 [evidence] IF API超时或解析失败 → 重试最多3次，若仍失败则返回错误信息并提示用户重新上传 (`ec_1781838507_6ac386`)
- ⏳ [待验证] 合同类型：[销售合同/其他] (`ec_1781838508_2e4813`)
- 📋 [evidence] 条款审核结果：逐条列出条款名称、风险等级（高风险/中风险/通过）、具体问题及建议 (`ec_1781838508_fc1cc5`)
- 📋 [evidence] 异常说明：如有重试失败或解析错误，在此说明 (`ec_1781838509_557576`)
- 📋 [evidence] API超时或解析失败 → 重试最多3次，若仍失败则返回错误信息 (`ec_1781838513_6d772e`)
- ⏳ [待验证] review_mode → string (`ec_1781838515_2cba96`)
