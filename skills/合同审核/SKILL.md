---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-19T19:16:31Z'
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
    version: 1.9.0
    weight: 0.83
    primary: true
  - id: media-publish
    version: 1.0.0
    weight: 0.17
    primary: false
  detected_at: '2026-06-19T19:16:31Z'
  conflicts:
  - 'PDCA(标准化渐进) vs OODA(快速适应): 两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。'
  domain_key: law
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1781896654
  dna_compliance:
    score: 5/6
    passed: 5
    total: 6
    all_passed: false
  save_gate:
    smoke_pass: false
    min_with_score: 24
    tasks:
    - workflow-080
  moe:
    overall_score: 76
    passed: true
    confidence: 0.7
    dimensions:
      structure: 87
      security: 100
      params: 35
      routing: 75
      content: 82
      brevity: 68
    boost_rounds:
    - boosted: true
      expert_key: params
      before_score: 27
      section: S_params
      round: 1
      score_before: 74
      soft_boost: true
      score_after: 76
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 40
  verified: 32
  pending: 8
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781896592_98772e
  - ec_1781896593_0b70c2
  - ec_1781896594_b86eb3
  - ec_1781896595_0ae469
  - ec_1781896596_d3dd40
  - ec_1781896597_30b883
  - ec_1781896597_9e18e1
  - ec_1781896598_0aa092
  - ec_1781896599_923e70
  - ec_1781896600_1c75ad
  - ec_1781896601_ee02b0
  - ec_1781896602_f84c9f
  - ec_1781896603_16856e
  - ec_1781896604_1fe396
  - ec_1781896605_1c6f7e
  - ec_1781896606_59132e
  - ec_1781896607_4abe0d
  - ec_1781896608_99cae9
  - ec_1781896609_69b3e3
  - ec_1781896609_950662
  - ec_1781896609_830bb0
  - ec_1781896609_2cd3e3
  - ec_1781896609_f525df
  - ec_1781896609_c55c14
  - ec_1781896610_129fc0
  - ec_1781896611_0c143d
  - ec_1781896612_e16575
  - ec_1781896613_b91e5b
  - ec_1781896614_4318ce
  - ec_1781896615_877553
  - ec_1781896615_45a045
  - ec_1781896616_57271c
  - ec_1781896617_08ab43
  - ec_1781896618_95b715
  - ec_1781896619_72adca
  - ec_1781896620_3b1864
  - ec_1781896621_63fbf1
  - ec_1781896621_debafe
  - ec_1781896622_ca73b0
  - ec_1781896623_53198b
  pending_ids:
  - ec_1781896592_98772e
  - ec_1781896604_1fe396
  - ec_1781896605_1c6f7e
  - ec_1781896609_950662
  - ec_1781896609_830bb0
  - ec_1781896609_2cd3e3
  - ec_1781896609_f525df
  - ec_1781896609_c55c14
  processed_at: 1781896627.2102501
version: 19
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
快速审核销售合同中的关键风险条款，确保合同条款符合公司标准。

## S_trigger
- keywords: contract, 合同, 销售合同, 审核合同, 合同审核
- context: 用户上传或指定一个文件，文件名包含“contract”关键词，且用户意图为审核合同内容。
- excludes: 文件名不包含“contract”关键词；用户意图不是审核合同（如只是询问合同模板）；文件内容为空或无法读取。

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1. [门禁] 确认文件名是否包含“contract”关键词。如果文件名不包含“contract”，则中止流程并提示“该文件不是合同，不执行审核”。
2. 读取合同文件内容。如果文件无法读取或为空，则中止并提示“文件内容为空或无法读取”。
3. 提取合同中的以下关键条款内容：
   - 价格条款（Price）：包括单价、总价、付款方式、付款期限。
   - 保修条款（Warranty）：包括保修期限、保修范围、免责条款。
   - 责任条款（Liability）：包括责任上限、责任排除、赔偿条件。
   - 知识产权条款（IP）：包括知识产权归属、使用许可、侵权责任。
   - 违约条款（Penalty）：包括违约情形、违约金计算方式、解除合同条件。
4. 对每个提取的条款，逐一检查是否存在以下风险：
   - 价格条款：价格是否明确、付款条件是否合理、是否存在隐藏费用。
   - 保修条款：保修期限是否过短、免责范围是否过大、是否包含不合理限制。
   - 责任条款：责任上限是否过低、责任排除是否过于宽泛、赔偿条件是否苛刻。
   - 知识产权条款：知识产权归属是否清晰、使用许可范围是否合理、侵权责任分配是否公平。
   - 违约条款：违约情形是否明确、违约金比例是否过高、解除合同条件是否合理。
5. [门禁] 如果任一条款存在高风险（如责任上限低于公司标准、违约金超过法定上限），则标记为“高风险”，并输出风险详情。如果所有条款均为低风险或中风险，则标记为“低风险”。
6. 输出审核结果，格式为：
   - 合同名称：[文件名]
   - 风险等级：[高风险/低风险]
   - 条款审核详情：
     - 价格条款：[通过/风险项描述]
     - 保修条款：[通过/风险项描述]
     - 责任条款：[通过/风险项描述]
     - 知识产权条款：[通过/风险项描述]
     - 违约条款：[通过/风险项描述]
   - 总体建议：[如：建议修改责任上限条款，将上限提高至XXX]

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 文件名包含“contract” | 执行完整合同审核流程 | 正常路径 |
| 文件名不包含“contract” | 中止流程，提示非合同文件 | 异常路径 |
| 文件内容为空或无法读取 | 中止流程，提示文件错误 | 边界情况 |
| 任一条款为高风险 | 标记为高风险，输出风险详情 | 高风险分支 |
| 所有条款均为低风险或中风险 | 标记为低风险，输出审核结果 | 低风险分支 |
| 确认文件名是否包含“contract”关键词。如果文件名不包含“contract”，则中止流程并提示“该文件不是合同，不 | 中止或升级 | [门禁] |
| 如果任一条款存在高风险（如责任上限低于公司标准、违约金超过法定上限），则标记为“高风险”，并输出风险详情。如果所有条款均 | 中止或升级 | [门禁] |

## S_params
- file_path: string, 无默认值，必填。待审核合同文件的路径。
- risk_threshold: string, 默认值 "high"，可选。风险等级阈值，可选值为 "high"（高风险）或 "low"（低风险），用于决定是否标记为高风险。
- output_format: string, 默认值 "text"，可选。输出格式，可选值为 "text"（文本）或 "json"（JSON），用于指定审核结果的输出格式。
- risk_rules: dict, 默认值如下，可选。各条款的风险判断标准，支持按条款类型独立配置阈值和关键词。
  - price:
      - hidden_fee_keywords: list, 默认值 ["隐藏费用","额外收费","另行收费"]，可选。识别隐藏费用的关键词列表。
      - max_payment_term_days: integer, 默认值 90，可选。最长付款期限（天），超过此值视为风险。
  - warranty:
      - min_warranty_months: integer, 默认值 12，可选。最低保修期限（月），低于此值视为风险。
      - exclusion_keywords: list, 默认值 ["人为损坏","不可抗力","非正常使用"]，可选。免责条款中不合理排除项的关键词列表。
  - liability:
      - min_liability_cap_ratio: float, 默认值 0.8，可选。责任上限占合同总价的最低比例（如0.8表示80%），低于此值视为高风险。
      - broad_exclusion_keywords: list, 默认值 ["任何","所有","全部","间接损失"]，可选。责任排除过于宽泛的关键词列表。
  - ip:
      - ownership_clarity_keywords: list, 默认值 ["归甲方所有","归乙方所有","共同所有"]，可选。知识产权归属明确性关键词。
      - unreasonable_license_keywords: list, 默认值 ["永久免费","无偿转让","无限授权"]，可选。使用许可不合理的关键词列表。
  - penalty:
      - max_penalty_ratio: float, 默认值 0.2，可选。违约金占合同总价的最高比例（如0.2表示20%），超过此值视为高风险。
      - termination_condition_keywords: list, 默认值 ["任意解除","单方解除","随时解除"]，可选。解除合同条件不合理的关键词列表。
- company_standard_liability_cap: float, 默认值 0.8，可选。公司标准责任上限比例，用于步骤5中高风险判断的基准值。
- company_standard_penalty_cap: float, 默认值 0.2，可选。公司标准违约金上限比例，用于步骤5中高风险判断的基准值。
- required_clauses: list, 默认值 ["价格条款","保修条款","责任条款","知识产权条款","违约条款"]，可选。合同必须包含的条款列表，缺失任一则触发错误处理。
- clause_extraction_rules: dict, 默认值如下，可选。条款提取时的关键词匹配规则，用于辅助识别各条款内容。
  - price_keywords: list, 默认值 ["单价","总价","付款方式","付款期限","价格"]，可选。
  - warranty_keywords: list, 默认值 ["保修","质保","保修期","保修范围"]，可选。
  - liability_keywords: list, 默认值 ["责任上限","责任排除","赔偿条件","赔偿责任"]，可选。
  - ip_keywords: list, 默认值 ["知识产权","版权","专利","商标","归属"]，可选。
  - penalty_keywords: list, 默认值 ["违约金","违约","解除合同","违约责任"]，可选。

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## S_appendix
### 示例
用户输入：文件路径为 "/documents/sales_contract_2024.pdf"，文件名包含 "contract"。
执行步骤：
1. 文件名包含 "contract"，通过门禁。
2. 读取文件成功。
3. 提取条款：价格条款为“总价100万，预付30%，尾款70%在验收后30天内支付”；保修条款为“保修期1年，不包括人为损坏”；责任条款为“责任上限为合同总价的50%”；知识产权条款为“知识产权归甲方所有，乙方仅有使用权”；违约条款为“违约金为合同总价的20%”。
4. 检查风险：价格条款通过；保修条款通过；责任条款风险项：责任上限低于公司标准（80%）；知识产权条款通过；违约条款通过。
5. 责任条款为高风险，标记为“高风险”。
6. 输出：
   - 合同名称：sales_contract_2024.pdf
   - 风险等级：高风险
   - 条款审核详情：
     - 价格条款：通过
     - 保修条款：通过
     - 责任条款：风险项：责任上限为合同总价的50%，低于公司标准80%
     - 知识产权条款：通过
     - 违约条款：通过
   - 总体建议：建议修改责任上限条款，将上限提高至合同总价的80%。

### 错误处理
- 如果文件路径不存在或无法访问，提示“文件路径无效，请检查路径是否正确”。
- 如果文件格式不支持（如 .exe 文件），提示“不支持的文件格式，请提供文本或PDF格式的合同文件”。
- 如果提取条款时发现缺少必要条款（如未找到价格条款），提示“缺少关键条款：[条款名]，请确认合同完整性”。

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ context: 用户上传或指定一个文件，文件名包含“contract”关键词，且用户意图为审核合同内容。
- ✅ excludes: 文件名不包含“contract”关键词；用户意图不是审核合同（如只是询问合同模板）；文件内容为空或无法读取。
- ✅ [门禁] 确认文件名是否包含“contract”关键词。如果文件名不包含“contract”，则中止流程并提示“该文件不是合同，不执行审核”。
- ✅ 读取合同文件内容。如果文件无法读取或为空，则中止并提示“文件内容为空或无法读取”。
- ✅ 提取合同中的以下关键条款内容：
- ✅ 价格条款（Price）：包括单价、总价、付款方式、付款期限。
- ✅ 保修条款（Warranty）：包括保修期限、保修范围、免责条款。
- ✅ 责任条款（Liability）：包括责任上限、责任排除、赔偿条件。
- ✅ 知识产权条款（IP）：包括知识产权归属、使用许可、侵权责任。
- ✅ 违约条款（Penalty）：包括违约情形、违约金计算方式、解除合同条件。
- ✅ 对每个提取的条款，逐一检查是否存在以下风险：
- ✅ 价格条款：价格是否明确、付款条件是否合理、是否存在隐藏费用。
- ✅ 知识产权条款：知识产权归属是否清晰、使用许可范围是否合理、侵权责任分配是否公平。
- ✅ 违约条款：违约情形是否明确、违约金比例是否过高、解除合同条件是否合理。
- ✅ [门禁] 如果任一条款存在高风险（如责任上限低于公司标准、违约金超过法定上限），则标记为“高风险”，并输出风险详情。如果所有条款均为低风险或中风险，则标记为“低风险”。

### 待确认
- ⏳ [待验证] keywords: contract, 合同, 销售合同, 审核合同, 合同审核 (`ec_1781896592_98772e`)
- ⏳ [待验证] 保修条款：保修期限是否过短、免责范围是否过大、是否包含不合理限制。 (`ec_1781896604_1fe396`)
- ⏳ [待验证] 责任条款：责任上限是否过低、责任排除是否过于宽泛、赔偿条件是否苛刻。 (`ec_1781896605_1c6f7e`)
- 📋 [evidence] 价格条款：[通过/风险项描述] (`ec_1781896609_950662`)
- 📋 [evidence] 保修条款：[通过/风险项描述] (`ec_1781896609_830bb0`)
- 📋 [evidence] 责任条款：[通过/风险项描述] (`ec_1781896609_2cd3e3`)
- 📋 [evidence] 知识产权条款：[通过/风险项描述] (`ec_1781896609_f525df`)
- 📋 [evidence] 违约条款：[通过/风险项描述] (`ec_1781896609_c55c14`)
