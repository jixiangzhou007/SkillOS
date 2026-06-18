---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-18T16:24:41Z'
description: Handles 合同审核 workflows with clear step-by-step instructions. Use when
  the user mentions 合同审核 or related tasks.
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
    version: 1.4.0
    weight: 0.85
    primary: true
  - id: media-publish
    version: 1.0.0
    weight: 0.15
    primary: false
  detected_at: '2026-06-18T16:24:41Z'
  domain_key: law
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1781799944
  dna_compliance:
    score: 6/6
    passed: 6
    total: 6
    all_passed: true
  save_gate:
    smoke_pass: false
    min_with_score: 73
    tasks:
    - workflow-080
  moe:
    overall_score: 83
    passed: true
    confidence: 0.7
    dimensions:
      structure: 87
      security: 100
      params: 88
      routing: 60
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
      score_after: 83
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 40
  verified: 33
  pending: 5
  preferences: 2
  errors: 0
  claim_ids:
  - ec_1781799882_e2f8d5
  - ec_1781799882_99d7c6
  - ec_1781799883_ad5ff8
  - ec_1781799884_3d4692
  - ec_1781799885_3f5570
  - ec_1781799885_17ce5a
  - ec_1781799886_022f62
  - ec_1781799887_3ac3c1
  - ec_1781799888_59c557
  - ec_1781799889_5b58cb
  - ec_1781799890_103dc7
  - ec_1781799890_3af124
  - ec_1781799891_8ffeea
  - ec_1781799892_70f619
  - ec_1781799893_c3b7ed
  - ec_1781799893_92b67b
  - ec_1781799894_805cd1
  - ec_1781799895_5d6024
  - ec_1781799896_ed1717
  - ec_1781799897_bde101
  - ec_1781799898_f7cbfb
  - ec_1781799898_1631a3
  - ec_1781799899_bbd858
  - ec_1781799900_737972
  - ec_1781799901_ed751c
  - ec_1781799902_d0fa9a
  - ec_1781799902_63deea
  - ec_1781799904_40b68c
  - ec_1781799905_1c8d91
  - ec_1781799906_6249fe
  - ec_1781799907_f3e8cd
  - ec_1781799908_e79cf9
  - ec_1781799909_46b650
  - ec_1781799910_4be44c
  - ec_1781799911_1d4ae2
  - ec_1781799911_5c221b
  - ec_1781799911_5660d2
  - ec_1781799912_09fab1
  - ec_1781799913_2d3363
  - ec_1781799914_459f3b
  pending_ids:
  - ec_1781799884_3d4692
  - ec_1781799885_17ce5a
  - ec_1781799891_8ffeea
  - ec_1781799893_92b67b
  - ec_1781799898_1631a3
  processed_at: 1781799916.5989025
version: 14
---

# 合同审核

## 核心问题
快速识别销售合同中的关键风险条款，确保我方权益。

## S_trigger
- keywords: contract, 合同, 销售合同, 审核合同, 审合同, 合同风险
- context: 用户上传文件或粘贴文本，意图为审查合同条款风险
- excludes: 用户要求起草合同、修改合同内容、或进行法律咨询

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1.  接收用户提供的文件或文本，检查文件名是否包含 "contract"。
    - 如果文件名包含 "contract"，则继续执行步骤2。
    - 如果文件名不包含 "contract"，则询问用户是否仍要执行合同审核流程；若用户确认，则继续执行步骤2；若用户否认，则终止流程并返回提示。
2.  识别合同中的关键条款，并逐一进行风险审查：
    - **价格条款**：检查合同金额、付款方式、付款周期、发票类型是否明确且符合我方标准。
    - **质保条款**：检查质保期限、质保范围、质保责任划分是否合理。
    - **责任条款**：检查违约赔偿上限、责任免除情形、争议解决方式（仲裁或诉讼）及管辖地。
    - **知识产权条款**：检查知识产权归属、使用许可范围、侵权责任承担方。
    - **违约金条款**：检查违约金比例、计算方式、触发条件是否对等。
3.  针对每个条款，输出风险评级（高/中/低）和具体风险描述。
    - 如果条款缺失，标记为“缺失”，并提示建议补充。
    - 如果条款存在但对我方不利，标记为“高风险”，并给出修改建议。
4.  汇总所有条款的审核结果，生成一份结构化的审核报告。如果审核过程中调用外部API（如条款数据库）超时，则重试3次，每次间隔2秒；若3次后仍超时，则返回错误提示：“条款数据库连接超时，请稍后重试或手动检查条款。”

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| 用户提供文件名包含 "contract" 的销售合同 | 执行完整的合同审核流程（S_body 步骤 1-4） | 标准触发场景 |
| 用户提供文件名不包含 "contract" 的合同文件 | 询问用户是否仍要执行审核流程 | 避免误触发 |
| 用户直接粘贴合同文本 | 跳过文件名检查，直接执行条款审核（S_body 步骤 2-4） | 处理非文件输入 |
| 用户要求审核特定条款（如“只看违约责任”） | 仅执行 S_body 步骤 2 中的对应条款审查，并输出结果 | 支持定向审核 |
| 审核过程中API超时 | 重试3次，每次间隔2秒；若仍超时则返回错误提示 | 异常处理分支 |

## S_params
- file_path: string, 空字符串, 待审核合同的文件路径
- contract_text: string, 空字符串, 待审核合同的文本内容
- focus_clause: string, "all", 指定要审核的条款，可选值: "price", "warranty", "liability", "ip", "penalty", "all"
- risk_threshold: string, "medium", 风险评级输出阈值，低于该级别的风险不输出，可选值: "low", "medium", "high"
- retry_max_attempts: integer, 3, API超时最大重试次数
- retry_interval_seconds: integer, 2, 每次重试间隔秒数
- price_min_amount: float, 0.0, 价格条款中合同金额的最小值阈值（低于此值标记为低风险）
- price_max_amount: float, 10000000.0, 价格条款中合同金额的最大值阈值（高于此值标记为高风险）
- warranty_min_months: integer, 12, 质保条款中质保期限的最小月数阈值（低于此值标记为高风险）
- liability_cap_ratio: float, 1.0, 责任条款中违约赔偿上限占合同金额的比例阈值（高于此值标记为高风险）
- penalty_min_ratio: float, 0.001, 违约金条款中日违约金比例的最小值阈值（低于此值标记为低风险）
- penalty_max_ratio: float, 0.005, 违约金条款中日违约金比例的最大值阈值（高于此值标记为高风险）
- ip_ownership_default: string, "我方", 知识产权条款中默认归属方，可选值: "我方", "对方", "双方共有"
- dispute_resolution_preference: string, "仲裁", 争议解决方式偏好，可选值: "仲裁", "诉讼"
- dispute_venue_preference: string, "我方所在地", 争议解决管辖地偏好，可选值: "我方所在地", "对方所在地", "第三方中立地"

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: contract, 合同, 销售合同, 审核合同, 审合同, 合同风险
- ✅ context: 用户上传文件或粘贴文本，意图为审查合同条款风险
- ✅ excludes: 用户要求起草合同、修改合同内容、或进行法律咨询
- ✅ 如果文件名包含 "contract"，则继续执行步骤2。
- ✅ 识别合同中的关键条款，并逐一进行风险审查：
- ✅ 价格条款：检查合同金额、付款方式、付款周期、发票类型是否明确且符合我方标准。
- ✅ 质保条款：检查质保期限、质保范围、质保责任划分是否合理。
- ✅ 责任条款：检查违约赔偿上限、责任免除情形、争议解决方式（仲裁或诉讼）及管辖地。
- ✅ 知识产权条款：检查知识产权归属、使用许可范围、侵权责任承担方。
- ✅ 违约金条款：检查违约金比例、计算方式、触发条件是否对等。
- ✅ 如果条款缺失，标记为“缺失”，并提示建议补充。
- ✅ 如果条款存在但对我方不利，标记为“高风险”，并给出修改建议。
- ✅ 用户意图/条件 → 执行动作
- ✅ 用户提供文件名包含 "contract" 的销售合同 → 执行完整的合同审核流程（S_body 步骤 1-4）
- ✅ 用户提供文件名不包含 "contract" 的合同文件 → 询问用户是否仍要执行审核流程

### 待确认
- 📋 [evidence] 接收用户提供的文件或文本，检查文件名是否包含 "contract"。 (`ec_1781799884_3d4692`)
- 📋 [evidence] 如果文件名不包含 "contract"，则询问用户是否仍要执行合同审核流程；若用户确认，则继续执行步骤2；若用户否认，则终止流程并返回提示。 (`ec_1781799885_17ce5a`)
- ⏳ [待验证] 针对每个条款，输出风险评级（高/中/低）和具体风险描述。 (`ec_1781799891_8ffeea`)
- 📋 [evidence] 汇总所有条款的审核结果，生成一份结构化的审核报告。如果审核过程中调用外部API（如条款数据库）超时，则重试3次，每次间隔2秒；若3次后仍超时，则返回错误提示：“条款数据库连接超时，请稍后重试或手动检查条款。” (`ec_1781799893_92b67b`)
- 📋 [evidence] 审核过程中API超时 → 重试3次，每次间隔2秒；若仍超时则返回错误提示 (`ec_1781799898_1631a3`)
- 📋 [preference] dispute_resolution_preference: string, "仲裁", 争议解决方式偏好，可选值: "仲裁", "诉讼" (`ec_1781799911_5c221b`)
- 📋 [preference] dispute_venue_preference: string, "我方所在地", 争议解决管辖地偏好，可选值: "我方所在地", "对方所在地", "第三方中立地" (`ec_1781799911_5660d2`)
