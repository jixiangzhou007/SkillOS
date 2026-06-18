"""P1 — user-visible lineage notices and review queue."""

import pytest


class TestLineageNotice:
    def test_format_success(self):
        from skillos.knowledge.ingest_pipeline import format_lineage_notice

        notice = format_lineage_notice({
            "lineage_applied": True,
            "items_added": 3,
            "edges_created": 2,
            "session_id": "sess_abc123456789",
        })
        assert "✓" in notice
        assert "3" in notice
        assert "2" in notice

    def test_format_no_items(self):
        from skillos.knowledge.ingest_pipeline import format_lineage_notice

        notice = format_lineage_notice({"lineage_applied": False, "reason": "no_items"})
        assert "未提取" in notice

    def test_format_failure(self):
        from skillos.knowledge.ingest_pipeline import format_lineage_notice

        notice = format_lineage_notice({"lineage_applied": False, "reason": "disk full"})
        assert "失败" in notice
        assert "disk full" in notice

    def test_enrich_with_lineage_warning(self):
        from skillos.knowledge.ingest_pipeline import enrich_with_lineage

        payload = enrich_with_lineage({}, {"lineage_applied": False, "reason": "boom"})
        assert payload["lineage_notice"]
        assert payload["warnings"]


class TestReviewAPI:
    def test_review_endpoint(self):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        client = TestClient(app)
        resp = client.get("/api/knowledge/review")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "items" in data

    def test_cycle_recent_endpoint(self):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        client = TestClient(app)
        resp = client.get("/api/knowledge/cycle/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data

    def test_queue_endpoint(self):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        client = TestClient(app)
        resp = client.get("/api/knowledge/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "tasks" in data
        assert "pending" in data["stats"]
