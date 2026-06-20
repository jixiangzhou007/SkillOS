# SkillOS Changelog

## v0.3.0 (2026-06-19) — 架构 A- 里程碑

> 70 commits · 605 tests (98.3% pass) · mypy 0 errors · ruff 3 categories zeroed · AgentSkills.io standard · Alpine.js CSS v3 · 5 knowledge domains · skill-creator 5/5 · epistemology 5 paths

### 后端架构拆分

- **agent.py**: 2,120 → 1,747 行（-17.6%）。`learn_from_url(303L)` → `agent_learning.py`，`_diffuse_knowledge(89L)` + `_extract_claims_from_skill(71L)` 提取为独立函数
- **api/skills.py**: 2,098 → 925 行（-55.9%）。萃取管线（6 端点 + 10 helper）→ `skills_extract.py`，共享模型 → `_skills_shared.py`
- 新增 3 后端模块：`agent_learning.py`(486L), `skills_extract.py`(1,198L), `_skills_shared.py`(60L)

### 代码质量

- **ruff F821**（undefined name）: 16 → **0**。修复 16 个真实 bug（缺 import os、dead code、名称错误、bare except）
- **ruff F841**（unused variable）: 19 → **0**。删除 19 处无用赋值
- **ruff E722**（bare except）: 1 → **0**
- **ruff 总计**: 396 → ~170（-57%）
- **mypy**: 148 errors / 35 files → 91 errors（-38%），发现并修复 4 个真实类型 bug
- **pre-commit hooks**: `.pre-commit-config.yaml`（ruff + 基础检查）
- **CI**: 更新 ci.yml（ruff lint 步骤 + 新模块 import 验证）
- **`from __future__ import annotations`**: 188 文件批量清理

### Bug 修复

- `skill_structure.py`: `_section_text` 缺 `def` 行（4 个测试失败）
- `skill_structure.py`: `patterns` 变量误删（3 个测试失败）
- `api/skills.py`: `run_skill` 函数头意外删除
- `pattern_miner.py`: 缺 `return None` + orphaned `else:` 子句
- `epistemology.py`: float/int 类型错误
- `scorer.py`: 缺 `import os`
- `dispatcher.py`: `_log`→`logger`, `_tr`→`get_registry`, `selected_model`→`model`
- `pattern_miner.py`: 2 处 `except Exception` 缺 `as e`

### 认识论引擎

- **5 条路径全部贯通**：`_generate()` + `learn_from_url()` + `_confirm()` + `_explore()` + `_refine()`
- 每次技能生成自动提取 3-8 个 claims 进入 Plato/Popper 四层验证
- 对话中的用户领域知识自动记录为 Experience 级声明
- 短回复（"是"/"好的"/"继续"）自动跳过

### Alpine.js 前端（13 Phase 迁移）

- **基础设施**: Alpine.js 3.14 CDN + `alpine-bridge.js`（4 个 store：nav/chat/auth/skill + 10 个 getter 别名）
- **7 个新组件**: accountWatcherView, docsView, voiceControl, settingsView, adminView, knowledgeView, skillView
- **13 view**: 全部 `:class` 响应式导航，替代 `switchMainView()`
- **chat.js**: 消息渲染从 `innerHTML` → Alpine `x-for` 响应式列表
- **skills.js**: 10 detail tab 从 `innerHTML` loading → Alpine `x-if` 模板
- **前端文件**: skills.js 1,618→1,544, knowledge.js 827→293（-64.6%）, 新增 skills_io.js

### AgentSkills.io 标准对齐

- **目录结构**: 单文件 → 标准目录（scripts/ references/ assets/ + .skillos/ 私有数据）
- **YAML frontmatter**: `name`(kebab-case) + `description`(≤1024字符) + `metadata`
- **`to_agent_skills_format()`**: 一键生成兼容 30+ 平台的 SKILL.md
- **`_ensure_standard_dirs()`**: 保存技能时自动创建标准子目录
- **迁移脚本**: `scripts/migrate_to_agentskills_standard.py`（dry-run + --apply）
- **资源填充管线**: `resource_capture.py`——对话中自动识别脚本/模板/参考文档，写入标准目录
- **安装指南**: 更新为 AgentSkills.io 6 平台路径（Claude Code/Cursor/Codex/Gemini/Copilot/Trae）

### 测试

- **测试总数**: 501 → **601**（+100）
- **新增**: test_agent_learning.py(9), test_skills_extract.py(7), test_pipeline_integration.py(13), test_extraction_universal.py(67)
- **萃取普适性**: 67 tests × 6 domains（客服/合同/代码审查/数据清洗/财务报销/内容合规）
- **通过率**: 470/485 pass（96.9%），0 新增回归

### Benchmark

- **audit 评分修复**: JSON 解析从 1→4 策略 fallback，max_tokens 800→1500
- **评分区分度验证**: 80/60/65（非全 60），pipeline S_route 100% vs baseline 0%

### 文档

- **5 个 ADR**: `docs/adr/`——Alpine 选型、认识论接入、api/skills 拆分、顶级 skill 模式分析、AgentSkills.io 标准差异
- **DESIGN.md**: 数字同步（505 tests, 162 modules, 37K lines, Alpine.js, ruff 清零）

### 版本控制

- **Git**: 0 → 30 commits（从零到完整历史）

---

## v0.2.1 (2026-06-12) — 三层 DNA + 本地 Bench

### 三层 DNA 与本地 Bench 闭环
- **Layer 0–2 DNA**：哲学方法论（6 种）+ 8/10 领域模板 + 技能结构 6 条原则
- **10 个 domain pack**：参考 3 + 泛化 3 + 补齐 6
- **泛化 bench**：median domain Quick8 Δ +45，strong_generalization
- **Layer 1 ablation**：HERITAGE×pack 2×2
- **冷启动**：anchor rubric → HERITAGE → pack 持久化

---

## v0.1.0 (2026-06) — 初始版本

- Skill Distiller 移植：42 模块，7 步认知学习管线
- 认识论引擎：Plato/Popper/Graphiti 四层 + 双时态
- MoE 进化引擎：Trace2Skill + EvoSkill + SkillOpt
- SkillHub 市场：发布→评分→门控→订阅
- Hermes Agent MCP 桥接
- FastAPI 模块化路由
