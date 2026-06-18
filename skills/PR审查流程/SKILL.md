---
name: PR审查流程
created_at: '2026-06-14T04:19:04Z'
updated_at: '2026-06-14T04:19:04Z'
epistemic:
  source: feasibility-dialogue-test
  source_type: conversation
  total_claims: 28
  verified: 26
  pending: 2
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781410746_500024
  - ec_1781410746_10b020
  - ec_1781410749_23d5a2
  - ec_1781410751_efc9ff
  - ec_1781410752_ff97d4
  - ec_1781410753_c45c74
  - ec_1781410755_359508
  - ec_1781410756_3c343c
  - ec_1781410757_e6bdd1
  - ec_1781410759_5d4e3a
  - ec_1781410760_fa1c9d
  - ec_1781410761_b6a835
  - ec_1781410762_0252b1
  - ec_1781410763_343de5
  - ec_1781410764_9b8ef8
  - ec_1781410766_282b6f
  - ec_1781410767_95bd9a
  - ec_1781410768_f5e07c
  - ec_1781410769_af4025
  - ec_1781410770_6dcf4b
  - ec_1781410771_409bab
  - ec_1781410772_ff7946
  - ec_1781410774_83b665
  - ec_1781410775_c431d0
  - ec_1781410776_ab84e8
  - ec_1781410778_52d7dd
  - ec_1781410779_5e0540
  - ec_1781410780_d2ad68
  pending_ids:
  - ec_1781410746_10b020
  - ec_1781410759_5d4e3a
  processed_at: 1781410782.0308533
version: 1
---

# 技能名称：PR审查流程
## 核心问题
规范后端团队基于Python+FastAPI的GitHub PR审查与合并流程，确保代码质量与协作效率。

## S_body
1. **检查PR描述完整性**：审查者确认PR描述是否包含变更动机、测试方式、是否breaking change。若缺失，要求开发者补充。
2. **检查CI状态**：确认CI（pytest和ruff）是否通过。若CI红灯，不允许merge；若为draft PR，允许先讨论。
3. **检查PR规模**：若改动超过500行，要求开发者拆分PR。
4. **检查数据库迁移**：若涉及数据库migration，必须获得双人approve。
5. **检查安全相关变更**：若涉及auth或权限，必须@security组review。
6. **处理hotfix**：若为hotfix，可走fast-track合并，但合并后24小时内必须补测试。
7. **处理依赖升级**：若为依赖升级，必须单独提PR，不与其他功能混提。
8. **合并后操作**：在Jira工单评论PR链接，发Slack #eng-releases通知版本号，并在CHANGELOG对应章节追加条目。

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| PR描述不完整 | 要求开发者补充 | 步骤1 |
| CI红灯 | 不允许merge；若为draft PR可讨论 | 步骤2 |
| 改动超过500行 | 要求拆PR | 步骤3 |
| 涉及数据库迁移 | 必须双人approve | 步骤4 |
| 涉及auth/权限 | 必须@security组review | 步骤5 |
| hotfix | 走fast-track，合并后24h内补测试 | 步骤6 |
| 依赖升级 | 单独提PR | 步骤7 |
| 合并完成 | 评论Jira、发Slack、更新CHANGELOG | 步骤8 |

## S_trigger
- keywords: PR, pull request, 审查, merge, 合并, 代码审查, FastAPI, pytest, ruff, Jira, CI, hotfix, 数据库迁移, 依赖升级
- context: 开发者在GitHub上提交PR，target分支为main，需要后端团队按规范进行审查和合并，涉及CI检查、规模控制、安全审查、合并后通知等环节。

## S_params
- pr_url: string, 无默认值, PR的GitHub链接
- target_branch: string, 默认值"main", PR的目标分支
- change_lines: integer, 无默认值, PR改动的代码行数
- has_migration: boolean, 默认值false, 是否涉及数据库迁移
- is_security_related: boolean, 默认值false, 是否涉及auth或权限
- is_hotfix: boolean, 默认值false, 是否为hotfix
- is_dependency_upgrade: boolean, 默认值false, 是否为依赖升级
- jira_ticket_id: string, 无默认值, 关联的Jira工单号
- release_version: string, 无默认值, 本次发布的版本号

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ 检查PR描述完整性：审查者确认PR描述是否包含变更动机、测试方式、是否breaking change。若缺失，要求开发者补充。
- ✅ 检查PR规模：若改动超过500行，要求开发者拆分PR。
- ✅ 检查数据库迁移：若涉及数据库migration，必须获得双人approve。
- ✅ 检查安全相关变更：若涉及auth或权限，必须@security组review。
- ✅ 处理hotfix：若为hotfix，可走fast-track合并，但合并后24小时内必须补测试。
- ✅ 处理依赖升级：若为依赖升级，必须单独提PR，不与其他功能混提。
- ✅ 合并后操作：在Jira工单评论PR链接，发Slack #eng-releases通知版本号，并在CHANGELOG对应章节追加条目。
- ✅ 用户意图/条件 → 执行动作
- ✅ CI红灯 → 不允许merge；若为draft PR可讨论
- ✅ 改动超过500行 → 要求拆PR
- ✅ 涉及数据库迁移 → 必须双人approve
- ✅ 涉及auth/权限 → 必须@security组review
- ✅ hotfix → 走fast-track，合并后24h内补测试
- ✅ 依赖升级 → 单独提PR
- ✅ 合并完成 → 评论Jira、发Slack、更新CHANGELOG

### 待确认
- 📋 [evidence] 检查CI状态：确认CI（pytest和ruff）是否通过。若CI红灯，不允许merge；若为draft PR，允许先讨论。 (`ec_1781410746_10b020`)
- ⏳ [待验证] PR描述不完整 → 要求开发者补充 (`ec_1781410759_5d4e3a`)
