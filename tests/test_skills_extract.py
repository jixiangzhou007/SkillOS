"""Smoke tests for skills_extract.py — route registration and dispatch flow (no LLM)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from skillos.api.skills import router as skills_router
    from skillos.api.skills_extract import router as extract_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(skills_router, prefix="/api/skills")
    # extract_router is already included via skills_router.include_router
    return TestClient(app)


class TestExtractRouterRegistration:
    def test_extract_router_included_in_skills(self):
        """Verify extract_router is properly included via skills router."""
        from skillos.api.skills import router as skills_router
        from skillos.api.skills_extract import router as extract_router

        # Both routers should have routes
        assert len(skills_router.routes) >= 30  # skills routes
        assert len(extract_router.routes) >= 6   # extract routes

    def test_dispatch_endpoint_exists(self, client):
        """POST /api/skills/dispatch should exist (even if it returns auth error)."""
        resp = client.post("/api/skills/dispatch", json={"message": "test"})
        # Accept 200, 401, 422 as valid responses (not 404)
        assert resp.status_code != 404, f"Dispatch endpoint not found: {resp.status_code}"

    def test_finalize_endpoint_exists(self, client):
        """POST /api/skills/finalize should exist."""
        resp = client.post("/api/skills/finalize", json={"session_id": "test"})
        assert resp.status_code != 404, f"Finalize endpoint not found: {resp.status_code}"

    def test_status_endpoint_exists(self, client):
        """GET /api/skills/status should exist."""
        resp = client.get("/api/skills/status")
        assert resp.status_code != 404, f"Status endpoint not found: {resp.status_code}"

    def test_ingest_endpoint_exists(self, client):
        """POST /api/skills/ingest should exist."""
        resp = client.post("/api/skills/ingest")
        assert resp.status_code != 404, f"Ingest endpoint not found: {resp.status_code}"


class TestExtractImports:
    def test_re_exported_helpers_importable(self):
        """Verify re-exported helpers are accessible from skills module."""
        from skillos.api.skills import (
            _create_mode_skills_list,
            _finalize_extraction_response,
            _persist_created_skill,
            _run_extraction_dispatch,
        )
        assert callable(_create_mode_skills_list)
        assert callable(_finalize_extraction_response)
        assert callable(_persist_created_skill)
        assert callable(_run_extraction_dispatch)

    def test_shared_models_importable(self):
        """Verify shared Pydantic models import correctly."""
        from skillos.api._skills_shared import DispatchRequest, CreateSkillRequest
        req = DispatchRequest(message="hello")
        assert req.message == "hello"
        req2 = CreateSkillRequest(text="test", content="body")
        assert req2.text == "test"
        assert req2.content == "body"
