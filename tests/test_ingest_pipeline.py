"""Phase 4 — ingest_pipeline post_ingest integration."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _mock_digest():
    dd = MagicMock()
    dd.title = "Phase4 Test Doc"
    dd.glossary = [{"term": "AlphaTerm", "definition": "Alpha definition here"}]
    dd.patterns = [{"name": "PatternOne", "description": "Pattern description here"}]
    dd.sections = [{"heading": "Intro", "summary": "Intro summary alpha beta", "key_points": []}]
    dd.cross_references = [{"skill_name": "合同审核", "relation": "补充知识", "note": "相关"}]
    return dd


class TestIngestPipeline:
    def test_post_ingest_from_digest(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": True, "session_id": session_id},
        )

        from skillos.knowledge.ingest_pipeline import post_ingest

        result = post_ingest(
            "x" * 400,
            "https://phase4.test/doc",
            source_title="Phase4 Test Doc",
            digest_result=_mock_digest(),
            channel="test",
        )

        assert result["lineage_applied"] is True
        assert result["items_added"] >= 2
        assert result["session_id"]
        session_file = lineage_dir / f"{result['session_id']}.json"
        assert session_file.exists()
        saved = json.loads(session_file.read_text(encoding="utf-8"))
        assert saved["summary"]["total_items"] >= 2

    def test_post_ingest_skill_precipitation(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": False},
        )

        from skillos.knowledge.ingest_pipeline import post_ingest

        body = (
            "# 技能名称：合同审核\n\n"
            "## 核心问题\n审核采购合同风险\n\n"
            "## S_body\n1. 读合同\n"
        )
        result = post_ingest(
            body,
            "skill://合同审核",
            source_title="合同审核",
            skill_name="合同审核",
            skill_body=body,
            sync_graph=False,
            channel="skill_precipitation",
        )

        assert result["lineage_applied"] is True
        assert result["items_added"] == 1
        session_file = lineage_dir / f"{result['session_id']}.json"
        assert session_file.exists()

    def test_post_ingest_no_items(self):
        from skillos.knowledge.ingest_pipeline import post_ingest

        result = post_ingest("short", "https://empty.test")
        assert result["lineage_applied"] is False
        assert result["reason"] == "no_items"

    def test_finalize_ingest_unified_payload(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": False},
        )

        from skillos.knowledge.ingest_pipeline import finalize_ingest

        out = finalize_ingest(
            "x" * 400,
            "https://finalize.test/doc",
            digest_result=_mock_digest(),
            channel="test_finalize",
            payload={"saved": 3},
        )
        assert out["saved"] == 3
        assert out["lineage"]["lineage_applied"] is True
        assert "lineage_notice" in out

    def test_finalize_ingest_failure_adds_warning(self, monkeypatch):
        monkeypatch.setattr(
            "skillos.knowledge.ingest_pipeline.post_ingest",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        recorded = []
        monkeypatch.setattr(
            "skillos.knowledge.ingest_metrics.record_ingest_event",
            lambda **kw: recorded.append(kw),
        )

        from skillos.knowledge.ingest_pipeline import finalize_ingest

        out = finalize_ingest("content", "https://fail.test", channel="test_fail")
        assert out["lineage"]["lineage_applied"] is False
        assert out["warnings"]
        assert recorded and recorded[0]["channel"] == "test_fail"


class TestFileIngestLineageHook:
    def test_ingest_and_learn_records_lineage(self, tmp_path, monkeypatch):
        store_root = tmp_path / "incremental"
        store_root.mkdir()
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.incremental_store.INCREMENTAL_DIR", store_root)
        monkeypatch.setattr("skillos.knowledge.incremental_store._store", None)
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": False},
        )

        content = "z" * 300 + "\nAlphaTerm: definition\nBetaTerm: other\n"
        path = tmp_path / "phase4-ingest.txt"
        path.write_text(content, encoding="utf-8")

        with patch("skillos.knowledge.deep_digest.deep_digest", return_value=_mock_digest()), \
             patch("skillos.knowledge.deep_digest.save_digest"), \
             patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]):
            from skillos.utils.file_ingest import ingest_and_learn

            result = ingest_and_learn(str(path), path.name, llm_args=("k", "u", "m", {}))

        assert "lineage" in result
        assert result["lineage"]["lineage_applied"] is True
        assert list(lineage_dir.glob("*.json"))

    def test_items_from_digest_sets_affected_skills(self):
        from skillos.knowledge.ingest_pipeline import items_from_digest

        items = items_from_digest(_mock_digest(), "https://phase4.test/doc", "content")
        assert items
        assert any(item.affected_skills for item in items)
        assert items[0].affected_skills[0]["skill_name"] == "合同审核"
