---
name: deep-digest
type: knowledge-package
description: "Deep document digestion — structured knowledge extraction from articles, papers, and long-form content. Use when user sends a URL or pastes long text and wants structured understanding (glossary, patterns, cheatsheet, section summaries), not just flat facts. Triggers on keywords like analyze article, digest document, extract knowledge."
---

# 技能名称：deep-digest

## S_body

当用户发送 URL 或长文本（>500字），要求你"分析"、"理解"、"消化"、"提取知识"时，按以下流程执行：

1. **预检**：判断内容是否值得深度分析（信息密度、类型）
   - 技术教程/学术论文/参考手册 → 值得深度分析
   - 新闻/观点/营销内容 → 快速摘要即可
2. **深度消化**：调用 deep_digest 模块进行6阶段分析
   - 扫描与分类 → 确定文档类型和核心主题
   - 论点与结构 → 提取核心论点，划分章节
   - 术语提取 → 术语表 + 定义 + 关联
   - 模式挖掘 → 可复用的思维模型、启发式规则
   - 速查表 → 30秒可查的关键规则
   - 交叉引用 → 与已有技能建立关联
3. **结构化存储**：生成知识包存放在 skills/<slug>/ 下
   - overview.md / glossary.md / patterns.md / cheatsheet.md / sections/
4. **回复用户**：展示知识包的内容概要（术语数、模式数、章节数）和关键发现

## S_trigger

- **keywords**: 分析这篇文章, 消化这个文档, 提取知识, 帮我理解这个, 这篇文章说了什么, 总结这篇, deep digest, 深度分析, 帮我拆解, 这篇文章的核心观点
- **context**: 用户发送了 URL 或粘贴了长文本（>500字），要求结构化的分析而非简单摘要
- **excludes**: 创建技能, 新建skill, 帮我写, 帮我做（这些是 skill-creator 的范畴）

## S_params

- model: deepseek-v4-flash
- max_content_length: 15000

## S_appendix

### 与 skill-creator 的区别

| deep-digest | skill-creator |
|-------------|---------------|
| 输入是**知识型文档**（文章、论文、书籍章节） | 输入是**用户意图**（"我想创建一个XX技能"） |
| 输出是**知识包**（术语表、模式、速查表） | 输出是**可执行技能**（S_body、S_trigger、S_params） |
| 关注"**这篇文章讲了什么**" | 关注"**怎么把这个流程变成技能**" |

### 与普通 "总结这篇文章" 的区别

- 普通总结：一段话概括
- 深度消化：术语表 + 模式挖掘 + 速查表 + 章节摘要 + 知识关联
