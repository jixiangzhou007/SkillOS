# SkillOS Changelog

## v0.3.0 (2026-06-18) — 未发布

### 三层 DNA 与本地 Bench 闭环
- **Layer 0–2 DNA**：哲学方法论（6 种）+ 8/10 领域模板 + 技能结构 6 条原则；`dna_lineage` 血缘落盘 + semver 进化
- **Path B 冷启动**：`skillos/skills/cold_start.py` — anchor rubric → HERITAGE → pack 持久化（`data/domain_packs/`）
- **10 个 domain pack**：参考 3 + 泛化 3 + Sprint 10/11 补齐 6；含 heritage_body / anchor / routing
- **泛化 bench**：median domain Quick8 Δ **+45**，`strong_generalization`，回归 **ALL PASS**
- **Layer 1 ablation**：HERITAGE×pack 2×2 — 报告 [`docs/paper/experiments/layer1_ablation_results.md`](docs/paper/experiments/layer1_ablation_results.md)

### 萃取体验（Sprint 12–13）
- 对话自然化：工程师面试模式 → 朋友聊天模式（内部仍保留 DNA/MoE 链路）
- 长对话：>20 轮自动摘要；断线 `POST /resume` 续传；`GET /status` 进度查询
- 费曼简化 + 跨域类比：`_generate()` / `learn_from_url` 接入

### Bench / API
- `scripts/run_bench_regression.py` — 参考 + 泛化域 Quick8 + 6 技能烟测
- `GET /api/bench/official/summary` 增加 `generalize_skills`
- 本地评测指南：[`docs/BENCHMARK_LOCAL.md`](docs/BENCHMARK_LOCAL.md)

### 测试
- DNA / 路由 / 冷启动 / ablation 单测；全量 501 collected，478 pass / 21 fail（`--ignore=tests/test_feasibility_eval.py`，2026-06-18）

---

## v0.2.1 (2026-06-14)

### 进化深化（Phase 7）
- `export_for_skillopt()` — 导出 `best_skill.md` + traces + manifest（[`docs/evolution/SKILLOPT_EXPORT.md`](docs/evolution/SKILLOPT_EXPORT.md)）
- API `POST /api/evolution/{name}/export-skillopt`；MCP `export_for_skillopt`
- 知识扩散认识论门控：ERROR 阻断；全 pending 仅建议不自动改写

---

## v0.2.0 (2026-06-14)

### 认识论主链路（Phase 1）
- `epistemic_bridge.py`：声明提取 → `record_claim()` → falsify → SKILL.md 认识论状态 + YAML meta
- `save_skill()` 统一触发；API/MCP 返回 `epistemic_summary`
- dispatch / MCP `confirm_pending_claims` 晋升待审声明

### Epistemic Benchmark（Phase 2）
- 100 条标注声明数据集 + A/B/C ablation（`python -m skillos.benchmark_epistemic`）
- C Full：F1=0.750，false-claim filter=100% vs Baseline 0%
- 报告：[`docs/paper/experiments/epistemic_results.md`](docs/paper/experiments/epistemic_results.md)

### 沉淀协议（Phase 3）
- `intent_router.py`：extract / confirm_claims / playbook / chat 统一路由
- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) 中英话术表

### 通道产品化（Phase 4）
- MCP `extract_skill` 走 7 步管线，返回 pipeline_log + 路径
- `SKILLOS_SKILLS_DIR` / `SKILLOS_WORKSPACE_SKILLS` 工作区写入
- 飞书 session `feishu:{chat_id}:{user_id}`；Hermes checklist

### 团队上下文（Phase 5）
- chat_id → Playbook 绑定（`data/playbook_bindings.json`）
- 沉淀 lineage（`skill_precipitations.jsonl`）；变体自动登记

### 论文与叙事（Phase 6）
- 更新 [`docs/paper/paper.tex`](docs/paper/paper.tex) 实验节
- arXiv checklist：[`docs/paper/SUBMIT.md`](docs/paper/SUBMIT.md)

### 测试
- 154 passed, 2 skipped（pytest 全量）

---

## v1.0.0 (2026-06-13)

### Core Engine
- 7-step cognitive learning pipeline (初识→理解→拆解→重构→验证→内化→沉淀)
- 10-dimension Auditor for skill quality scoring
- MoE evolution router (Trace2Skill / EvoSkill / SkillOpt)
- Decision history with WHY chain (SkillHone)
- Targeted rollback — revert only regressed sections
- Role isolation (Optimizer vs Evaluator structural separation)
- Temporal knowledge with Graphiti-inspired edge invalidation
- EvoRAG contribution scoring with auto-pruning
- Compression reward for concise skills

### Knowledge System
- 4-level epistemic classification (Evidence→Experience→Knowledge→Preference→Error)
- Knowledge graph with 8 relation types + spreading activation
- Dual-layer retrieval (keyword + graph traversal)
- Full data lineage tracking (source → transform → knowledge → skill impact)
- Deep document digestion (glossary, patterns, cheatsheet, sections)
- SHA256 incremental caching for file re-ingestion
- Source change detection + auto-refresh (Craw4AI-inspired)

### Marketplace
- Publish → Auto-score → Gate (70+ approve, 50-69 review, <50 reject)
- Elite pool tournament (top-3 competing versions)
- Subscription + auto-update system
- Pricing (free/one-time/subscription) + 20% platform commission
- Revenue dashboard for authors + platform
- RBAC 4-roles (admin/reviewer/publisher/member) + audit log

### Integration
- MCP server with 10 tools (Claude Code / Hermes / Cursor)
- Hermes Agent bridge (bidirectional skill sync)
- WeChat / Feishu gateway support via Hermes
- File ingest (PDF/Word/Excel/PPT/image/audio → Markdown)
- WeChat article CDP fetching (anti-crawl bypass)
- File system watcher (~/.skillos/inbox/ auto-ingest)

### Developer Experience
- FastAPI server with 38 routes + OpenAPI docs
- 91 tests (81 unit + 10 E2E)
- Rate limiting middleware + token hashing
- Database versioned migrations
- Startup config validation + compatibility check
- Role-based model selection (small for evolution, large for execution)
- Ollama local mode (no API key required)
- .env.example + deployment guide

### Frontend
- 8 modular JS files
- Responsive design (3 breakpoints)
- Markdown rendering for skill details
- Global search (Ctrl+K)
- Toast notifications (replaces alert())
- Loading skeletons (shimmer animation)
- Drag-and-drop file upload
- Mermaid diagram rendering with zoom/fullscreen
