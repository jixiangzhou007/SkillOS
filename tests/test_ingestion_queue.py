"""P0 — ingestion queue gap_research and watcher archive fixes."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class TestGapResearch:
    def test_sparse_cluster_uses_label_and_node_ids(self, tmp_path, monkeypatch):
        queue_file = tmp_path / "queue.jsonl"
        monkeypatch.setattr("skillos.knowledge.ingestion_queue.QUEUE_DIR", tmp_path)
        monkeypatch.setattr("skillos.knowledge.ingestion_queue.QUEUE_FILE", queue_file)

        sparse_cluster = MagicMock()
        sparse_cluster.id = "c_sparse_1"
        sparse_cluster.label = "Sparse Topic"
        sparse_cluster.node_ids = ["n1", "n2", "n3"]
        sparse_cluster.cohesion = 0.05

        dense_cluster = MagicMock()
        dense_cluster.id = "c_dense_1"
        dense_cluster.label = "Dense Topic"
        dense_cluster.node_ids = ["n4", "n5"]
        dense_cluster.cohesion = 0.9

        mock_graph = MagicMock()
        mock_graph.detect_clusters.return_value = [sparse_cluster, dense_cluster]
        mock_graph.nodes = {}
        mock_graph.edges = []

        with patch("skillos.knowledge.graph.get_graph", return_value=mock_graph):
            from skillos.knowledge.ingestion_queue import trigger_gap_research

            task_ids = trigger_gap_research()

        assert len(task_ids) == 1
        lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        import json
        task = json.loads(lines[0])
        assert task["source_type"] == "gap_research"
        assert task["source_path"] == "cluster:c_sparse_1"
        assert task["meta"]["cluster_label"] == "Sparse Topic"
        assert task["meta"]["size"] == 3
        assert task["meta"]["cohesion"] == 0.05

    def test_isolated_nodes_use_edge_degree(self, tmp_path, monkeypatch):
        queue_file = tmp_path / "queue.jsonl"
        monkeypatch.setattr("skillos.knowledge.ingestion_queue.QUEUE_DIR", tmp_path)
        monkeypatch.setattr("skillos.knowledge.ingestion_queue.QUEUE_FILE", queue_file)

        edge_ab = SimpleNamespace(source_id="a", target_id="b")
        edge_bc = SimpleNamespace(source_id="b", target_id="c")

        mock_graph = MagicMock()
        mock_graph.detect_clusters.return_value = []
        mock_graph.nodes = {"a": MagicMock(), "b": MagicMock(), "c": MagicMock(), "d": MagicMock()}
        mock_graph.edges = [edge_ab, edge_bc]

        with patch("skillos.knowledge.graph.get_graph", return_value=mock_graph):
            from skillos.knowledge.ingestion_queue import trigger_gap_research

            task_ids = trigger_gap_research()

        assert len(task_ids) == 1
        import json
        task = json.loads(queue_file.read_text(encoding="utf-8").strip())
        assert task["source_path"].startswith("isolated_nodes:")
        assert task["meta"]["isolated_count"] == 3
        assert set(task["meta"]["sample_ids"]) == {"a", "c", "d"}


class TestWatcherArchive:
    def test_ingest_callback_archives_after_enqueue(self, tmp_path, monkeypatch):
        watch_dir = tmp_path / "inbox"
        watch_dir.mkdir()
        filepath = watch_dir / "note.txt"
        filepath.write_text("hello", encoding="utf-8")

        monkeypatch.setattr("skillos.utils.watcher.get_watch_dir", lambda: watch_dir)

        with patch("skillos.knowledge.ingestion_queue.enqueue") as mock_enqueue:
            from skillos.utils.watcher import ingest_callback

            result = ingest_callback(filepath)

        assert result["enqueued"] is True
        mock_enqueue.assert_called_once()
        assert not filepath.exists()
        archived = watch_dir / ".processed" / "note.txt"
        assert archived.exists()


class TestQueueUnifiedExit:
    def test_url_digest_calls_finalize_ingest(self, monkeypatch):
        with patch("skillos.utils.web_fetch.fetch", return_value="x" * 200), \
             patch("skillos.knowledge.ingest_dedup.should_skip_ingest", return_value=False), \
             patch("skillos.knowledge.content_classify.classify_content", return_value="conceptual"), \
             patch("skillos.knowledge.precipitation.precipitate_conceptual_source") as mock_conceptual:
            mock_conceptual.return_value = {
                "title": "Queue Doc",
                "lineage_applied": True,
            }
            from skillos.knowledge.ingestion_queue import IngestionTask, process_ingestion_task

            result = process_ingestion_task(
                IngestionTask(
                    task_id="t1", source_type="url", source_path="https://queue.test/article",
                ),
                llm_args=("k", "u", "m", {}),
            )

        assert "digest:Queue Doc:lineage=yes" == result
        mock_conceptual.assert_called_once()
        assert mock_conceptual.call_args.kwargs.get("channel") == "ingestion_queue"
