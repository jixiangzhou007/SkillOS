# ADR 007: skill-creator 分析——SkillOS 萃取管线可借鉴的模式

**日期**：2026-06-20
**来源**：Anthropic 官方 `skill-creator` SKILL.md（skills/skill-creator/SKILL.md）
**目的**：对照业界最成熟的技能创建方法论，找出 SkillOS 萃取管线的差距

---

## 一、skill-creator 的核心模式

### 1. 测试驱动的技能创建

skill-creator 的核心循环不是"对话→生成"，而是：

```
Draft → Test (3-5 prompts, with/without skill) → Evaluate (quantitative + human) → Improve → Repeat
```

每次迭代：
- 并行跑 with-skill + baseline（无 skill 或有旧版本）
- 捕获 timing.json（tokens + duration）
- 用 grader subagent 对 assertion 打分
- 聚合为 benchmark.json（pass_rate, time, tokens, mean ± stddev）
- 打开 eval viewer 让用户可视化对比

**SkillOS 差距**：有 benchmark 系统，但没有集成到萃取对话中。用户生成技能后没有自动提示"要不要跑个测试看看效果？"

### 2. 渐进式披露作为硬纪律

> "铁的纪律：SKILL.md 必须精简。如果超过 500 字，把详细内容拆到 references/ 里。"

skill-creator 强制执行三层结构：
- SKILL.md ≤ 500 字（角色 + 决策表 + 路由）
- references/ 按需加载
- scripts/ 按需执行

**SkillOS 差距**：`_generate()` 生成的技能没有字数限制，没有主动建议拆分。用户可能会得到一个 2,500 字的单文件技能——违反了渐进式披露原则。

### 3. Description = 触发灵魂

skill-creator 对 description 有严格的规则：

| 规则 | 例子 |
|------|------|
| 必须有具体触发词 | ❌ "帮助处理视频" → ✅ "短视频口播稿撰写。触发词：写脚本、改文案、短视频结构" |
| 必须有边界（何时不要触发） | "注意：纯娱乐向搞笑视频请勿触发" |
| 必须"pushy"——对抗 undertrigger | "即使用户没有明确说'做仪表盘'，只要涉及数据可视化就触发" |
| 写完后自问：陌生人能判断触发时机吗？ | — |

而且有专门的**描述优化循环**：20 个 eval queries（10 should-trigger + 10 should-not-trigger），60% train / 40% test，最多 5 轮自动优化。

**SkillOS 差距**：`build_description()` 从 S_trigger keywords + core problem 自动生成，但没有检查质量、没有边界条件、没有抗 undertrigger 优化。

### 4. 迭代改进方法论

skill-creator 对"如何改进技能"有具体的思维框架：

1. **从反馈中泛化**：不要为测试样例过拟合。如果技能只在 3 个样例上工作，那就是废的。
2. **保持 prompt 精简**：删除不产生价值的指令。读 transcript，看看模型是否在浪费时间。
3. **解释 why**：不要用 ALWAYS/NEVER 大写加粗，而要解释为什么这样做重要。
4. **寻找重复工作**：如果所有 test case 的子 agent 都独立写了类似的脚本，那就该 bundle 到 scripts/ 里。

**SkillOS 差距**：进化引擎（skillopt/skillhone）有这个能力，但它是一个**离线批处理系统**——不在用户对话中运行。用户生成技能后，进化引擎可能要等 24 小时才自动优化。

### 5. 反模式目录

skill-creator 直接列了一张常见错误表：

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 所有内容塞进 SKILL.md | token 浪费，关键信息稀释 | SKILL.md = 目录，references = 详情 |
| 没有决策表 | AI 不知道 references 下有东西 | 显式列出路由 |
| description 太模糊 | Skill 不触发或误触发 | 具体触发词 + 边界 |
| 引用不存在的文件 | Agent 执行报错 | 生成后检查路径引用 |

**SkillOS 差距**：SkillOS 在生成技能时没有做这些检查。没有自动验证文件引用是否存在、没有检查 description 质量、没有字数警告。

---

## 二、SkillOS 应该内化的 5 个改进

### P0：生成后质量自检

在 `_generate()` 完成后，自动运行检查：

```python
def _post_generation_check(content, slug):
    issues = []
    # 1. 字数检查
    if len(content) > 3000:
        issues.append("SKILL.md 超过 3000 字，建议拆分到 references/")
    # 2. S_route 存在性检查
    if "## S_route" not in content and "## Decision routes" not in content:
        issues.append("缺少决策表——AI 不知道何时加载 references/")
    # 3. Description 质量检查
    desc = build_description(name, content)
    if any(vague in desc for vague in ["帮助", "处理", "用于", "工具"]):
        issues.append("description 包含泛词，可能触发不准确")
    # 4. 文件引用存在性检查
    refs = re.findall(r'references/(\S+)', content)
    for ref in refs:
        if not (skill_dir / "references" / ref).exists():
            issues.append(f"引用了不存在的文件: references/{ref}")
    return issues
```

然后在生成回复中追加：`"⚠️ 检测到 N 个问题：... 是否现在修复？"`

### P1：描述优化循环

吸收 skill-creator 的 description optimization 流程：

1. 用户生成技能后，问："要不要优化触发精确度？"
2. 自动生成 10 个 should-trigger + 10 个 should-not-trigger 查询
3. 让用户审核（类似 eval_review.html 的交互）
4. 跑优化循环（60% train / 40% test，最多 5 轮）
5. 回写最佳 description 到 SKILL.md

这可以直接复用 `build_description()` 的输出作为初始值，然后调用 LLM 迭代改进。

### P2：萃取对话引入迭代循环

当前的 Socratic 萃取是**单次**的：对话→生成→完成。skill-creator 的核心洞察是**迭代**才是质量的关键。

改进：在 `_generate()` 完成后，不直接结束，而是进入一个"改进循环"模式：

```
Agent: "技能已生成。要不要我跑 3 个测试用例看看效果？"
User: "好的"
Agent: [并行跑 3 个 with-skill + baseline 测试]
Agent: "结果出来了：S_route 覆盖率 100%，但'金额超限处理'步骤在测试 2 中未被触发。
       要我修改这个步骤吗？"
User: "是的，把金额阈值改成可配置参数"
Agent: [修改 skill，重新跑测试]
Agent: "已修改。现在全部 3 个测试都正确触发。要发布吗？"
```

### P3：反模式自动检测

在 `_generate()` 生成后自动运行 skill-creator 的反模式检查，作为质量门禁：

- [ ] S_route 决策表存在且 ≥ 2 行
- [ ] Description 包含至少 3 个具体触发词
- [ ] Description 包含边界条件（"不触发"）
- [ ] SKILL.md ≤ 500 行 / 3,000 字
- [ ] 所有 references/ 文件引用路径有效

不通过的在生成回复中警告用户。

### P4：常见错误表写入领域 DNA

把 skill-creator 的反模式表写入 SkillOS 的领域 DNA 模板，让 `_generate()` prompt 自带这些检查规则：

```markdown
## 常见错误（生成前自查）
| 错误 | 后果 | 正确做法 |
|------|------|---------|
| SKILL.md 塞太多内容 | token 浪费 | 核心步骤放 body，详细说明放 references/ |
| 没有决策表 | AI 不知道何时做什么 | ## S_route 至少 2 行 |
| description 太模糊 | 不触发 | 具体触发词 + 不触发的边界 |
| 引用不存在的文件 | 执行报错 | 检查所有文件路径引用 |
```

---

## 三、一行总结

> skill-creator 不是"帮你写一个技能"，而是"教你如何迭代出一个好技能"。SkillOS 当前做到了前者，缺的是后者——测试驱动、质量自检、迭代循环、反模式预防。把这四个内化，SkillOS 就从"技能生成器"变成"技能工程平台"。
