---
name: contract-review-external
created_at: '2026-06-19T19:31:20Z'
updated_at: '2026-06-19T19:31:20Z'
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
    version: 1.10.0
    weight: 0.86
    primary: true
  - id: code-review-pr
    version: 1.13.0
    weight: 0.14
    primary: false
  detected_at: '2026-06-19T19:31:20Z'
  domain_key: law
epistemic:
  source: contract-review-external
  source_type: llm_generated
  total_claims: 13
  verified: 0
  pending: 13
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781897480_685877
  - ec_1781897480_127b28
  - ec_1781897480_34712e
  - ec_1781897480_63a0ee
  - ec_1781897481_5bb7cb
  - ec_1781897481_5cf437
  - ec_1781897481_2914dc
  - ec_1781897481_34ddb3
  - ec_1781897481_bba823
  - ec_1781897482_cde8d0
  - ec_1781897482_e1ad21
  - ec_1781897482_12efa0
  - ec_1781897482_c59739
  pending_ids:
  - ec_1781897480_685877
  - ec_1781897480_127b28
  - ec_1781897480_34712e
  - ec_1781897480_63a0ee
  - ec_1781897481_5bb7cb
  - ec_1781897481_5cf437
  - ec_1781897481_2914dc
  - ec_1781897481_34ddb3
  - ec_1781897481_bba823
  - ec_1781897482_cde8d0
  - ec_1781897482_e1ad21
  - ec_1781897482_12efa0
  - ec_1781897482_c59739
  processed_at: 1781897482.7773008
version: 1
---

---
name: contract-review
description: Review legal contracts for risks, compliance, and negotiable terms. Use when user mentions contract, agreement, legal review, 合同, 协议.
---

# 合同审核
## S_body
1. [动作] 扫描合同全文，标记关键条款（金额、期限、违约、管辖）
2. [门禁] 合同主体信息必须完整 → 不完整则中止
3. [动作] 检查违约金比例是否超过合同总金额30%
4. [动作] 检查管辖法院是否为甲方所在地
5. [动作] 检查是否存在单方免责的格式条款
6. [动作] 汇总风险项，按高/中/低分级
7. [动作] 生成审核报告

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 违约金>30% | 建议修改 | 民法典585条 |
| 管辖法院在对方所在地 | 建议改为甲方 | |
| 格式条款单方免责 | 标注高风险 | |

## S_trigger
- keywords: 审合同, 合同审核, contract review, 审核协议
- context: 收到合同需要法务审核
- excludes: 劳动合同, 租赁合同

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 待确认
- ⏳ [待验证] [动作] 扫描合同全文，标记关键条款（金额、期限、违约、管辖） (`ec_1781897480_685877`)
- ⏳ [待验证] [门禁] 合同主体信息必须完整 → 不完整则中止 (`ec_1781897480_127b28`)
- ⏳ [待验证] [动作] 检查违约金比例是否超过合同总金额30% (`ec_1781897480_34712e`)
- ⏳ [待验证] [动作] 检查管辖法院是否为甲方所在地 (`ec_1781897480_63a0ee`)
- ⏳ [待验证] [动作] 检查是否存在单方免责的格式条款 (`ec_1781897481_5bb7cb`)
- ⏳ [待验证] [动作] 汇总风险项，按高/中/低分级 (`ec_1781897481_5cf437`)
- ⏳ [待验证] 条件 → 动作 (`ec_1781897481_2914dc`)
- ⏳ [待验证] 违约金>30% → 建议修改 (`ec_1781897481_34ddb3`)
- ⏳ [待验证] 管辖法院在对方所在地 → 建议改为甲方 (`ec_1781897481_bba823`)
- ⏳ [待验证] 格式条款单方免责 → 标注高风险 (`ec_1781897482_cde8d0`)
- ⏳ [待验证] keywords: 审合同, 合同审核, contract review, 审核协议 (`ec_1781897482_e1ad21`)
- ⏳ [待验证] context: 收到合同需要法务审核 (`ec_1781897482_12efa0`)
- ⏳ [待验证] excludes: 劳动合同, 租赁合同 (`ec_1781897482_c59739`)
