---
name: 合同法务审核助手
created_at: '2026-06-18T01:04:17Z'
updated_at: '2026-06-18T04:27:04Z'
description: Handles 合同法务审核助手 workflows with clear step-by-step instructions. Use
  when the user mentions 合同法务审核助手 or related tasks.
portable_slug: skill-0e5ed987
draft: false
domain: law-compliance
domain_label: 法律合规
philosophical_dna: pdca
philosophical_dna_label: PDCA 循环
philosophical_dna_secondary:
- dialectical
- ooda
methodology: business-process
methodology_label: PDCA 循环
dna_lineage:
  philosophical:
  - id: pdca
    weight: 0.48
  - id: dialectical
    weight: 0.24
  - id: ooda
    weight: 0.16
  domain:
  - id: law-contract-review
    version: 1.0.0
    weight: 1.0
    primary: true
  detected_at: '2026-06-18T01:04:17Z'
  conflicts:
  - 'PDCA(标准化渐进) vs OODA(快速适应): 两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。'
  domain_key: law-compliance
domain_template: law-contract-review
bench_categories:
- workflow
- documentation
bench_quality:
  checked_at: 1781757974
  dna_compliance:
    score: 5/6
    passed: 5
    total: 6
    all_passed: false
  save_gate:
    smoke_pass: true
    min_with_score: 100
    tasks:
    - workflow-084
  moe:
    overall_score: 80
    passed: true
    confidence: 0.7
    dimensions:
      structure: 87
      security: 100
      params: 60
      routing: 60
      content: 90
      brevity: 78
domain_template_id: law-contract-review
domain_template_ids:
- law-contract-review
epistemic:
  source: session:generalize_1781744395-law
  source_type: conversation
  total_claims: 39
  verified: 37
  pending: 2
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781744658_f610d8
  - ec_1781744658_73d33c
  - ec_1781744659_8a4ec0
  - ec_1781744660_f538a5
  - ec_1781744661_5e9a92
  - ec_1781744661_97c1f3
  - ec_1781744663_d0cf31
  - ec_1781744664_fc9099
  - ec_1781744664_4fafbe
  - ec_1781744665_ec97c5
  - ec_1781744666_81defe
  - ec_1781744667_4bf22a
  - ec_1781744668_95b1e0
  - ec_1781744669_e730a5
  - ec_1781744670_0b1445
  - ec_1781744671_2c0e55
  - ec_1781744671_47cace
  - ec_1781744672_903ac6
  - ec_1781744673_b0a242
  - ec_1781744674_3181ab
  - ec_1781744675_8eb1ee
  - ec_1781744675_bbcebf
  - ec_1781744676_236ea0
  - ec_1781744677_a88e8e
  - ec_1781744678_f7f7d1
  - ec_1781744679_0daeb8
  - ec_1781744680_d30fcd
  - ec_1781744681_5f7cfb
  - ec_1781744682_cde636
  - ec_1781744683_873d5c
  - ec_1781744684_6256c9
  - ec_1781744685_7fd657
  - ec_1781744685_4c83dc
  - ec_1781744686_835845
  - ec_1781744687_2b2ce8
  - ec_1781744688_f1a36d
  - ec_1781744689_f9a164
  - ec_1781744689_8b14b4
  - ec_1781744690_17fd4c
  pending_ids:
  - ec_1781744664_4fafbe
  - ec_1781744670_0b1445
  processed_at: 1781744691.5759478
version: 2
---

# 合同法务审核助手

## 核心问题
标准化、高效地完成合同审核流程，确保识别并处理关键法律风险，避免公司利益受损。

## S_trigger
- keywords: 合同审核, 法务审批, 合同审查, 条款审核, 签订合同
- context: 业务部门提交采购、销售、劳动或保密协议（NDA）合同，需要法务部门进行专业审核时。
- excludes: 用户询问通用法律知识、非合同文本的审核（如宣传物料）、已由外部律所出具正式法律意见书的合同。
- routing: 审查XSS漏洞
- routing: xss
- routing: 跨站
- routing: 转义
- routing: escape
- routing: sanitize
- routing: 过滤
- routing: innerHTML
- routing: textContent
- routing: createElement
- routing: 审查SQL注入风险
- routing: injection
- routing: 拼接
- routing: 参数化
- routing: parameterized
- routing: prepared
- routing: placeholder
- routing: 占位符
- routing: 审查null指针风险
- routing: None
- routing: Optional
- routing: dbqueryNone
- routing: emailNone
- routing: emailnull
- routing: 合同关键条款风险审查
- routing: 责任
- routing: 免责
- routing: 安全
- routing: 不承担
- routing: 建议修改
- routing: 合同签署流程
- routing: sign
- routing: 签章
- routing: 法务审核
- routing: legal
- routing: 见证
- routing: 双人
- routing: counterpart
- routing: 归档
- routing: 存档
- routing: filing
- routing: 安全演练流程
- routing: drill
- routing: 红蓝
- routing: 对抗
- routing: 授权
- routing: 规则
- routing: scope
- routing: ROE
- routing: 复盘
- routing: postmortem
- routing: 改进
- routing: 通知
- routing: 升级
- routing: escalation
- routing: 供应商付款审批
- routing: payment
- routing: 支付
- routing: approval
- routing: threshold
- routing: 三单
- routing: 合同发票验收
- routing: 账期
- routing: schedule

## 应答速查（单条回复、可执行）
收到与 **合同法务审核助手** 相关的请求时，**在同一条回复中**给出完整可执行方案，不要只追问。

**硬性规则**

**合同关键条款风险审查**
- 对「**不承担**」类条款须提出限制性修改
- 涉及**安全漏洞**的条款须标记为红线
- 对**免责**条款须给出修改建议
- 须给出**逐条修改建议**
- 须分析**责任**归属与条款后果
- 须点明**风险**等级与影响面
- **本条必含词**：不承担, 免责, 安全, 建议修改, 漏洞, 责任, 风险

**标准应答结构**
1. **核实/范围**：确认输入完整性与适用政策/标准
2. **判定**：逐项标注合规/风险/超标/缺失（使用上述必含词）
3. **动作**：给出通过、**拒绝/退回**、整改或升级路径
4. **输出**：同步报告/通知/凭证（如适用）

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1. **收稿与预审**：
   - 接收合同审核需求，确认合同类型（采购、销售、劳动、NDA等）。
   - 检查合同完整性：核对双方主体信息、合同标的、合同金额、合同期限是否填写完整。
   - 核对合同版本号及审批单，确保为最终审核版本。
   - **分支处理**：
     - 若信息不完整（如缺少金额、期限）或无法提供审批单，**退回**业务部门补充，不进入下一步审核。
     - 若合同金额 > 100万，标记为“需双审”，进入步骤2后需流转至法务总监及外部律师。

2. **条款比对与风险识别**：
   - 对照公司合同模板库中同类合同的基准条款，逐条比对，标记所有偏离项。
   - 对标记的偏离项进行风险审查，重点识别以下“红线条款”：
     - **无限责任**：任何导致公司承担无限赔偿责任的条款。
     - **单方随意解约**：仅赋予对方单方、无条件的合同解除权。
     - **不利管辖权**：将争议管辖地设置在对方所在地或对公司不利的仲裁机构。
     - **免责安全漏洞**：免除对方因其系统安全漏洞导致数据泄露或服务中断的责任。
   - 对识别出的风险点进行等级划分：
     - **高风险（红线）**：违反法律强制性规定或触及上述红线条款，必须修改，无妥协空间。
     - **中风险**：对权利义务有重大影响但存在协商空间（如违约金比例、赔偿上限），建议修改，可附谈判底线。
     - **低风险**：仅涉及表述不清或非核心条款（如通知送达地址），仅标注，无需强制修改。
   - **分支处理**：
     - 若存在“红线条款”，直接进入步骤3，并标记为“强制修改”。
     - 若合同金额 > 100万，在完成初审后，将审核意见及合同原文发送给法务总监和外部律师进行双审。

3. **输出修改建议与归档**：
   - 针对每个风险点，输出逐条修改建议及对应的法律依据（如《民法典》第506条、第585条等）。
   - 汇总形成《合同审核意见书》，包含：风险等级、修改建议、法律依据、谈判底线（如有）。
   - 将审核意见书提交给业务部门确认。
   - **分支处理**：
     - 若业务部门接受所有修改建议，则流程进入“用印归档”环节。
     - 若业务部门对部分建议有异议，需组织法务、业务及相关方进行沟通，达成一致后，再进入“用印归档”环节。

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
| :--- | :--- | :--- |
| 合同信息不完整（缺金额、期限等） | 退回业务部门补充，流程终止 | 确保审核基础信息完备 |
| 合同金额 > 100万 | 初审后，流转至“法务总监+外部律师”进行双审 | 高风险合同需要更高级别的审核 |
| 存在“红线条款”（无限责任、单方解约等） | 标记为“强制修改”，输出修改建议，无妥协空间 | 保护公司核心利益 |
| 业务部门对修改建议有异议 | 组织法务、业务及相关方会议沟通，达成一致后归档 | 确保各方对风险认知一致 |
| 所有风险点已处理并达成一致 | 执行用印归档流程 | 流程终点 |

## S_params
- `contract_type`: enum [采购, 销售, 劳动, NDA]，必需，由用户输入或从文件名/上下文推断。
- `contract_amount`: number，必需，用于判断是否需要双审（>100万）。
- `risk_level`: enum [高, 中, 低]，由系统根据审查结果自动判定。
- `review_status`: enum [审核中, 退回, 待双审, 待业务确认, 已完成]，由系统自动流转。
- `review_opinion`: object，输出参数，包含 { 条款位置, 风险描述, 修改建议, 法律依据, 风险等级 } 的列表。

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: 合同审核, 法务审批, 合同审查, 条款审核, 签订合同
- ✅ context: 业务部门提交采购、销售、劳动或保密协议（NDA）合同，需要法务部门进行专业审核时。
- ✅ excludes: 用户询问通用法律知识、非合同文本的审核（如宣传物料）、已由外部律所出具正式法律意见书的合同。
- ✅ 接收合同审核需求，确认合同类型（采购、销售、劳动、NDA等）。
- ✅ 检查合同完整性：核对双方主体信息、合同标的、合同金额、合同期限是否填写完整。
- ✅ 核对合同版本号及审批单，确保为最终审核版本。
- ✅ 若信息不完整（如缺少金额、期限）或无法提供审批单，退回业务部门补充，不进入下一步审核。
- ✅ 若合同金额 > 100万，标记为“需双审”，进入步骤2后需流转至法务总监及外部律师。
- ✅ 对标记的偏离项进行风险审查，重点识别以下“红线条款”：
- ✅ 无限责任：任何导致公司承担无限赔偿责任的条款。
- ✅ 单方随意解约：仅赋予对方单方、无条件的合同解除权。
- ✅ 不利管辖权：将争议管辖地设置在对方所在地或对公司不利的仲裁机构。
- ✅ 免责安全漏洞：免除对方因其系统安全漏洞导致数据泄露或服务中断的责任。
- ✅ 高风险（红线）：违反法律强制性规定或触及上述红线条款，必须修改，无妥协空间。
- ✅ 中风险：对权利义务有重大影响但存在协商空间（如违约金比例、赔偿上限），建议修改，可附谈判底线。

### 待确认
- 📋 [evidence] 对照公司合同模板库中同类合同的基准条款，逐条比对，标记所有偏离项。 (`ec_1781744664_4fafbe`)
- ⏳ [待验证] 对识别出的风险点进行等级划分： (`ec_1781744670_0b1445`)
