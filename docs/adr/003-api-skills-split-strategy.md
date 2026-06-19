# ADR 003: api/skills.py 拆分策略

**日期**：2026-06-19
**状态**：已采纳
**决策者**：Claude Code

## 上下文

`api/skills.py` 膨胀至 2,098 行，38 个路由端点杂糅在一个文件中。需要拆分以改善可维护性，但拆分方式决定了模块间的耦合模式。

核心约束：路由端点与 helper 函数之间存在复杂的依赖网（`_finalize_extraction_response` → `_epistemic_reply_suffix` → `_persist_created_skill` → `_team_context_from_session`），且不能引入循环 import。

## 决策

采用 **共享模型 + 独立 Router + re-export** 三层拆分：

1. **`_skills_shared.py`**（60 行）：Pydantic 模型（`DispatchRequest`、`CreateSkillRequest`）+ 4 个跨路由共享的 helper（`_skills_list`、`_tenant_context_from_auth` 等）。这是唯一被多文件 import 的模块，故意取 `_` 前缀以示内部使用。

2. **`skills_extract.py`**（1,198 行）：6 个萃取管线端点（dispatch/create/finalize/status/resume/ingest）+ 10 个专属 helper。使用独立 `APIRouter`，在主 `skills.py` 中通过 `router.include_router()` 挂载。

3. **`skills.py`**（925 行）：剩余 32 个端点。重新导出移动的函数（`_create_mode_skills_list`、`_finalize_extraction_response` 等）保持测试向后兼容。

## 理由

1. **萃取管线是最大的自包含子系统**。`dispatch` 一个端点就 323 行，加上 5 个辅助端点和 10 个 helper，合计 ~700 行——足够独立成一个模块。其他端点组（DNA evaluation、variants、meta skill）规模较小（各 100-200 行），拆分会过度碎片化。

2. **共享模型放到 `_skills_shared.py` 避免循环 import**。如果 `skills.py` import `skills_extract.py`（为了 `include_router`），同时 `skills_extract.py` import `skills.py`（为了 Pydantic 模型），就会形成循环。`_skills_shared.py` 作为单向依赖的底层模块解决了这个问题。

3. **Re-export 保持测试兼容**。在 `skills.py` 中添加 `from skillos.api.skills_extract import _create_mode_skills_list` 等 re-export，使得 `test_phase_a.py` 等旧测试的 `from skillos.api.skills import _create_mode_skills_list` 继续工作。

4. **`_` 前缀是故意的信号**。`_skills_shared.py` 不是公共 API，它只在 `skills.py` 和 `skills_extract.py` 之间共享。`_` 前缀告诉外部的 import 者"不要直接依赖这个模块"。

## 后果

### 正面
- skills.py：2,098 → 925 行（-56%），回归到可管理的大小
- 萃取管线的修改现在只需动 `skills_extract.py`，降低 merge 冲突风险
- 共享模型集中管理，避免 definition duplication

### 负面
- 总行数略增（原 2,098 vs 新 925 + 1,198 + 60 = 2,183），增加了 85 行的 import/header 开销
- Re-export 列表需要维护——如果 `skills_extract.py` 添加新的公开函数，需同步更新 `skills.py` 的 re-export
- 3 个文件比 1 个文件更难全局搜索，但 IDE 的 "Go to Definition" 缓解了这个问题

### 为什么不拆更多文件

考虑过将 DNA evaluation 端点（10 个，~300 行）拆到 `skills_dna.py`，将 variants/meta skill 端点（8 个，~200 行）拆到 `skills_meta.py`。不做是因为：
- 每个文件只有 200-300 行，拆分的 overhead（import/header/router 样板）占比过高
- DNA 端点和 meta skill 端点都依赖 `skills.py` 的 helper，会引入更多 `_shared` 模块
- 当前 `skills.py` 的 925 行已经足够可管理
