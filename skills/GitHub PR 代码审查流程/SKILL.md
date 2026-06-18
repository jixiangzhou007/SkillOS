---
name: GitHub PR 代码审查流程
created_at: '2026-06-14T04:18:21Z'
updated_at: '2026-06-14T04:20:20Z'
epistemic:
  source: feasibility://single-shot
  source_type: url_content
  total_claims: 34
  verified: 30
  pending: 4
  preferences: 0
  errors: 0
  claim_ids:
  - ec_1781410821_6b2324
  - ec_1781410823_31ed4e
  - ec_1781410824_e2eca9
  - ec_1781410825_0bfe71
  - ec_1781410826_8f45e4
  - ec_1781410827_e4feee
  - ec_1781410828_17a9bd
  - ec_1781410829_8e35e1
  - ec_1781410830_dd3126
  - ec_1781410831_a70149
  - ec_1781410833_d1bc12
  - ec_1781410834_c2f92d
  - ec_1781410835_03fff7
  - ec_1781410836_e39b31
  - ec_1781410840_1bdc69
  - ec_1781410841_b0638f
  - ec_1781410841_a6b9c4
  - ec_1781410842_10a2d0
  - ec_1781410843_f8d4bd
  - ec_1781410844_318462
  - ec_1781410845_3d3414
  - ec_1781410846_094c9b
  - ec_1781410848_f02395
  - ec_1781410848_53d0d2
  - ec_1781410850_005e0f
  - ec_1781410851_34161c
  - ec_1781410852_fd2fdb
  - ec_1781410853_f68cd2
  - ec_1781410854_9c2e2d
  - ec_1781410855_c7ea6e
  - ec_1781410857_d4f0f9
  - ec_1781410858_101c4d
  - ec_1781410859_e963c3
  - ec_1781410861_14e74f
  pending_ids:
  - ec_1781410841_a6b9c4
  - ec_1781410844_318462
  - ec_1781410858_101c4d
  - ec_1781410859_e963c3
  processed_at: 1781410864.7754843
version: 5
---

# 技能名称：GitHub PR 代码审查流程
## 来源
- feasibility://single-shot
## 核心问题
确保每个合并到 main 分支的 PR 都经过完整检查，避免有问题的代码进入生产环境。

## S_route（决策表）
| 用户意图 | 执行动作 | 按需加载 |
|---------|---------|---------|
| 提交新 PR | 按流程逐项检查 | references/workflow-detail.md |
| PR 描述缺失 | 直接关闭，要求重提 | references/workflow-detail.md |
| 紧急安全漏洞修复 | 走独立安全应急流程 | 不适用本流程 |
| CI 基础设施故障 | 联系 DevOps 修复后重试 | references/workflow-detail.md |
| hotfix 无法 24h 补测试 | 升级技术主管决策 | references/workflow-detail.md |
| 安全组 review 超时 | 升级安全主管 | references/workflow-detail.md |

## S_body
1. **检查 PR 基本信息** — 确认 PR 标题和描述包含 Jira 工单号、变更动机、测试方式、是否 breaking change。如果缺失，在 PR 评论要求补充并暂停审查。
2. **检查 PR 规模** — 统计总行数（新增+删除）。超过 500 行则要求拆分为多个 PR 并关闭当前 PR。
3. **检查特殊类型** — 按顺序检查：
   - 涉及数据库 migration → 需要双人 approve
   - 涉及 auth/权限 → 在 PR 评论 @security 组，等待 review
   - 是 draft 状态 → 允许讨论，不触发 CI 合并检查
   - 是 hotfix → 允许 fast-track 合并，但需 24h 内补测试
   - 包含依赖升级（如 requirements.txt 变更）且混有其他功能 → 要求拆分为独立 PR
4. **检查 CI 状态** — 确认 pytest + ruff 通过。红灯则禁止合并，在 PR 评论说明失败原因。
5. **获取 approve 并合并** — 至少 1 人 approve（涉及 migration 需 2 人）。合并后排查冲突。
6. **输出通知** — 在 Jira 工单评论 PR 链接，在 Slack #eng-releases 发送版本号通知，在 CHANGELOG 追加条目。

## S_trigger
- **触发条件**：开发者在 GitHub 提 PR，target 分支是 main
- **不应触发**：PR 涉及紧急安全漏洞修复（走独立安全应急流程）

## S_params
| 参数 | 说明 | 默认值 |
|------|------|--------|
| target_branch | PR 目标分支 | main |
| max_lines | 单 PR 最大行数 | 500 |
| ci_tools | CI 工具列表 | pytest, ruff |
| notification_channels | 通知渠道 | Jira, Slack #eng-releases, CHANGELOG |

## S_appendix
- references/workflow-detail.md — 完整步骤详解（含异常处理）
- references/examples.md — 示例和用法

## 知识关联
- 这一步与「GitHub PR 代码审查流程」的步骤 1-16 相通（本技能即该流程的重构）
- 这一步与「Customer Refund Processing」的「检查输入完整性」步骤相通（都要求先验证基本信息再继续）
- 这一步与「Export Data from App」的「按顺序检查依赖」步骤相通（都有严格的步骤依赖关系）

## 质量审核
好的，我是技能文档的测试者。现在开始对这份草稿进行攻击性测试。

---

**边界问题:**
1. **PR 描述缺失的处理过于粗暴**：决策表中“PR 描述缺失 → 直接关闭，要求重提”。这没有考虑“描述不完整但包含关键信息”或“提交者是新员工”等边界情况。直接关闭可能引发团队矛盾或丢失上下文。
2. **`max_lines` 边界模糊**：S_body 第2步说“超过 500 行则要求拆分”。如果 PR 刚好 501 行，但其中 400 行是自动生成的 lock 文件或测试数据，是否仍应关闭？草稿未定义“有效代码行数”的过滤规则。
3. **紧急安全漏洞修复的边界**：S_trigge

<!-- Skill DNA principles considered in generation -->

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ feasibility://single-shot
- ✅ 用户意图 → 执行动作
- ✅ 提交新 PR → 按流程逐项检查
- ✅ PR 描述缺失 → 直接关闭，要求重提
- ✅ 紧急安全漏洞修复 → 走独立安全应急流程
- ✅ CI 基础设施故障 → 联系 DevOps 修复后重试
- ✅ hotfix 无法 24h 补测试 → 升级技术主管决策
- ✅ 安全组 review 超时 → 升级安全主管
- ✅ 检查 PR 基本信息 — 确认 PR 标题和描述包含 Jira 工单号、变更动机、测试方式、是否 breaking change。如果缺失，在 PR 评论要求补充并暂停审查。
- ✅ 检查 PR 规模 — 统计总行数（新增+删除）。超过 500 行则要求拆分为多个 PR 并关闭当前 PR。
- ✅ 检查特殊类型 — 按顺序检查：
- ✅ 涉及数据库 migration → 需要双人 approve
- ✅ 涉及 auth/权限 → 在 PR 评论 @security 组，等待 review
- ✅ 是 draft 状态 → 允许讨论，不触发 CI 合并检查
- ✅ 是 hotfix → 允许 fast-track 合并，但需 24h 内补测试

### 待确认
- 📋 [evidence] 检查 CI 状态 — 确认 pytest + ruff 通过。红灯则禁止合并，在 PR 评论说明失败原因。 (`ec_1781410841_a6b9c4`)
- 📋 [evidence] 触发条件：开发者在 GitHub 提 PR，target 分支是 main (`ec_1781410844_318462`)
- ⏳ [待验证] PR 描述缺失的处理过于粗暴：决策表中“PR 描述缺失 → 直接关闭，要求重提”。这没有考虑“描述不完整但包含关键信息”或“提交者是新员工”等边界情况。直接关闭可能引发团队矛盾或丢失上下文。 (`ec_1781410858_101c4d`)
- ⏳ [待验证] max_lines 边界模糊：S_body 第2步说“超过 500 行则要求拆分”。如果 PR 刚好 501 行，但其中 400 行是自动生成的 lock 文件或测试数据，是否仍应关闭？草稿未定义“有效代码行数”的过滤规则。 (`ec_1781410859_e963c3`)
