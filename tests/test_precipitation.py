"""Precipitation orchestration — behavior-preserving wrappers."""

from unittest.mock import patch

import pytest


class TestLegacyQueueFlag:
    def test_legacy_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("SKILLOS_PRECIPITATION_LEGACY_QUEUE", raising=False)
        from skillos.knowledge.precipitation import legacy_queue_enabled

        assert legacy_queue_enabled() is False

    def test_legacy_enabled_via_env(self, monkeypatch):
        monkeypatch.setenv("SKILLOS_PRECIPITATION_LEGACY_QUEUE", "true")
        from skillos.knowledge.precipitation import legacy_queue_enabled

        assert legacy_queue_enabled() is True


class TestPrecipitateActionableSource:
    def test_persists_by_default(self, monkeypatch):
        monkeypatch.delenv("SKILLOS_PRECIPITATION_LEGACY_QUEUE", raising=False)
        doc = {"name": "test-skill", "content": "# skill\nbody"}

        with patch(
            "skillos.knowledge.precipitation.learn_skill_from_source",
            return_value=("ok", doc),
        ) as mock_learn, patch(
            "skillos.knowledge.precipitation.persist_skill_document",
            return_value={"lineage": {"lineage_applied": True}},
        ) as mock_persist:
            from skillos.knowledge.precipitation import precipitate_actionable_source

            result = precipitate_actionable_source(
                "https://example.com/a",
                "x" * 300,
                ("k", "u", "m", {}),
                channel="test",
            )

        mock_learn.assert_called_once()
        mock_persist.assert_called_once()
        assert result.skill_name == "test-skill"
        assert result.persisted is True
        assert "persisted" in result.queue_message()

    def test_legacy_skips_persist(self, monkeypatch):
        monkeypatch.setenv("SKILLOS_PRECIPITATION_LEGACY_QUEUE", "1")
        doc = {"name": "legacy-skill", "content": "body"}

        with patch(
            "skillos.knowledge.precipitation.learn_skill_from_source",
            return_value=("ok", doc),
        ), patch(
            "skillos.knowledge.precipitation.persist_skill_document",
        ) as mock_persist, patch(
            "skillos.knowledge.precipitation.finalize_skill_lineage_only",
            return_value={"lineage": {"lineage_applied": True}},
        ) as mock_lineage:
            from skillos.knowledge.precipitation import precipitate_actionable_source

            result = precipitate_actionable_source(
                "https://example.com/b",
                "x" * 300,
                ("k", "u", "m", {}),
            )

        mock_persist.assert_not_called()
        mock_lineage.assert_called_once()
        assert result.persisted is False
        assert "lineage_only" in result.queue_message()

    def test_persist_failure_falls_back_to_lineage(self, monkeypatch):
        monkeypatch.delenv("SKILLOS_PRECIPITATION_LEGACY_QUEUE", raising=False)
        doc = {"name": "fallback-skill", "content": "body"}

        with patch(
            "skillos.knowledge.precipitation.learn_skill_from_source",
            return_value=("ok", doc),
        ), patch(
            "skillos.knowledge.precipitation.persist_skill_document",
            side_effect=RuntimeError("quota"),
        ), patch(
            "skillos.knowledge.precipitation.finalize_skill_lineage_only",
            return_value={"lineage": {"lineage_applied": True}},
        ) as mock_lineage:
            from skillos.knowledge.precipitation import precipitate_actionable_source

            result = precipitate_actionable_source(
                "https://example.com/c",
                "x" * 300,
                ("k", "u", "m", {}),
            )

        mock_lineage.assert_called_once()
        assert result.persisted is False
        assert result.warnings
        assert result.lineage_applied is True


class TestQueueActionableUrl:
    def test_queue_actionable_calls_persist(self, monkeypatch):
        monkeypatch.delenv("SKILLOS_PRECIPITATION_LEGACY_QUEUE", raising=False)

        with patch("skillos.utils.web_fetch.fetch", return_value="x" * 200), \
             patch("skillos.knowledge.ingest_dedup.should_skip_ingest", return_value=False), \
             patch("skillos.knowledge.content_classify.classify_content", return_value="actionable"), \
             patch("skillos.knowledge.precipitation.precipitate_actionable_source") as mock_prec, \
             patch("skillos.knowledge.ingest_dedup.mark_ingest_complete"):
            mock_prec.return_value.queue_message.return_value = "skill:q-skill:lineage=yes:persisted"
            from skillos.knowledge.ingestion_queue import IngestionTask, process_ingestion_task

            result = process_ingestion_task(
                IngestionTask(
                    task_id="t2", source_type="url", source_path="https://queue.test/skill",
                ),
                llm_args=("k", "u", "m", {}),
            )

        mock_prec.assert_called_once()
        assert result == "skill:q-skill:lineage=yes:persisted"
