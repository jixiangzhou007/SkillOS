"""Phase 1 — file_ingest SHA256 incremental cache."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _sample_content() -> str:
    return (
        "x" * 300
        + "\n术语Alpha: 定义Alpha\n术语Beta: 定义Beta\n"
        "模式PatternOne: 在场景A中使用\n"
    )


def _write_temp_txt(tmp_path: Path, name: str = "phase1-test.txt") -> Path:
    path = tmp_path / name
    path.write_text(_sample_content(), encoding="utf-8")
    return path


def _mock_digest_result():
    mock_dd = MagicMock()
    mock_dd.glossary = [{"term": "Alpha", "definition": "定义Alpha"}]
    mock_dd.patterns = []
    mock_dd.sections = [{"heading": "h", "summary": "s", "key_points": []}]
    mock_dd.slug = "phase1-test"
    mock_dd.title = "Phase1 Test"
    mock_dd.doc_type = "article"
    mock_dd.cross_references = []
    mock_dd.elapsed_s = 0.1
    return mock_dd


@pytest.fixture
def isolated_ingest_cache(tmp_path, monkeypatch):
    store_root = tmp_path / "incremental"
    store_root.mkdir()
    monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", store_root)
    monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)
    return store_root / "files"


class TestIngestCacheDigestPath:
    def test_digest_success_writes_cache(self, tmp_path, isolated_ingest_cache):
        path = _write_temp_txt(tmp_path)
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        cache_file = isolated_ingest_cache / f"{file_hash[:16]}.json"

        with patch("skillos.knowledge.deep_digest.deep_digest", return_value=_mock_digest_result()), \
             patch("skillos.knowledge.deep_digest.save_digest"), \
             patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]):
            from skillos.utils.file_ingest import ingest_and_learn

            result = ingest_and_learn(str(path), path.name, llm_args=("k", "u", "m", {}))

        assert "digest" in result
        assert cache_file.exists()
        assert result.get("cached_hash") == file_hash[:12]

    def test_second_ingest_returns_from_cache(self, tmp_path, isolated_ingest_cache):
        path = _write_temp_txt(tmp_path)
        deep_digest = MagicMock(return_value=_mock_digest_result())

        with patch("skillos.knowledge.deep_digest.deep_digest", deep_digest), \
             patch("skillos.knowledge.deep_digest.save_digest"), \
             patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]):
            from skillos.utils.file_ingest import ingest_and_learn

            first = ingest_and_learn(str(path), path.name, llm_args=("k", "u", "m", {}))
            second = ingest_and_learn(str(path), path.name, llm_args=("k", "u", "m", {}))

        assert "digest" in first
        assert second.get("from_cache") is True
        assert "digest" in second
        deep_digest.assert_called_once()

    def test_write_ingest_cache_skips_errors(self, tmp_path):
        from skillos.utils.file_ingest import _write_ingest_cache

        cache_file = tmp_path / "abc.json"
        payload = {"filename": "x.txt", "error": "boom"}
        out = _write_ingest_cache(cache_file, "deadbeef" * 4, payload)

        assert out is payload
        assert not cache_file.exists()
