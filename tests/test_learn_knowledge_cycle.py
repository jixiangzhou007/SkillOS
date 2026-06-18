"""Legacy closure: learn_knowledge fallback + full_knowledge_cycle API entry."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _mock_digest():
    dd = MagicMock()
    dd.title = "Cycle Test Doc"
    dd.slug = "cycle-test"
    dd.doc_type = "article"
    dd.glossary = [{"term": "TermA", "definition": "Definition A"}]
    dd.patterns = [{"name": "Pat1", "description": "Pattern one alpha beta"}]
    dd.sections = [{"heading": "Intro", "summary": "Summary alpha beta gamma", "key_points": []}]
    dd.cross_references = []
    dd.elapsed_s = 0.1
    return dd


class TestLearnKnowledge:
    def test_learn_knowledge_empty(self):
        from skillos.knowledge.extractor import learn_knowledge

        with patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]):
            result = learn_knowledge("short", "https://empty.test")

        assert result == {"extracted": 0, "verified": 0, "needs_review": 0, "saved": 0}

    def test_learn_knowledge_with_items(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": False},
        )

        from skillos.knowledge.extractor import KnowledgeItem, learn_knowledge

        items = [
            KnowledgeItem(
                item_id="ki_test01",
                content="Alpha beta gamma delta epsilon",
                category="fact",
                confidence=0.8,
                source_url="https://learn.test/doc",
            )
        ]

        with patch("skillos.knowledge.extractor.extract_knowledge", return_value=items), \
             patch("skillos.knowledge.extractor.verify_knowledge", side_effect=lambda i, _: i), \
             patch("skillos.knowledge.extractor.save_knowledge", return_value=1), \
             patch("skillos.knowledge.extractor.load_all_knowledge", return_value=[]):
            result = learn_knowledge("x" * 300, "https://learn.test/doc")

        assert result["extracted"] == 1
        assert result["saved"] == 1
        assert result["lineage"]["lineage_applied"] is True
        assert list(lineage_dir.glob("*.json"))


class TestFullKnowledgeCycle:
    def test_full_knowledge_cycle(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr("skillos.knowledge.extractor.KNOWLEDGE_DIR", knowledge_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": True, "session_id": session_id},
        )

        with patch("skillos.knowledge.deep_digest.deep_digest", return_value=_mock_digest()), \
             patch("skillos.knowledge.deep_digest.save_digest"), \
             patch("skillos.knowledge.extractor.extract_knowledge", return_value=[]), \
             patch("skillos.knowledge.lineage.detect_surprise"), \
             patch("skillos.knowledge.lineage.trigger_pattern_mining", return_value={"mined": 0}), \
             patch("skillos.knowledge.lineage.run_consolidation_cycle", return_value={"ok": True}), \
             patch("skillos.knowledge.lineage.extract_wisdom", return_value={"wisdom": False, "insights": []}), \
             patch("skillos.skills.skill_store.list_skills", return_value=["合同审核", "brainstorming"]), \
             patch("skillos.skills.skill_store.get_skill_body", return_value="alpha beta gamma delta epsilon zeta"), \
             patch("skillos.skills.skill_store.load_skill", return_value=MagicMock()):
            from skillos.knowledge.lineage import full_knowledge_cycle

            result = full_knowledge_cycle(
                "z" * 400 + "\nAlphaTerm: definition\n",
                "https://cycle.test/doc",
                ("key", "url", "model", {}),
            )

        assert result["session_id"]
        assert result["digest"]["glossary_terms"] >= 1
        assert result["lineage"]["lineage_applied"] is True
        assert "elapsed_s" in result

    def test_run_full_knowledge_cycle_wrapper(self):
        from skillos.knowledge import ingest_pipeline

        with patch(
            "skillos.knowledge.lineage.full_knowledge_cycle",
            return_value={"session_id": "cycle_mock"},
        ) as mock_cycle:
            out = ingest_pipeline.run_full_knowledge_cycle("body", "https://x", ("k",))

        mock_cycle.assert_called_once()
        assert out["session_id"] == "cycle_mock"


class TestKnowledgeCycleAPI:
    def test_post_cycle_endpoint(self):
        """Backward-compatible name — delegates to async task API."""
        from fastapi.testclient import TestClient

        from skillos.api.server import app

        payload = {
            "content": "y" * 400 + "\nTermX: definition here\n",
            "source_url": "https://api-cycle.test/doc",
        }

        with patch("skillos.config.get_config") as mock_cfg, \
             patch(
                 "skillos.knowledge.ingest_pipeline.run_full_knowledge_cycle",
                 return_value={"session_id": "api_cycle_1", "lineage": {"lineage_applied": True}},
             ):
            mock_cfg.return_value.to_llm_args.return_value = ("key", "url", "model", {})
            client = TestClient(app)
            resp = client.post("/api/knowledge/cycle", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"].startswith("kc_")
        assert "poll_url" in data
