---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-19T02:03:16Z'
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
    version: 1.6.0
    weight: 0.83
    primary: true
  - id: media-publish
    version: 1.0.0
    weight: 0.17
    primary: false
  detected_at: '2026-06-19T02:03:16Z'
  conflicts:
  - 'PDCA(标准化渐进) vs OODA(快速适应): 两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。'
  domain_key: law
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1781834665
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
      structure: 97
      security: 100
      params: 72
      routing: 60
      content: 83
      brevity: 78
    boost_rounds:
    - boosted: true
      expert_key: params
      before_score: 27
      section: S_params
      round: 1
      score_before: 74
      soft_boost: true
      score_after: 82
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 40
  verified: 39
  pending: 1
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781834597_c32139
  - ec_1781834598_32e49f
  - ec_1781834599_977b44
  - ec_1781834600_9a2a7a
  - ec_1781834601_962a1f
  - ec_1781834601_c5f488
  - ec_1781834602_803346
  - ec_1781834603_690a6a
  - ec_1781834604_fd0d6b
  - ec_1781834604_91f9e4
  - ec_1781834605_3c7279
  - ec_1781834606_2ae545
  - ec_1781834607_e1f2cd
  - ec_1781834607_498942
  - ec_1781834608_e6508a
  - ec_1781834609_c9e98d
  - ec_1781834610_f1d338
  - ec_1781834610_42dadb
  - ec_1781834611_fb7bb5
  - ec_1781834612_d2625a
  - ec_1781834613_777b3b
  - ec_1781834614_fb8fa7
  - ec_1781834614_64a91e
  - ec_1781834615_8e87cb
  - ec_1781834616_076544
  - ec_1781834617_f105e1
  - ec_1781834618_ee3e53
  - ec_1781834618_117a44
  - ec_1781834619_311af3
  - ec_1781834620_b4ba71
  - ec_1781834620_776d87
  - ec_1781834621_d4b845
  - ec_1781834622_8e2ad3
  - ec_1781834623_9f9b32
  - ec_1781834623_fb99ef
  - ec_1781834624_a3d3b5
  - ec_1781834625_5beb16
  - ec_1781834625_a82617
  - ec_1781834626_a5c595
  - ec_1781834627_97da53
  pending_ids:
  - ec_1781834598_32e49f
  processed_at: 1781834629.9033768
version: 16
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
快速识别销售合同中的关键条款风险，提供初步审核意见。

## S_trigger
- keywords: contract, 合同审核, 审合同, 销售合同
- context: 用户上传文件或提出审核合同的需求时
- excludes: 文件名不包含 "contract" 且用户未明确要求审核合同；文件类型不是销售合同

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1.  接收用户上传的文件，检查文件名是否包含 "contract" 或用户是否明确要求审核合同。
    - 如果文件名包含 "contract" 或用户明确要求，则进入步骤 2。
    - 否则，不触发本技能，并提示用户：“请提供文件名包含‘contract’的销售合同文件，或明确说明需要审核合同。”
2.  确认文件类型是否为销售合同。
    - 如果文件内容明确为销售合同（例如，包含“销售合同”、“买卖合同”等标题或条款），则进入步骤 3。
    - 如果文件不是销售合同（例如，是劳动合同、租赁合同等），则终止流程，并提示用户：“当前文件不是销售合同，本技能仅适用于销售合同审核。”
3.  读取并解析合同全文，提取关键条款信息，包括但不限于：
    - 合同双方信息
    - 标的物描述与价格
    - 付款方式与期限
    - 交付与验收条款
    - 质量保证与保修条款
    - 违约责任与赔偿限额
    - 知识产权归属
    - 保密条款
    - 争议解决方式
    - 合同期限与终止条件
4.  根据以下规则对提取的条款进行风险审核：
    - **价格与付款条款**：检查价格是否明确、付款节点是否清晰、是否存在不合理的预付款或尾款比例。
    - **质量保证条款**：检查质保期是否过长或过短、质保范围是否明确、维修响应时间是否合理。
    - **违约责任条款**：检查违约金比例是否过高（通常不超过合同总金额的30%）、赔偿限额是否对己方不利、是否存在单方免责条款。
    - **知识产权条款**：检查在合作过程中产生的知识产权归属是否清晰、是否存在将己方背景知识产权无偿转让给对方的风险。
    - **争议解决条款**：检查争议解决方式（仲裁或诉讼）是否对己方有利、管辖地是否合理。
5.  汇总审核结果，生成结构化报告。
    - 如果发现高风险条款，在报告中明确标记，并给出修改建议。
    - 如果所有条款风险可控，则在报告中说明“未发现重大风险”。
    - 如果无法解析合同内容或条款不完整，则在报告中说明“无法完成审核，请提供完整清晰的合同文件”。

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
| :--- | :--- | :--- |
| 文件名包含 "contract" | 执行 S_body 步骤 2-5 | 主要触发路径 |
| 用户明确要求审核合同 | 执行 S_body 步骤 1-5 | 次要触发路径 |
| 文件名不包含 "contract" 且用户未要求 | 不触发，提示用户 | 避免误触发 |
| 文件不是销售合同 | 终止流程，提示用户 | 类型不匹配 |
| 合同内容无法解析 | 输出“无法完成审核”报告 | 异常处理 |

## S_params
- file_path: string, 无默认值，用户上传的文件路径
- contract_type: string, 默认值 "sales"，文件类型，当前仅支持销售合同
- risk_thresholds: dict, 默认值如下，风险审核规则中的关键阈值参数化，允许用户按需调整：
  - penalty_ratio_max: float, 默认值 0.3，违约金比例上限（如合同总金额的30%），超过此值标记为高风险
  - warranty_period_min: int, 默认值 12，质保期最短月数，低于此值标记为风险
  - warranty_period_max: int, 默认值 60，质保期最长月数，超过此值标记为风险
  - prepayment_ratio_max: float, 默认值 0.5，预付款比例上限，超过此值标记为风险
  - tail_ratio_min: float, 默认值 0.1，尾款比例下限，低于此值标记为风险
  - response_time_max: int, 默认值 48，维修响应时间上限（小时），超过此值标记为风险
- judgment_rules: dict, 默认值如下，风险判断标准参数化，支持自定义审核策略：
  - check_price_clarity: bool, 默认值 true，是否检查价格明确性
  - check_payment_milestones: bool, 默认值 true，是否检查付款节点清晰度
  - check_warranty_scope: bool, 默认值 true，是否检查质保范围明确性
  - check_liability_cap: bool, 默认值 true，是否检查赔偿限额对己方不利
  - check_unilateral_exemption: bool, 默认值 true，是否检查单方免责条款
  - check_ip_ownership: bool, 默认值 true，是否检查知识产权归属清晰性
  - check_background_ip_transfer: bool, 默认值 true，是否检查背景知识产权无偿转让风险
  - check_dispute_method: bool, 默认值 true，是否检查争议解决方式对己方有利
  - check_jurisdiction: bool, 默认值 true，是否检查管辖地合理性
- custom_rules: list of dict, 默认值 []，用户可自定义扩展的审核规则列表，每条规则包含：
  - rule_name: string，规则名称
  - condition: string，条件表达式（如 "price > 1000000"）
  - risk_level: string，风险等级（"high" / "medium" / "low"）
  - suggestion: string，修改建议

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: contract, 合同审核, 审合同, 销售合同
- ✅ excludes: 文件名不包含 "contract" 且用户未明确要求审核合同；文件类型不是销售合同
- ✅ 接收用户上传的文件，检查文件名是否包含 "contract" 或用户是否明确要求审核合同。
- ✅ 如果文件名包含 "contract" 或用户明确要求，则进入步骤 2。
- ✅ 否则，不触发本技能，并提示用户：“请提供文件名包含‘contract’的销售合同文件，或明确说明需要审核合同。”
- ✅ 确认文件类型是否为销售合同。
- ✅ 如果文件内容明确为销售合同（例如，包含“销售合同”、“买卖合同”等标题或条款），则进入步骤 3。
- ✅ 如果文件不是销售合同（例如，是劳动合同、租赁合同等），则终止流程，并提示用户：“当前文件不是销售合同，本技能仅适用于销售合同审核。”
- ✅ 读取并解析合同全文，提取关键条款信息，包括但不限于：
- ✅ 根据以下规则对提取的条款进行风险审核：
- ✅ 价格与付款条款：检查价格是否明确、付款节点是否清晰、是否存在不合理的预付款或尾款比例。
- ✅ 质量保证条款：检查质保期是否过长或过短、质保范围是否明确、维修响应时间是否合理。
- ✅ 违约责任条款：检查违约金比例是否过高（通常不超过合同总金额的30%）、赔偿限额是否对己方不利、是否存在单方免责条款。
- ✅ 知识产权条款：检查在合作过程中产生的知识产权归属是否清晰、是否存在将己方背景知识产权无偿转让给对方的风险。
- ✅ 争议解决条款：检查争议解决方式（仲裁或诉讼）是否对己方有利、管辖地是否合理。

### 待确认
- ⏳ [待验证] context: 用户上传文件或提出审核合同的需求时 (`ec_1781834598_32e49f`)
