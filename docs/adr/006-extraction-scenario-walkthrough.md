# ADR 006: 萃取体系端到端场景验证

**日期**：2026-06-19
**目的**：以两种真实用户角色走通完整萃取链路，验证所有组件协同工作

---

## 场景 1：普通岗位员工——电商客服组长沉淀退款 SOP

### 角色画像

- **姓名**：小王
- **岗位**：电商客服组长（数码配件公司，日单量 200）
- **技能水平**：会用 ERP 系统，写过简单 Python 脚本，不懂 AI
- **目标**：把自己每天处理退款的流程沉淀下来，新人来了可以直接用

### 对话流程

```
用户: 帮我沉淀一下电商客服处理退款的流程

系统:
  [Topic Extraction]
  "帮我沉淀一下电商客服处理退款的流程"
  → strip prefix "帮我沉淀一下" → "电商客服处理退款"
  → _extract_topic() → "电商客服处理退款"

  [Agent Start]
  Domain opening: "好的，聊聊「电商客服处理退款」——
  你碰到过最头疼的一个客户退款，是怎么处理的？
  从接到问题到最后解决，中间都发生了什么？"

用户: 我们公司做数码配件，日单量200左右。退款流程是这样的：
  先在ERP里查订单号和支付渠道。如果没发货就直接退款，
  发了货的要看物流状态——已经签收的要买家退货我们收到货才退款，
  没签收的联系物流拦截。超过500元的退款必须主管审批。

系统:
  [Resource Detection]
  classify_resource_type() → "reference"
  (用户描述了退款政策规则，触发 reference 分类)

  [Epistemology]
  record_claim(content="先在ERP里查订单号和支付渠道...",
               source="dialogue_explore:电商客服处理退款",
               source_type="user_feedback")

用户: 退款邮件模板是这样的：
  亲爱的{客户姓名}，您的订单{订单号}退款{金额}元
  已原路退回，预计3-5个工作日到账。如有疑问请联系客服。

系统:
  [Resource Detection]
  classify_resource_type() → "asset"
  (检测到 {客户姓名} 模板占位符，触发 asset 分类)
  → Queued to _pending_resources

用户: 我平时查ERP用的是这个Python脚本：
  ```python
  import requests
  def check_order(order_id):
      resp = requests.get(f'http://erp.internal/api/orders/{order_id}')
      ...
  ```

系统:
  [Resource Detection]
  classify_resource_type() → "script"
  (检测到 Python 代码块，触发 script 分类)
  → Queued to _pending_resources

用户: 可以了，生成吧

系统:
  [Generate Pipeline]
  1. _generation_context() — 组装对话上下文 + 渐进草稿
  2. LLM call — 生成 SKILL.md（prompt 要求 [动作]/[门禁] 标注）
  3. normalize_skill_body() — 规范化为标准段落
  4. ensure_gate_steps_in_route() — 检测 2 个门禁步骤
  5. finalize_portable_skill() — 规范化格式
  6. to_agent_skills_format() — YAML frontmatter 包装
  7. _flush_pending_resources() — 批量写入资源文件
  8. _extract_claims_from_skill() — 提取 claims
  9. record_claim() × N — 写入认识论引擎
```

### 产出

```
refund-processing/
├── SKILL.md
│   ---
│   name: refund-processing
│   description: >
│     Handle e-commerce refund requests including ERP order
│     verification and payment reversal. Use when user mentions
│     refund, 退款, 退货. Trigger terms: refund, return, 退款.
│   metadata:
│     display_name: 电商客服处理退款
│     generated_by: SkillOS
│   ---
│   # 电商客服处理退款
│   ## When to use
│   - keywords: 退款, 退货, 退款申请
│   ...
│   ## Instructions
│   1. [动作] 在ERP中查询订单号和支付渠道
│   2. [门禁] 订单状态必须已确认 → 未确认则中止
│   3. [动作] 根据发货状态分支处理
│   4. [门禁] 金额>500元必须主管审批 → 自动升级
│   ...
│   ## Decision routes
│   | 仅退款+未发货 | 直接退款 | |
│   | 订单状态必须已确认 → 未确认则中止 | 中止或升级 | [门禁] |
│   | 金额>500元必须主管审批 | 自动升级 | [门禁] |
├── scripts/
│   └── check_order.py          ← ERP 查询脚本（从对话中提取）
├── references/
│   └── policy.md               ← 退款政策规则
├── assets/
│   └── email_template.txt      ← 退款邮件模板
└── .skillos/
    └── versions/
```

### 小王获得了什么

1. **标准 SKILL.md**——可直接安装到 Claude Code/Cursor/Codex CLI
2. **ERP 脚本**——保存在 scripts/，不是只描述不执行
3. **邮件模板**——保存在 assets/，拿到就能用
4. **2 个门禁**——ERP 状态确认 + 金额审批——自动入 S_route，AI 无法跳过
5. **5 条知识声明**——进入 Plato/Popper 验证管线，后续可交叉验证

---

## 场景 2：行业专家——财务合规顾问沉淀方法论供订阅

### 角色画像

- **姓名**：陈老师
- **岗位**：财务合规顾问（10 年四大会计师事务所经验）
- **技能水平**：精通中国会计准则和税务法规，经常给企业做培训
- **目标**：把自己的报销审核方法论沉淀为技能包，发布到市场供其他公司订阅

### 对话流程

```
用户: 帮我沉淀一套财务报销审核的方法论，我想发布到技能市场

系统:
  [Topic Extraction]
  "帮我沉淀一套财务报销审核的方法论"
  → strip "帮我沉淀一套" → "财务报销审核的方法论"
  → strip suffix "的方法论" → "财务报销审核"
  → _extract_topic() → "财务报销审核"

  [Agent Start]
  "好的，聊聊「财务报销审核」——你最近一次审报销单，
  从拿到单子到签字通过，中间都查了什么？随便聊聊"

用户: 我做财务合规10年了。报销审核的核心不是看发票真伪——
  那个是基础。核心是三条线：业务真实性、金额合理性、税务合规性。
  业务真实性要看报销事项是否与业务相关、时间是否合理、
  是否有对应的审批记录。金额合理性要对比历史数据和行业标准。
  税务合规性要检查发票类型是否匹配、税率是否正确、
  是否有需要代扣代缴的情况。

系统:
  [Resource Detection]
  classify_resource_type() → "reference"
  (用户描述了三线审核框架，属于方法论参考)

  [Epistemology]
  record_claim(content="报销审核核心三条线：业务真实性、金额合理性、税务合规性",
               source="dialogue_explore:财务报销审核",
               source_type="user_feedback")
  record_claim(content="业务真实性：报销事项与业务相关、时间合理、有审批记录",
               source="dialogue_explore:财务报销审核",
               source_type="user_feedback")
  ... (每个核心论点一条 claim)

用户: 我还有个检查清单，审核的时候逐项核对：
  [ ] 发票抬头与公司名称一致
  [ ] 发票税号正确
  [ ] 报销金额与发票金额一致
  [ ] 费用类型在预算范围内
  [ ] 审批人权限足够（超过5000需要部门总监）
  [ ] 附件齐全（合同/行程单/验收单）
  [ ] 发票类型与费用类型匹配（餐费不能用专票抵扣）

系统:
  [Resource Detection]
  classify_resource_type() → "asset"
  (检测到检查清单 [ ] 格式，属于 asset)

用户: 我还想把这个审核流程做成一个流水线：
  第一步业务分析师澄清报销类型和上下文，
  第二步审核员检查三线合规，
  第三步安全审计员检查敏感费用（超过1万的要特别标注），
  最后发布经理确认所有门禁通过才能签字。

系统:
  [MetaSkill 检测]
  用户描述了多角色协作流程 → 建议使用 MetaSkill 管道

  [Role Matching]
  "业务分析师" → business_analyst ✓ (built-in)
  "审核员" → reviewer ✓ (built-in)
  "安全审计员" → security_auditor ✓ (built-in)
  "发布经理" → release_manager ✓ (built-in)

用户: 是的，生成 MetaSkill

系统:
  [Generate MetaSkill Pipeline]

  ```yaml
  # MetaSkill: expense-audit-orchestrator
  ## Pipeline
  clarify: 报销需求澄清
    # role: business_analyst | accept: 报销类型、金额、附件清单明确 | handoff_to: reviewer

  audit: 三线合规审核
    # role: reviewer | depends_on: [clarify]
    | accept: 三线全部通过或标记不合规项 | handoff_to: security_auditor

  security: 敏感费用审查
    # role: security_auditor | depends_on: [audit]
    | accept: >1万费用已标注、无不寻常模式

  release: 发布确认
    # role: release_manager | depends_on: [security]
    | accept: 全部门禁通过、检查清单完成
  ```

  ## Acceptance Gates
  - 📋 业务分析师 → clarify: 报销类型和上下文明确
  - ✅ 审核员 → audit: 三线全部通过或标记不合规
  - 🛡️ 安全审计员 → security: 敏感费用已标注
  - 🚀 发布经理 → release: 全部门禁通过
```

### 产出

```
expense-audit/
├── SKILL.md                         ← 三线审核法（YAML frontmatter）
│   [动作]/[门禁] 标注
│   description 包含触发词: 报销, 审核, 发票, expense audit
├── scripts/
├── references/
│   └── three_line_methodology.md    ← 三线审核方法论
├── assets/
│   └── checklist.md                 ← 7 项检查清单
├── .skillos/
│   └── versions/
│
expense-audit-orchestrator/          ← MetaSkill 管道
├── SKILL.md
│   type: metaskill
│   4 roles × 4 steps
│   每个步骤有角色、验收标准、handoff
```

### 发布到市场

```
[Marketplace Publish]
1. 生成 3-5 个测试任务（审核员看不到）
2. Fresh Agent 加载技能执行 → 调用率 + 均分 → 执行分
3. Auditor 10 维检查 → 审计分
4. overall = 执行分 × 0.6 + 审计分 × 0.4
5. Gate: ≥70 自动通过 → 进入市场目录

[订阅者获得]
- SKILL.md + 全部资源文件（脚本/模板/检查清单）
- MetaSkill 管道（4 角色协作）
- 认识论验证状态（三线方法论已通过交叉验证）
- 版本历史 + 决策记录
```

---

## 对比：两种用户的价值差异

| 维度 | 小王（普通员工） | 陈老师（行业专家） |
|------|-----------------|-------------------|
| **输入方式** | 口语化描述日常工作 | 结构化方法论 + 检查清单 + 流水线 |
| **资源丰富度** | 1 脚本 + 1 模板 | 1 方法论文档 + 1 检查清单 |
| **门禁数量** | 2（ERP 确认 + 金额审批） | 4（每个角色一个验收标准） |
| **角色协作** | 无（单人技能） | 4 角色 MetaSkill 管道 |
| **产出格式** | SKILL.md（单文件） | SKILL.md + MetaSkill 管道 |
| **发布目标** | 团队内部使用 | 市场发布供订阅 |
| **认识论验证** | 5 条 experience 声明 | 10+ 条，含行业标准交叉验证 |
| **知识复用** | 新人入职培训 | 多公司订阅 + 版本迭代 |

---

## 结论

萃取体系在两种场景下均完整运作：

1. **普通员工**获得的是"操作手册"——脚本、模板、门禁一步到位
2. **行业专家**获得的是"可订阅的方法论产品"——多角色管道 + 市场验证 + 版本管理

两种场景共用同一套基础设施（Socratic 对话 → 资源捕获 → 门禁检测 → AgentSkills.io 输出 → 认识论记录），仅在 MetaSkill 角色编排和发布流程上有差异。
