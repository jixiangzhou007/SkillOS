---
name: code-review-test
created_at: '2026-06-27T02:42:40Z'
updated_at: '2026-06-27T02:42:40Z'
domain: computer-science
domain_label: 计算机科学
philosophical_dna: ooda
philosophical_dna_label: OODA 循环
philosophical_dna_secondary:
- reductionist
- scientific-method
methodology: diagnostic
methodology_label: OODA 循环
dna_lineage:
  philosophical:
  - id: ooda
    weight: 0.44
  - id: reductionist
    weight: 0.22
  - id: scientific-method
    weight: 0.15
  domain:
  - id: code-review-pr
    version: 1.17.0
    weight: 0.69
    primary: true
  - id: security-audit
    version: 1.1.0
    weight: 0.23
    primary: false
  - id: law-contract-review
    version: 1.13.0
    weight: 0.08
    primary: false
  detected_at: '2026-06-27T02:42:40Z'
  conflicts:
  - 'PDCA(标准化渐进) vs OODA(快速适应): 两者都是迭代循环，但节奏不同。请明确本流程偏向SOP化(PDCA)还是实时响应(OODA)。'
  domain_key: computer-science
epistemic:
  source: code-review-test
  source_type: llm_generated
  total_claims: 6
  verified: 0
  pending: 6
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1782528160_fd3501
  - ec_1782528160_21dc73
  - ec_1782528160_f89ebc
  - ec_1782528160_a31fea
  - ec_1782528161_29ac5f
  - ec_1782528161_ed0f9a
  pending_ids:
  - ec_1782528160_fd3501
  - ec_1782528160_21dc73
  - ec_1782528160_f89ebc
  - ec_1782528160_a31fea
  - ec_1782528161_29ac5f
  - ec_1782528161_ed0f9a
  processed_at: 1782528161.3615553
version: 1
---

# Python Code Review
## trigger
审核Python代码变更时触发

## S_body
1. 运行pytest检查测试覆盖
2. ruff lint检查代码规范  
3. mypy检查类型注解
4. 人工审查逻辑和安全
5. 合并到main分支

## S_route
| 条件 | 动作 |
|------|------|
| E/F级lint错误 | 必须修复才能继续 |
| 测试失败 | 回退修改，重新提交 |

## S_trigger
- keywords: code review, PR, 代码审查, ruff, mypy

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 待确认
- ⏳ [待验证] 运行pytest检查测试覆盖 (`ec_1782528160_fd3501`)
- ⏳ [待验证] ruff lint检查代码规范 (`ec_1782528160_21dc73`)
- ⏳ [待验证] 条件 → 动作 (`ec_1782528160_f89ebc`)
- ⏳ [待验证] E/F级lint错误 → 必须修复才能继续 (`ec_1782528160_a31fea`)
- 📋 [evidence] 测试失败 → 回退修改，重新提交 (`ec_1782528161_29ac5f`)
- ⏳ [待验证] keywords: code review, PR, 代码审查, ruff, mypy (`ec_1782528161_ed0f9a`)
