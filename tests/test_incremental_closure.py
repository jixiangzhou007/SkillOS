"""Phase 5 — watcher / refresher / incremental closure."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestFileWatcherModify:
    def test_reingest_on_content_change(self, tmp_path):
        from skillos.utils.watcher import FileWatcher

        calls: list[str] = []

        def callback(path: Path) -> None:
            calls.append(path.read_text(encoding="utf-8"))

        watch_dir = tmp_path / "inbox"
        watch_dir.mkdir()
        target = watch_dir / "note.txt"
        target.write_text("version-one " + "x" * 50, encoding="utf-8")

        watcher = FileWatcher(watch_dir, callback, interval=0.01)
        watcher._scan()
        assert len(calls) == 1
        assert calls[0].startswith("version-one")

        target.write_text("version-two " + "y" * 50, encoding="utf-8")
        watcher._scan()
        assert len(calls) == 2
        assert calls[1].startswith("version-two")

    def test_hidden_files_ignored(self, tmp_path):
        from skillos.utils.watcher import FileWatcher

        calls: list[Path] = []
        watch_dir = tmp_path / "inbox"
        watch_dir.mkdir()
        (watch_dir / ".hidden.txt").write_text("secret", encoding="utf-8")

        watcher = FileWatcher(watch_dir, lambda p: calls.append(p), interval=0.01)
        watcher._scan()
        assert calls == []


class TestPeriodicRefresh:
    def test_start_and_stop(self):
        from skillos.knowledge.refresher import (
            is_periodic_refresh_running,
            start_periodic_refresh,
            stop_periodic_refresh,
        )

        stop_periodic_refresh()
        assert not is_periodic_refresh_running()
        start_periodic_refresh(interval_hours=9999)
        assert is_periodic_refresh_running()
        stop_periodic_refresh()
        assert not is_periodic_refresh_running()

    def test_refresh_if_changed_calls_post_ingest(self, monkeypatch, tmp_path):
        store_root = tmp_path / "incremental"
        store_root.mkdir()
        monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", store_root)
        monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)

        url = "https://phase5.test/article"
        old_content = "old article " + "a" * 250
        new_content = "new article " + "b" * 250

        from skillos.knowledge.refresher import check_source_changed, refresh_if_changed

        check_source_changed(url, old_content)

        mock_dd = MagicMock()
        mock_dd.title = "Updated"
        mock_dd.glossary = [{"term": "T", "definition": "D"}]
        mock_dd.patterns = []
        mock_dd.sections = []
        mock_dd.cross_references = []
        mock_dd.elapsed_s = 0.1

        with patch("skillos.utils.web_fetch.fetch", return_value=new_content), \
             patch("skillos.knowledge.deep_digest.deep_digest", return_value=mock_dd), \
             patch("skillos.knowledge.deep_digest.save_digest"), \
             patch("skillos.knowledge.ingest_pipeline.post_ingest", return_value={"lineage_applied": True}) as mock_post:
            result = refresh_if_changed(url, ("k", "u", "m", {}))

        assert result is not None
        mock_post.assert_called_once()


class TestLifespanBackgroundServices:
    @pytest.mark.asyncio
    async def test_lifespan_starts_refresher_by_default(self, monkeypatch):
        monkeypatch.delenv("SKILLOS_ENABLE_REFRESH", raising=False)
        monkeypatch.delenv("SKILLOS_DISABLE_REFRESH", raising=False)
        monkeypatch.delenv("SKILLOS_ENABLE_WATCHER", raising=False)

        from skillos.config import reset_config
        from skillos.knowledge.refresher import is_periodic_refresh_running, stop_periodic_refresh
        from skillos.utils.watcher import is_watching, stop_watching

        reset_config()
        stop_periodic_refresh()
        stop_watching()

        from skillos.api.server import _lifespan

        app = MagicMock()
        async with _lifespan(app):
            assert is_periodic_refresh_running()
            assert not is_watching()
        stop_periodic_refresh()

    @pytest.mark.asyncio
    async def test_lifespan_skips_refresher_when_disabled(self, monkeypatch):
        monkeypatch.setenv("SKILLOS_DISABLE_REFRESH", "1")
        monkeypatch.delenv("SKILLOS_ENABLE_WATCHER", raising=False)

        from skillos.config import reset_config
        from skillos.knowledge.refresher import is_periodic_refresh_running, stop_periodic_refresh
        from skillos.utils.watcher import is_watching, stop_watching

        reset_config()
        stop_periodic_refresh()
        stop_watching()

        from skillos.api.server import _lifespan

        app = MagicMock()
        async with _lifespan(app):
            assert not is_periodic_refresh_running()
            assert not is_watching()


class TestAccountWatcherSourceCache:
    def test_marks_source_hash_after_ingest(self, tmp_path, monkeypatch):
        store_root = tmp_path / "incremental"
        store_root.mkdir()
        monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", store_root)
        monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)

        mock_dd = MagicMock()
        mock_dd.title = "Article"
        mock_dd.glossary = [{"term": "A", "definition": "B"}]
        mock_dd.patterns = []
        mock_dd.sections = []

        url = "https://mp.weixin.qq.com/s/phase5-test"
        content = "article body " + "z" * 250

        with patch("skillos.utils.account_watcher.fetch_account_articles", return_value=[{"url": url}]), \
             patch("skillos.utils.account_watcher.is_new_article", return_value=True), \
             patch("skillos.knowledge.ingestion_queue.enqueue", side_effect=RuntimeError("force direct ingest")), \
             patch("skillos.utils.wechat_fetch.fetch", return_value=content), \
             patch("skillos.knowledge.deep_digest.deep_digest", return_value=mock_dd), \
             patch("skillos.knowledge.deep_digest.save_digest"), \
             patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]), \
             patch("skillos.knowledge.ingest_pipeline.post_ingest"), \
             patch("skillos.utils.account_watcher.WATCH_DIR", tmp_path):
            from skillos.utils.account_watcher import add_account

            add_account("test-account")

        hash_files = list((store_root / "index.json").parent.glob("**/*"))
        assert (store_root / "index.json").exists()
        from skillos.knowledge.incremental_store import get_incremental_store
        assert get_incremental_store().get_source_hash(url)
