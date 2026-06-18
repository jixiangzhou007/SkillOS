"""P2 — default refresher + ingest metrics."""

import json
import time
from pathlib import Path

import pytest


class TestRefreshDefault:
    def test_refresh_enabled_by_default(self, monkeypatch):
        monkeypatch.delenv("SKILLOS_ENABLE_REFRESH", raising=False)
        monkeypatch.delenv("SKILLOS_DISABLE_REFRESH", raising=False)
        from skillos.config import reset_config, get_config

        reset_config()
        assert get_config().enable_periodic_refresh is True

    def test_refresh_disabled_explicitly(self, monkeypatch):
        monkeypatch.setenv("SKILLOS_ENABLE_REFRESH", "0")
        monkeypatch.delenv("SKILLOS_DISABLE_REFRESH", raising=False)
        from skillos.config import reset_config, get_config

        reset_config()
        assert get_config().enable_periodic_refresh is False

    def test_refresh_disabled_via_disable_flag(self, monkeypatch):
        monkeypatch.setenv("SKILLOS_DISABLE_REFRESH", "1")
        monkeypatch.delenv("SKILLOS_ENABLE_REFRESH", raising=False)
        from skillos.config import reset_config, get_config

        reset_config()
        assert get_config().enable_periodic_refresh is False


class TestIngestMetrics:
    def test_record_and_summarize(self, tmp_path, monkeypatch):
        metrics_path = tmp_path / "ingest_metrics.jsonl"
        monkeypatch.setattr("skillos.knowledge.ingest_metrics.METRICS_PATH", metrics_path)

        from skillos.knowledge.ingest_metrics import get_metrics_summary, record_ingest_event

        record_ingest_event(
            channel="test",
            source_url="https://metrics.test/a",
            lineage={"lineage_applied": True, "items_added": 2, "edges_created": 1},
        )
        record_ingest_event(
            channel="test",
            source_url="https://metrics.test/b",
            lineage={"lineage_applied": False, "reason": "boom"},
        )
        record_ingest_event(
            channel="test",
            source_url="https://metrics.test/c",
            lineage={"lineage_applied": False, "reason": "no_items"},
        )

        summary = get_metrics_summary(window_hours=24)
        assert summary["total_events"] == 3
        assert summary["success_count"] == 2
        assert summary["lineage_applied_count"] == 1
        assert summary["success_rate"] == pytest.approx(0.667, abs=0.01)
        assert summary["lineage_coverage_rate"] == pytest.approx(0.333, abs=0.01)
        assert summary["by_channel"]["test"]["total"] == 3

    def test_post_ingest_records_metric(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        metrics_path = tmp_path / "ingest_metrics.jsonl"
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr("skillos.knowledge.ingest_metrics.METRICS_PATH", metrics_path)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": False},
        )

        from skillos.knowledge.ingest_pipeline import post_ingest
        from skillos.knowledge.ingest_metrics import get_metrics_summary

        mock_dd = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        mock_dd.title = "Metrics Doc"
        mock_dd.glossary = [{"term": "T", "definition": "D"}]
        mock_dd.patterns = []
        mock_dd.sections = []
        mock_dd.cross_references = []

        post_ingest("x" * 300, "https://metrics-post.test", digest_result=mock_dd, channel="metrics_test")
        summary = get_metrics_summary(window_hours=1)
        assert summary["total_events"] >= 1
        assert summary["lineage_applied_count"] >= 1


class TestMetricsAPI:
    def test_metrics_endpoint(self):
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        client = TestClient(app)
        resp = client.get("/api/knowledge/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "success_rate" in data
        assert "lineage_coverage_rate" in data
        assert "refresher" in data
