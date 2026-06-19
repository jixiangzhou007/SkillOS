# ADR 005: SkillOS vs AgentSkills.io 标准差异分析

**日期**：2026-06-19
**触发**：验证 SkillOS 技能格式与 agentskills.io 开放标准的一致性
**参考**：https://agentskills.io/specification (2025-12-18 发布，30+ 平台采纳)

---

## 一、核心差异

| 维度 | AgentSkills.io 标准 | SkillOS 当前 | 差距 |
|------|-------------------|-------------|------|
| **技能载体** | **目录**（含子文件和子目录） | 单文件 SKILL.md | ❌ 重大 |
| **命名** | `kebab-case` 英文（如 `pdf-processing`） | 中文名（如 `退款处理`） | ⚠️ 不兼容 |
| **目录结构** | scripts/ references/ assets/ | 无 | ❌ 缺失 |
| **YAML 字段** | name, description, license?, compatibility?, metadata?, allowed-tools? | name, description | ⚠️ 缺 4 个可选字段 |
| **name 约束** | 1-64 字符，仅 a-z0-9- | 中文任意长度 | ❌ 违反 |
| **description** | ≤1024 字符，第三人称 | 中文第一人称 | ⚠️ 风格差异 |
| **渐进式加载** | 3 层（Metadata→Body→Resources） | 无分层加载机制 | ❌ 缺失 |

## 二、详细对比

### 2.1 目录结构

**标准要求**：
```
skill-name/
├── SKILL.md                # 必须有
├── scripts/                # 可选：可执行脚本
├── references/             # 可选：按需加载的文档
│   └── REFERENCE.md
├── assets/                 # 可选：模板、图片等
│   ├── templates/
│   └── images/
```

**SkillOS 当前**：
```
skills/
├── 退款处理/
│   └── SKILL.md            # 只有这一个文件
│   └── memory.json         # SkillOS 私有格式（认识论记录）
│   └── v1.md, v2.md...     # 版本迭代文件
```

**差异**：SkillOS 的文件是围绕**版本和记忆**组织的（memory.json, v1.md...），而非围绕**可执行资源**（scripts/, references/）。两个组织维度不冲突，但 SkillOS 缺少标准的 scripts/references/assets 目录。

### 2.2 name 字段

**标准**：`name: pdf-processing`（kebab-case，小写英文）
**SkillOS**：`name: 退款处理`（中文）

这是**最致命的差异**。SkillOS 的 `tool_name`（SKILL.md 生成模板中的 kebab-case 英文名）实际符合标准，但 `name` 字段用的是中文。标准规定 name 必须等于目录名，但 SkillOS 的目录名也是中文。

### 2.3 description 字段

**标准要求**：第三人称，包含触发词，≤1024 字符。
**好的例子**：`"Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction."`
**差的例子**：`"Helps with PDFs."`

**SkillOS 当前**：`_generate()` 方法用 `tool_description: <第三人称描述：做什么 + 何时触发 + 触发词，一句话>` ——这个实际上是符合标准的！只是它嵌在 Markdown 正文里而非 YAML frontmatter 中。

### 2.4 S_trigger 与 description 的关系

**标准**：`description` 字段承担触发路由功能。Claude Code 在会话启动时读取所有 skill 的 `name + description`，匹配用户意图。

**SkillOS**：`S_trigger` 段（keywords + context + excludes）承担触发功能。这是**更精细的设计**——标准只有一个 description 字段做触发+描述，SkillOS 把触发逻辑拆分成了 keywords（精确匹配）+ context（场景描述）+ excludes（反触发）。

→ **这是 SkillOS 应该贡献回标准的设计**。

---

## 三、内化建议

### P0：目录结构对齐（立即）

```
# 改后：SkillOS 技能同时满足自身需求和 AgentSkills.io 标准
skill-name/
├── SKILL.md              # 标准 YAML + Markdown
├── scripts/              # 标准 + SkillOS：可执行脚本
├── references/           # 标准 + SkillOS：按需加载文档
├── assets/               # 标准 + SkillOS：模板和资源
├── .skillos/             # SkillOS 私有：认识论记录、版本历史
│   ├── memory.json
│   ├── epistemic_state.json
│   └── versions/         # v1.md, v2.md... 移入此处
```

**改动**：
- 技能版本文件（v1.md, v2.md...）移入 `.skillos/versions/`
- 认识论记录（memory.json）移入 `.skillos/`
- 保留标准 scripts/references/assets 目录

### P1：name 字段双语

```
# 标准兼容 + SkillOS 增强
name: refund-processing          # 标准 kebab-case
display_name: 退款处理            # SkillOS 扩展（非标准字段，metadata 中）
description: >
  Handle customer refund requests including order verification, return
  coordination, and payment reversal. Use when processing refunds, returns,
  or customer complaints about orders. Triggers: 退款, 退货, 退款申请.
```

### P2：description 增强

SkillOS 的 S_trigger 设计优于标准的纯 description 触发。建议：
- `description` 字段按标准要求写（第三人称 + 触发词 + 场景）
- `S_trigger` 保留为增强版路由信息（keywords + context + excludes）
- 前端展示时从 S_trigger 自动生成 description

---

## 四、总结

SkillOS 离 AgentSkills.io 标准**只差一步**：目录结构标准化。

当前的核心巧思（S_trigger/S_body/S_route 三段式、认识论验证、DNA 多态、进化引擎）全部**在标准之上**，不冲突。问题只是文件组织方式——把技能从单文件改为标准目录，把私有数据（版本、记忆）移到 `.skillos/` 子目录。

改完后，SkillOS 产出的技能可以**直接安装在 Claude Code、Cursor、Codex CLI、Gemini CLI 等 30+ 平台**——而不是只有 SkillOS 自己能读。
