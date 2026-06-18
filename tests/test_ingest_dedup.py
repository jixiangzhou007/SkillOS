"""Ingest deduplication — skip unchanged URL content."""

from unittest.mock import MagicMock, patch

import pytest


class TestIngestDedup:
    def test_should_skip_when_hash_matches(self, tmp_path, monkeypatch):
        monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", tmp_path)
        monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)

        from skillos.knowledge.ingest_dedup import mark_ingest_complete, should_skip_ingest

        url = "https://dedup.test/doc"
        content = "x" * 300
        assert should_skip_ingest(url, content) is False
        mark_ingest_complete(url, content)
        assert should_skip_ingest(url, content) is True
        assert should_skip_ingest(url, content + "changed") is False

    def test_enqueue_skips_duplicate_pending(self, tmp_path, monkeypatch):
        queue_file = tmp_path / "queue.jsonl"
        monkeypatch.setattr("skillos.knowledge.ingestion_queue.QUEUE_DIR", tmp_path)
        monkeypatch.setattr("skillos.knowledge.ingestion_queue.QUEUE_FILE", queue_file)

        from skillos.knowledge.ingestion_queue import enqueue

        first = enqueue("url", "https://dup.test/a")
        second = enqueue("url", "https://dup.test/a")
        assert first.task_id == second.task_id
        lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_queue_skips_unchanged_url(self, monkeypatch):
        task = MagicMock()
        task.source_type = "url"
        task.source_path = "https://skip.test/doc"

        with patch("skillos.utils.web_fetch.fetch", return_value="same" * 50), \
             patch("skillos.knowledge.ingest_dedup.should_skip_ingest", return_value=True):
            from skillos.knowledge.ingestion_queue import IngestionTask, process_ingestion_task

            result = process_ingestion_task(
                IngestionTask(task_id="t1", source_type="url", source_path=task.source_path),
            )

        assert result.startswith("skipped:unchanged:")

    def test_cycle_skips_unchanged_content(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "cycle_tasks"
        monkeypatch.setattr("skillos.knowledge.cycle_tasks.TASKS_DIR", tasks_dir)

        with patch("skillos.knowledge.ingest_dedup.should_skip_ingest", return_value=True), \
             patch("skillos.knowledge.ingest_pipeline.run_full_knowledge_cycle") as mock_run:
            from skillos.knowledge.cycle_tasks import get_cycle_task, submit_cycle_task

            task = submit_cycle_task("body", "https://skip-cycle.test", ("k",))
            import time
            deadline = time.time() + 5
            final = None
            while time.time() < deadline:
                final = get_cycle_task(task.task_id)
                if final and final.status == "completed":
                    break
                time.sleep(0.05)

        assert final is not None
        assert final.result.get("skipped") is True
        mock_run.assert_not_called()
