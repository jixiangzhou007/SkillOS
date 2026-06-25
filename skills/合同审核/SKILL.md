---
name: 合同审核
created_at: '2026-06-15T06:04:59Z'
updated_at: '2026-06-23T12:12:51Z'
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
    version: 1.13.0
    weight: 0.89
    primary: true
  - id: media-publish
    version: 1.0.0
    weight: 0.11
    primary: false
  detected_at: '2026-06-23T12:12:51Z'
  domain_key: law
bench_categories:
- documentation
- workflow
bench_quality:
  checked_at: 1782216781
  dna_compliance:
    score: 2/6
    passed: 2
    total: 6
    all_passed: false
  save_gate:
    smoke_pass: false
    min_with_score: 0
    tasks:
    - workflow-080
  moe:
    overall_score: 60
    passed: false
    confidence: 0.7
    dimensions:
      structure: 60
      security: 60
      params: 60
      routing: 60
      content: 60
      brevity: 60
    boost_rounds:
    - boosted: true
      expert_key: structure
      before_score: 60
      section: S_body
      round: 1
      score_before: 60
      soft_boost: false
      score_after: 60
    - boosted: true
      expert_key: structure
      before_score: 60
      section: S_body
      round: 2
      score_before: 60
      soft_boost: false
      score_after: 60
epistemic:
  source: session:test-meta-no-restart
  source_type: conversation
  total_claims: 4
  verified: 0
  pending: 4
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1782216771_2c8ace
  - ec_1782216772_74a092
  - ec_1782216773_efe2fc
  - ec_1782216773_b64c16
  pending_ids:
  - ec_1782216771_2c8ace
  - ec_1782216772_74a092
  - ec_1782216773_efe2fc
  - ec_1782216773_b64c16
  processed_at: 1782216774.387098
version: 22
---

---
name: skill-aecb7055
description: Handles 合同审核 workflows with clear step-by-step instructions. Use when
  the user mentions 合同审核 or related tasks.
metadata:
  skillos_version: 0.3.0
  display_name: 合同审核
  generated_by: SkillOS
  skillos_slug: skill-aecb7055
---

# 合同审核

## S_body
<QUESTION>合同审核时验收条款有哪些要点？</QUESTION>
<SKILL_DRAFT>
```skill_doc
# 技能名称：合同审核

## S_body
1. 检查条款
```
</SKILL_DRAFT>

## S_body
1. 检查条款
```
</SKILL_DRAFT>

## S_params
- user_message: string — 用户请求或对话上下文

## Outputs
- status: enum — 执行结果（success / pending / rejected / escalated）
- message: string — 给用户或下游系统的摘要说明
- audit_notes: string — 关键操作记录（可选）

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 待确认
- ⏳ [待验证] user_message: string — 用户请求或对话上下文 (`ec_1782216771_2c8ace`)
- ⏳ [待验证] status: enum — 执行结果（success / pending / rejected / escalated） (`ec_1782216772_74a092`)
- ⏳ [待验证] message: string — 给用户或下游系统的摘要说明 (`ec_1782216773_efe2fc`)
- ⏳ [待验证] audit_notes: string — 关键操作记录（可选） (`ec_1782216773_b64c16`)
