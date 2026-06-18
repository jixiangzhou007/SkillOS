"""Phase 6 — DNA lineage API for frontend tab."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from skillos.api.server import app
    return TestClient(app)


class TestDnaLineageApi:
    def test_get_dna_lineage_refund_skill(self, client):
        r = client.get("/api/skills/电商客服退款处理/dna-lineage")
        assert r.status_code == 200
        data = r.json()
        assert data["skill"] == "电商客服退款处理"
        lineage = data["dna_lineage"]
        assert lineage.get("philosophical")
        assert lineage.get("domain")
        primary = next((d for d in lineage["domain"] if d.get("primary")), None)
        assert primary is not None
        assert primary.get("id") == "workflow-refund"
        assert "title" in primary
        assert "current_version" in primary
        assert "is_stale" in primary

    def test_refresh_dna_lineage(self, client):
        r = client.post("/api/skills/电商客服退款处理/refresh-dna-lineage")
        assert r.status_code == 200
        data = r.json()
        assert data["skill"] == "电商客服退款处理"
        assert "lineage" in data

    def test_dna_lineage_not_found(self, client):
        r = client.get("/api/skills/__nonexistent_skill__/dna-lineage")
        assert r.status_code == 404
