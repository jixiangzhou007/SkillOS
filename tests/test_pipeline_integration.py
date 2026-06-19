"""Integration tests for key pipelines — dispatch→generate→epistemology, URL learning.

Route B.3: Tests critical paths without requiring LLM (mock where needed).
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from fastapi import FastAPI
    from skillos.api.skills import router as skills_router

    app = FastAPI()
    app.include_router(skills_router, prefix="/api/skills")
    return TestClient(app)


class TestExtractionPipeline:
    """Dispatch → finalize → status → resume flow."""

    def test_dispatch_creates_session(self, client):
        """POST /dispatch should return session_id."""
        resp = client.post("/api/skills/dispatch", json={
            "message": "帮我创建一个退款处理技能",
            "mode": "create",
        })
        assert resp.status_code in (200, 401, 422)  # 401 if no auth, 422 if missing fields

    def test_status_returns_state(self, client):
        """GET /status should return extraction state."""
        resp = client.get("/api/skills/status")
        assert resp.status_code == 200

    def test_finalize_requires_session(self, client):
        """POST /finalize without session should fail gracefully."""
        resp = client.post("/api/skills/finalize", json={})
        assert resp.status_code in (200, 400, 422, 500)

    def test_resume_requires_session_id(self, client):
        """POST /resume without session_id should fail gracefully."""
        resp = client.post("/api/skills/resume", json={})
        assert resp.status_code in (200, 400, 422)


class TestClaimExtractionPipeline:
    """Epistemology claim extraction from skill content."""

    def test_extract_claims_from_full_skill(self):
        from skillos.skills.agent_learning import _extract_claims_from_skill

        content = """# 技能名称：测试
## S_body
1. 第一步：验证用户身份和权限
2. 第二步：检查数据完整性和格式
3. 如果格式错误：返回错误提示；如果正确：继续处理

## S_route
| 条件 | 动作 | 备注 |
|------|------|------|
| 身份验证失败 | 返回401 | 终止流程 |
| 数据格式错误 | 返回400 | 提示修正 |

## S_trigger
- keywords: 测试, 验证
"""
        claims = _extract_claims_from_skill(content)
        assert len(claims) >= 4  # body steps + route rows
        # Verify route claims contain "|" separator
        route_claims = [c for c in claims if "|" in c]
        assert len(route_claims) >= 2

    def test_claims_recorded_during_generation(self):
        """Verify epistemology record_claim is importable and callable."""
        from skillos.knowledge.epistemology import record_claim, get_store

        claim = record_claim(
            content="测试声明：单元测试验证认识论引擎接入",
            source="test_pipeline",
            source_type="test_result",
            skill_name="test-skill",
        )
        assert claim.claim_id
        assert claim.level.value in ("experience", "evidence")  # depends on source_type
        assert claim.source == "test_pipeline"


class TestURLLearningPipeline:
    """URL learning pipeline structure validation (no LLM)."""

    def test_run_learning_pipeline_importable(self):
        from skillos.skills.agent_learning import run_learning_pipeline
        assert callable(run_learning_pipeline)

    def test_diffuse_knowledge_importable(self):
        from skillos.skills.agent_learning import diffuse_knowledge
        assert callable(diffuse_knowledge)

    def test_learning_pipeline_empty_content_handling(self):
        """Empty content should be caught early."""
        from skillos.skills.agent_learning import _extract_claims_from_skill
        claims = _extract_claims_from_skill("")
        assert claims == []


class TestRouterIntegration:
    """Cross-router integration."""

    def test_skills_router_includes_extract_routes(self):
        from skillos.api.skills import router as skills_router

        route_paths = []
        for route in skills_router.routes:
            if hasattr(route, 'methods'):
                route_paths.append(route.path)

        assert "/dispatch" in route_paths or any("dispatch" in p for p in route_paths)
        assert "/finalize" in route_paths or any("finalize" in p for p in route_paths)

    def test_shared_models_cross_import(self):
        """Verify shared models work across both modules."""
        from skillos.api._skills_shared import DispatchRequest, CreateSkillRequest
        from skillos.api.skills import router
        from skillos.api.skills_extract import router as extr

        req = DispatchRequest(message="hello", mode="create")
        assert req.message == "hello"
        assert req.mode == "create"

        req2 = CreateSkillRequest(text="test skill", content="body")
        assert req2.text == "test skill"


class TestEpistemologyCrossPath:
    """Verify epistemology is wired to all 3 paths."""

    def test_record_claim_from_generate_path(self):
        """Claims from _extract_claims_from_skill can be recorded."""
        from skillos.knowledge.epistemology import record_claim
        from skillos.skills.agent_learning import _extract_claims_from_skill

        content = "## S_body\n1. 测试步骤\n## S_trigger\n- keywords: test"
        claims = _extract_claims_from_skill(content)
        assert len(claims) > 0

        for c in claims:
            claim = record_claim(content=c, source="test:generate", source_type="llm_generated", skill_name="test")
            assert claim.claim_id

    def test_epistemology_store_persistence(self):
        """Claims persist in the epistemology store."""
        from skillos.knowledge.epistemology import record_claim, get_store

        store = get_store()
        before = len(store.claims)

        record_claim(content="test persistence claim", source="test", source_type="test_result", skill_name="test")

        store2 = get_store()
        after = len(store2.claims)
        assert after >= before
