---
name: GitHub Pull
created_at: '2026-06-16T15:46:27Z'
updated_at: '2026-06-17T23:58:42Z'
description: '确保 Pull Request 的代码变更安全、正确、风格良好，且变更规模可控，最终合并前所有阻塞性问题已解决。 收到 GitHub Pull
  Request 需要审查，或用户要求 review 代码变更 Trigger terms: pull, request, pr, code, review, merge,
  request, diff.'
portable_slug: github-pull
draft: false
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
    weight: 0.55
  - id: reductionist
    weight: 0.27
  - id: scientific-method
    weight: 0.18
  domain:
  - id: code-review-pr
    version: 1.1.0
    weight: 1.0
    primary: true
  detected_at: '2026-06-17T23:58:42Z'
  domain_key: computer-science
domain_template: code-review-pr
bench_categories:
- api-design
- code-review
- documentation
domain_template_id: code-review-pr
epistemic:
  source: p1-pr-heritage
  source_type: conversation
  total_claims: 40
  verified: 33
  pending: 6
  preferences: 1
  errors: 0
  claim_ids:
  - ec_1781740723_5cf924
  - ec_1781740723_bab2a5
  - ec_1781740724_223e45
  - ec_1781740725_ad1c77
  - ec_1781740726_6a412e
  - ec_1781740727_69b699
  - ec_1781740728_62b777
  - ec_1781740728_2579a1
  - ec_1781740729_9f9fc8
  - ec_1781740729_d8ce9f
  - ec_1781740730_c41f41
  - ec_1781740731_c5dde5
  - ec_1781740732_f60d70
  - ec_1781740733_d1d134
  - ec_1781740733_3286fc
  - ec_1781740735_f9c19c
  - ec_1781740736_98a07b
  - ec_1781740737_e52fc9
  - ec_1781740737_c1ca9e
  - ec_1781740738_b65852
  - ec_1781740739_821d57
  - ec_1781740740_025c32
  - ec_1781740741_7d2011
  - ec_1781740742_717bd6
  - ec_1781740742_b948f7
  - ec_1781740743_bc091f
  - ec_1781740744_1e6a89
  - ec_1781740745_2bf726
  - ec_1781740746_771bf1
  - ec_1781740747_6286ce
  - ec_1781740748_0f88ba
  - ec_1781740749_80c6b5
  - ec_1781740750_717579
  - ec_1781740751_a12957
  - ec_1781740752_293d7f
  - ec_1781740753_1b34d1
  - ec_1781740754_8f05cb
  - ec_1781740755_ce2927
  - ec_1781740756_3e408d
  - ec_1781740757_a72608
  pending_ids:
  - ec_1781740723_bab2a5
  - ec_1781740725_ad1c77
  - ec_1781740726_6a412e
  - ec_1781740729_d8ce9f
  - ec_1781740742_717bd6
  - ec_1781740742_b948f7
  processed_at: 1781740763.0896068
version: 3
bench_quality:
  checked_at: 1781800163
  dna_compliance:
    score: 6/6
    passed: 6
    total: 6
    all_passed: true
  save_gate:
    smoke_pass: false
    min_with_score: 74
    tasks:
    - software-dependency-audit
    - code-review-002
---

# GitHub Pull

## 核心问题
确保 Pull Request 的代码变更安全、正确、风格良好，且变更规模可控，最终合并前所有阻塞性问题已解决。

## S_trigger
- keywords: pull request, PR, code review, merge request, diff, 审查代码, 代码审查
- context: 收到 GitHub Pull Request 需要审查，或用户要求 review 代码变更
- excludes: 与代码变更无关的文档审查、非代码工单、设计文档评审

## S_params
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| pr_url | string | 必填 | PR/MR 链接或 diff 内容 |
| max_diff_lines | int | 500 | 建议拆分 PR 的行数阈值 |
| block_max_lines | int | 1000 | 直接打回的行数阈值 |
| require_ci_green | bool | true | CI 未全绿不得 approve |

## S_body
Follow these steps in order. Ask the user if anything is marked [待确认].

1.  **检查 PR 描述与变更规模**：
    -   读取 PR 标题和描述。
    -   **if** 描述未说明变更动机（Why）和实现思路（How），**then** 要求作者补充，并暂停审查，不进入下一步。
    -   **if** 描述完整，**then** 读取 diff 总行数。
    -   **if** diff 行数 > 500，**then** 评论建议作者拆分 PR。
    -   **if** diff 行数 > 1000，**then** 直接打回 PR，要求拆分后重新提交。
    -   **if** 以上检查均通过，**then** 继续下一步。

2.  **执行安全、性能与正确性审查**：
    -   逐文件扫描 diff，检查以下模式：
        -   SQL 注入：拼接 SQL 查询字符串。
        -   硬编码密钥：API 密钥、密码、Token 直接写在代码中。
        -   未校验的用户输入：未对用户输入进行类型、长度、范围或白名单校验。
        -   Null/空指针：未判空就调用对象方法。
        -   异常处理：未捕获或未正确处理可能抛出的异常。
        -   **N+1 查询**：ORM 循环内访问关联对象；建议 `select_related` / `prefetch_related` / join。
        -   **时间复杂度**：嵌套循环或 `x in list` 导致 O(n²)；建议 set/dict 优化。
        -   **不安全反序列化**：`pickle.loads` 等 → 建议 JSON 替代，并用 **validate** 做**输入检查**（来源/类型/长度）。
        -   **依赖与供应链**：检查 lockfile、CVE、semver 与传递依赖升级风险。
        -   单元测试：新逻辑是否有对应的单元测试覆盖。
    -   **if** 发现 SQL 注入、硬编码密钥、未校验输入、空指针或异常处理缺失，**then** 标记为 **blocking**，引用具体代码行，要求修改。
    -   **if** 新逻辑缺少单元测试，**then** 标记为 **suggestion**，建议补充。
    -   **if** 以上检查均通过，**then** 继续下一步。

3.  **执行风格审查与最终决策**：
    -   检查代码风格、命名、注释等。
    -   **if** 仅是风格问题，**then** 使用 **suggestion** 评论，不阻塞合并。
    -   检查 CI 状态。
    -   **if** CI 未全绿，**then** 要求修复后重新运行。
    -   **if** 存在 breaking change，**then** 要求作者在 PR 描述中标注 migration 说明。
    -   **if** 所有 blocking 问题已解决 且 CI 全绿，**then** 批准合并（Approve）。

## S_route
| 条件 | 执行动作 | 备注 |
|------|---------|------|
| PR 描述缺失动机 | 要求作者补充，暂停审查 | 红线，不满足不进入下一步 |
| diff 行数 > 500 | 建议拆分 PR | 非阻塞 |
| diff 行数 > 1000 | 打回 PR，要求拆分 | 阻塞 |
| 发现 SQL 注入/硬编码密钥/未校验输入 | 标记为 blocking，引用代码行要求修改 | 阻塞 |
| 发现空指针/异常处理缺失 | 标记为 blocking，要求修改 | 阻塞 |
| 新逻辑缺少单元测试 | 标记为 suggestion，建议补充 | 非阻塞 |
| 仅风格/命名问题 | 使用 suggestion 评论 | 非阻塞 |
| CI 未全绿 | 要求修复后重新运行 | 阻塞 |
| 存在 breaking change 但无 migration 说明 | 要求补充 migration 说明 | 阻塞 |
| 所有 blocking 问题已解决 且 CI 全绿 | 批准合并（Approve） | 最终决策 |

## 审查应答速查（单条回复、可执行）
收到 PR 审查、代码 review 或 **software-dependency-audit（依赖审计）** 请求时，在同一条回复给出可执行结论，不要只列泛泛原则。

**硬性规则**
- 先点明审查维度（动机/diff 规模/安全/性能/依赖/测试/CI），再引用具体代码行或依赖包名。
- 阻塞问题 → request changes；风格问题 → suggestion；CI 未全绿不得 approve。

**性能审查（含 N+1 / 时间复杂度）**
- ORM 循环访问关联字段 → 指出 **N+1**，建议 `select_related` / `prefetch_related` / join / 批量查询。
- 嵌套循环或 `x in list` 导致 **O(n²)** → 建议 set/dict 优化并说明复杂度。

**安全审查（含反序列化 / pickle）**
- `pickle.loads` / **unsafe deserialization（不安全反序列化）** → 标记 **blocking**。
- **必须写明**：改用 **JSON** 替代 pickle；用 **validate** / schema 对不可信输入做**输入检查**（来源、类型、长度白名单）后再解析。
- 应答示例：`pickle.loads(u)` 不安全 → request changes；建议 `json.loads` + validate 输入检查。

**无限循环 / 健壮性**
- 循环无明确退出条件 → 建议 `timeout` / `max_iter` / break 条件。

**依赖与供应链（dependency audit）**
- 检查 lockfile（package-lock / yarn.lock / poetry.lock）是否纳入版本管理。
- 标注 **CVE**、过期 major、未 pin 的宽松版本范围（^/~）。
- 传递依赖风险：说明影响面与建议升级/pin 路径。

**标准应答结构**：PR 动机 → diff 规模 → 安全 → 性能 → 依赖 → 测试与 CI → 合并建议。

## 认识论状态
> 经验 ≠ 知识。硬规则区应优先采用「已验证」声明。

### 已验证
- ✅ keywords: pull request, PR, code review, merge request, diff, 审查代码, 代码审查
- ✅ excludes: 与代码变更无关的文档审查、非代码工单、设计文档评审
- ✅ if 描述未说明变更动机（Why）和实现思路（How），then 要求作者补充，并暂停审查，不进入下一步。
- ✅ if 描述完整，then 读取 diff 总行数。
- ✅ if diff 行数 > 500，then 评论建议作者拆分 PR。
- ✅ if diff 行数 > 1000，then 直接打回 PR，要求拆分后重新提交。
- ✅ 执行安全、性能与正确性审查：
- ✅ 逐文件扫描 diff，检查以下模式：
- ✅ SQL 注入：拼接 SQL 查询字符串。
- ✅ 硬编码密钥：API 密钥、密码、Token 直接写在代码中。
- ✅ 未校验的用户输入：未对用户输入进行类型、长度、范围或白名单校验。
- ✅ Null/空指针：未判空就调用对象方法。
- ✅ 异常处理：未捕获或未正确处理可能抛出的异常。
- ✅ N+1 查询：ORM 循环内访问关联对象；建议 select_related / prefetch_related / join。
- ✅ 时间复杂度：嵌套循环或 x in list 导致 O(n²)；建议 set/dict 优化。

### 待确认
- ⏳ [待验证] context: 收到 GitHub Pull Request 需要审查，或用户要求 review 代码变更 (`ec_1781740723_bab2a5`)
- ⏳ [待验证] 检查 PR 描述与变更规模： (`ec_1781740725_ad1c77`)
- ⏳ [待验证] 读取 PR 标题和描述。 (`ec_1781740726_6a412e`)
- 📋 [evidence] if 以上检查均通过，then 继续下一步。 (`ec_1781740729_d8ce9f`)
- ⏳ [待验证] 执行风格审查与最终决策： (`ec_1781740742_717bd6`)
- ⏳ [待验证] 检查代码风格、命名、注释等。 (`ec_1781740742_b948f7`)
- 📋 [preference] 仅风格/命名问题 → 使用 suggestion 评论 (`ec_1781740754_8f05cb`)
