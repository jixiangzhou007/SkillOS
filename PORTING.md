# SkillOS — Migration Plan from Skill Distiller

## Architecture Changes

| Skill Distiller | SkillOS | Why |
|---|---|---|
| `http.server` single file | FastAPI modular routes | Clean routing, auto-docs, async |
| `app.js` 3200 lines | 6 separate JS files | Already split, carry over |
| `skill_server.py` monolith | `skillos/api/*.py` | One route group per file |
| No desktop | pywebview native window | Hermes-compatible desktop |
| Hermes unknown | `hermes_bridge.py` | Bidirectional skill interop |

## Porting Order (by dependency)

### Phase 1 — Foundation (must port first)
- [ ] `skill_store.py` → `skillos/skills/skill_store.py`
- [ ] `config.py` → `skillos/config.py`
- [ ] `llm_client.py` → `skillos/llm_client.py`
- [ ] `agent_factory.py` → `skillos/skills/agent_factory.py`
- [ ] `session_manager.py` → `skillos/skills/session_manager.py`
- [ ] `conversation_store.py` → `skillos/skills/conversation_store.py`

### Phase 2 — Knowledge Engine
- [ ] `epistemology.py` → `skillos/knowledge/epistemology.py`
- [ ] `knowledge_extractor.py` → `skillos/knowledge/extractor.py`
- [ ] `knowledge_store.py` → `skillos/knowledge/store.py`
- [ ] `knowledge_graph.py` → `skillos/knowledge/graph.py`
- [ ] `knowledge_lineage.py` → `skillos/knowledge/lineage.py`
- [ ] `deep_digest.py` → `skillos/knowledge/deep_digest.py`
- [ ] `skill_kb.py` → `skillos/knowledge/skill_kb.py`

### Phase 3 — Skill Pipeline
- [ ] `skill_agent.py` → `skillos/skills/agent.py`
- [ ] `dispatcher.py` → `skillos/skills/dispatcher.py`
- [ ] `metaskill.py` → `skillos/skills/metaskill.py`
- [ ] `tool_registry.py` → `skillos/skills/tool_registry.py`
- [ ] `skill_variants.py` → `skillos/skills/variants.py`
- [ ] `pattern_miner.py` → `skillos/skills/pattern_miner.py`

### Phase 4 — Evolution Engine
- [ ] `skill_evolver.py` → `skillos/evolution/evolver.py`
- [ ] `evolution_engine.py` → `skillos/evolution/engine.py`
- [ ] `skillopt.py` → `skillos/evolution/skillopt.py`
- [ ] `skillhone.py` → `skillos/evolution/skillhone.py`
- [ ] `learning_theory.py` → `skillos/evolution/learning_theory.py`
- [ ] `learning_records.py` → `skillos/evolution/learning_records.py`

### Phase 5 — Marketplace
- [ ] `skillhub_auth.py` → `skillos/marketplace/auth.py`
- [ ] `skillhub_registry.py` → `skillos/marketplace/registry.py`
- [ ] `skillhub_scorer.py` → `skillos/marketplace/scorer.py`
- [ ] `skillhub_payments.py` → `skillos/marketplace/payments.py`

### Phase 6 — Desktop & Integration
- [ ] `playbook.py` → `skillos/knowledge/playbook.py`
- [ ] `file_ingest.py` → `skillos/knowledge/file_ingest.py`
- [ ] `wechat_fetch.py` → `skillos/knowledge/wechat_fetch.py`
- [ ] `hermes_bridge.py` — Already created, polish interop
- [ ] Frontend files — Copy from `frontend/` (already split)

### Phase 7 — CLI
- [ ] `skillhub_cli.py` → `skillos/ui/cli.py`

## Porting Rules

1. **Don't copy-paste blindly.** Each file should be refactored to use FastAPI patterns (Pydantic models, dependency injection, proper error handling).
2. **Remove `from __future__ import annotations`.** Python 3.11+ doesn't need it.
3. **Use `pathlib` consistently.** No `os.path` in new code.
4. **Add type hints.** All public functions should have return types.
5. **Tests come with the port.** Each ported module gets a `tests/test_<module>.py`.
6. **Keep the Hermes bridge green.** Every change should maintain `skillos_to_hermes()` and `install_to_hermes()` compatibility.
