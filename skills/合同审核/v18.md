---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-19T18:18:02Z'
description: Handles 合同审核 workflows with step-by-step instructions. Use when the user
  mentions 合同审核 or related tasks.
portable_slug: skill-aecb7055
draft: false
domain: law
domain_label: 法学
philosophical_dna: pdca
philosophical_dna_label: PDCA 循环
philosophical_dna_secondary:
- ooda
methodology: business-process
methodology_label: PDCA 循环
dna_lineage:
  philosophical:
  - id: pdca
    weight: 0.67
  - id: ooda
    weight: 0.33
  domain:
  - id: law-contract-review
    version: 1.8.0
    weight: 0.85
    primary: true
  - id: code-review-pr
    version: 1.11.0
    weight: 0.15
    primary: false
  detected_at: '2026-06-19T18:18:02Z'
  conflicts:
  - 'PDCA(标准化渐进) vs OODA(快速适应): 两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。'
  domain_key: law
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1781893136
  dna_compliance:
    score: 6/6
    passed: 6
    total: 6
    all_passed: true
  save_gate:
    smoke_pass: false
    min_with_score: 24
    tasks:
    - workflow-080
  moe:
    overall_score: 82
    passed: true
    confidence: 0.7
    dimensions:
      structure: 87
      security: 100
      params: 78
      routing: 62
      content: 82
      brevity: 78
    boost_rounds:
    - boosted: true
      expert_key: params
      before_score: 28
      section: S_params
      round: 1
      score_before: 72
      soft_boost: true
      score_after: 82
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 37
  verified: 28
  pending: 9
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781893083_068527
  - ec_1781893084_77aed2
  - ec_1781893085_93347f
  - ec_1781893086_4d625f
  - ec_1781893086_213e11
  - ec_1781893087_eeda98
  - ec_1781893088_77ace3
  - ec_1781893089_ffaee6
  - ec_1781893089_c17c2e
  - ec_1781893090_9859bc
  - ec_1781893091_7874ba
  - ec_1781893092_69f819
  - ec_1781893092_7c5fbf
  - ec_1781893092_4546c4
  - ec_1781893093_823e80
  - ec_1781893094_e54d6c
  - ec_1781893095_697cc6
  - ec_1781893095_5d6d31
  - ec_1781893096_18fbab
  - ec_1781893097_3ae745
  - ec_1781893097_13f9ed
  - ec_1781893098_1e1709
  - ec_1781893099_4945ac
  - ec_1781893100_ccd09f
  - ec_1781893101_723dcc
  - ec_1781893102_906ee7
  - ec_1781893103_f12366
  - ec_1781893104_fac658
  - ec_1781893105_b226b8
  - ec_1781893105_dd8ac5
  - ec_1781893106_345898
  - ec_1781893107_ee3296
  - ec_1781893107_25297a
  - ec_1781893107_d55617
  - ec_1781893108_66e7af
  - ec_1781893109_f6ddb3
  - ec_1781893110_69330e
  pending_ids:
  - ec_1781893083_068527
  - ec_1781893084_77aed2
  - ec_1781893085_93347f
  - ec_1781893086_213e11
  - ec_1781893092_7c5fbf
  - ec_1781893097_3ae745
  - ec_1781893105_dd8ac5
  - ec_1781893107_25297a
  - ec_1781893107_d55617
  processed_at: 1781893114.696284
version: 18
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
快速识别销售合同中的关键风险条款，并给出修改建议。

## S_trigger
- keywords: contract, 合同, 审核, 条款, 风险, 销售合同
- context: 用户上传文件或提出与合同审核相关的请求时
- excludes: 用户仅询问法律常识（不涉及具体合同）、用户上传非合同类文件

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1.  [门禁] 确认文件名称包含 "contract" 或用户明确要求审核合同。若不满足，中止并告知原因；若用户上传非销售合同（如租赁、劳务），则告知本技能仅适用于销售合同，建议使用其他工具。
2.  识别合同类型为销售合同，提取合同主体（买方、卖方）、标的物、合同金额。若提取失败（如文件无法解析），则提示用户手动补充关键信息。
3.  逐条审核以下关键条款，并记录风险点：
    - 价格与支付条款：核对金额、币种、支付节点、发票要求。
    - 保修条款：保修期限、范围、责任上限。
    - 责任限制条款：赔偿上限、免责范围、间接损失排除。
    - 知识产权条款：所有权归属、使用许可范围、侵权赔偿。
    - 违约条款：违约金比例、触发条件、解除权。
    - 若发现以下高风险条款，标记为「严重风险」并建议拒绝签署：责任上限低于合同金额的 50%；知识产权归属约定不明确或对己方不利；违约金超过合同金额的 30%；保修期超过行业标准 2 倍以上。
4.  对每个风险条款，给出修改建议（具体措辞或谈判方向）。若API超时，则重试3次后返回错误信息“审核服务暂时不可用，请稍后重试”。
5.  汇总输出审核报告，格式根据 output_format 参数决定（report / summary / redline）。

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 用户上传合同文件，文件名含 "contract" | 执行完整审核流程（S_body 1-5） | 默认触发路径 |
| 用户要求审核合同，但文件名不含 "contract" | 确认用户意图后执行流程 | 需用户确认 |
| 用户询问合同条款建议（未上传文件） | 引导用户上传合同文件 | 前置条件不满足 |
| 用户上传非销售合同（如租赁、劳务） | 告知本技能仅适用于销售合同，建议使用其他工具 | 边界情况 |
| 审核过程中API超时 | 重试3次，若仍失败则返回错误信息 | 异常处理分支 |
| 确认文件名称包含 "contract" 或用户明确要求审核合同。若不满足，中止并告知原因；若用户上传非销售合同（如租赁、 | 中止或升级 | [门禁] |

## S_params
- file_path: string, 无默认值，合同文件的路径
- review_depth: string, "standard"，可选值 ["quick", "standard", "deep"]，审核深度
- output_format: string, "report"，可选值 ["report", "summary", "redline"]，输出格式
- risk_thresholds: object, 默认值如下，风险判定阈值参数化：
  - liability_cap_ratio: number, 0.5，责任上限低于合同金额的此比例时标记为「严重风险」，取值范围 [0, 1]
  - ip_ownership_unclear: boolean, true，知识产权归属不明确时标记为「严重风险」
  - penalty_ratio: number, 0.3，违约金超过合同金额的此比例时标记为「严重风险」，取值范围 [0, 1]
  - warranty_multiplier: number, 2.0，保修期超过行业标准此倍数时标记为「严重风险」，取值范围 [1, 5]
- error_handling: object, 默认值如下，异常处理策略参数化：
  - api_retry_count: integer, 3，API超时重试次数，取值范围 [0, 5]
  - api_timeout_seconds: integer, 30，API超时阈值（秒），取值范围 [10, 120]
  - fallback_message: string, "审核服务暂时不可用，请稍后重试"，重试失败后返回的错误信息
- extraction_fallback: string, "prompt_user"，可选值 ["prompt_user", "skip", "use_defaults"]，合同信息提取失败时的处理策略

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ [门禁] 确认文件名称包含 "contract" 或用户明确要求审核合同。若不满足，中止并告知原因；若用户上传非销售合同（如租赁、劳务），则告知本技能仅适用于销售合同，建议使用其他工具。
- ✅ 逐条审核以下关键条款，并记录风险点：
- ✅ 价格与支付条款：核对金额、币种、支付节点、发票要求。
- ✅ 保修条款：保修期限、范围、责任上限。
- ✅ 责任限制条款：赔偿上限、免责范围、间接损失排除。
- ✅ 知识产权条款：所有权归属、使用许可范围、侵权赔偿。
- ✅ 违约条款：违约金比例、触发条件、解除权。
- ✅ 若发现以下高风险条款，标记为「严重风险」并建议拒绝签署：责任上限低于合同金额的 50%；知识产权归属约定不明确或对己方不利；违约金超过合同金额的 30%；保修期超过行业标准 2 倍以上。
- ✅ 汇总输出审核报告，格式根据 output_format 参数决定（report / summary / redline）。
- ✅ 用户意图/条件 → 执行动作
- ✅ 用户上传合同文件，文件名含 "contract" → 执行完整审核流程（S_body 1-5）
- ✅ 用户要求审核合同，但文件名不含 "contract" → 确认用户意图后执行流程
- ✅ 用户询问合同条款建议（未上传文件） → 引导用户上传合同文件
- ✅ 用户上传非销售合同（如租赁、劳务） → 告知本技能仅适用于销售合同，建议使用其他工具
- ✅ 确认文件名称包含 "contract" 或用户明确要求审核合同。若不满足，中止并告知原因；若用户上传非销售合同（如租赁、 → 中止或升级

### 待确认
- ⏳ [待验证] keywords: contract, 合同, 审核, 条款, 风险, 销售合同 (`ec_1781893083_068527`)
- ⏳ [待验证] context: 用户上传文件或提出与合同审核相关的请求时 (`ec_1781893084_77aed2`)
- ⏳ [待验证] excludes: 用户仅询问法律常识（不涉及具体合同）、用户上传非合同类文件 (`ec_1781893085_93347f`)
- 📋 [evidence] 识别合同类型为销售合同，提取合同主体（买方、卖方）、标的物、合同金额。若提取失败（如文件无法解析），则提示用户手动补充关键信息。 (`ec_1781893086_213e11`)
- 📋 [evidence] 对每个风险条款，给出修改建议（具体措辞或谈判方向）。若API超时，则重试3次后返回错误信息“审核服务暂时不可用，请稍后重试”。 (`ec_1781893092_7c5fbf`)
- 📋 [evidence] 审核过程中API超时 → 重试3次，若仍失败则返回错误信息 (`ec_1781893097_3ae745`)
- 📋 [evidence] error_handling: object, 默认值如下，异常处理策略参数化： (`ec_1781893105_dd8ac5`)
- 📋 [evidence] fallback_message: string, "审核服务暂时不可用，请稍后重试"，重试失败后返回的错误信息 (`ec_1781893107_25297a`)
- 📋 [evidence] extraction_fallback: string, "prompt_user"，可选值 ["prompt_user", "skip", "use_defaults"]，合同信息提取失败时的处理策略 (`ec_1781893107_d55617`)
