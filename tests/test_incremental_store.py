"""Tests for unified incremental store."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    root = tmp_path / "incremental"
    monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", root)
    monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)
    from skillos.knowledge.incremental_store import get_incremental_store
    return get_incremental_store()


class TestIncrementalStore:
    def test_file_ingest_roundtrip(self, store):
        payload = {"filename": "a.txt", "digest": {"title": "T"}}
        store.put_file_ingest("abc" * 10 + "def", payload)
        loaded = store.get_file_ingest("abc" * 10 + "def")
        assert loaded["filename"] == "a.txt"

    def test_source_hash_change_detection(self, store):
        url = "https://example.com/page"
        assert store.check_source_changed(url, "hash_v1") is False
        assert store.check_source_changed(url, "hash_v1") is False
        assert store.check_source_changed(url, "hash_v2") is True

    def test_account_seen_urls(self, store, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skillos.knowledge.incremental_store.LEGACY_WATCH_DIR",
            tmp_path / "watched_accounts",
        )
        assert not store.is_account_url_seen("acc", "https://a/1")
        store.mark_account_url_seen("acc", "https://a/1")
        assert store.is_account_url_seen("acc", "https://a/1")
        accounts = store.list_accounts()
        assert accounts[0]["articles_seen"] == 1

    def test_migrate_legacy_ingest_cache(self, tmp_path, monkeypatch):
        legacy = tmp_path / "legacy_ingest"
        legacy.mkdir()
        (legacy / "deadbeef00000000.json").write_text('{"filename":"old.txt"}', encoding="utf-8")
        root = tmp_path / "incremental"
        monkeypatch.setattr("skillos.knowledge.incremental_store.LEGACY_INGEST_CACHE", legacy)
        monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", root)
        monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)
        from skillos.knowledge.incremental_store import get_incremental_store
        s = get_incremental_store()
        loaded = s.get_file_ingest("deadbeef00000000" + "0" * 48)
        assert loaded is not None
        assert loaded.get("filename") == "old.txt"
        assert (s.files_dir / "deadbeef00000000.json").exists()
