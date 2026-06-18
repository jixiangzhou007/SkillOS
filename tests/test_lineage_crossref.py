"""Phase 3 — 4-signal lineage cross-reference engine."""

import json
from pathlib import Path

import pytest

from skillos.knowledge.lineage import (
    KnowledgeItem,
    SourceChunk,
    append_items_to_lineage,
    build_cross_references,
    load_lineage,
)


def _item(
    item_id: str,
    content: str,
    *,
    category: str = "concept",
    source_url: str = "",
    affected_skills: list | None = None,
) -> KnowledgeItem:
    chunk = SourceChunk(source_url=source_url) if source_url else None
    return KnowledgeItem(
        item_id=item_id,
        content=content,
        category=category,
        source_chunk=chunk,
        affected_skills=affected_skills or [],
    )


class TestBuildCrossReferences:
    def test_same_source_shared_words_creates_same_source_edge(self):
        chunk_url = "https://example.com/doc-a"
        items = [
            _item("ki_1", "alpha beta gamma delta", source_url=chunk_url),
            _item("ki_2", "alpha beta epsilon zeta", category="heuristic", source_url=chunk_url),
        ]

        edges = build_cross_references(items)

        assert edges == 1
        assert items[0].related_items[0]["relation_type"] == "same_source"
        assert items[0].related_items[0]["item_id"] == "ki_2"
        assert items[0].related_items[0]["weight"] > 0.25

    def test_unrelated_items_no_edge(self):
        items = [
            _item("ki_a", "foo bar baz qux"),
            _item("ki_b", "one two three four"),
        ]
        assert build_cross_references(items) == 0
        assert items[0].related_items == []

    def test_below_threshold_no_edge(self):
        items = [
            _item("ki_1", "aaa bbb ccc ddd eee fff ggg hhh iii", source_url="https://a"),
            _item("ki_2", "aaa bbb xxx yyy zzz www vvv uuu ttt", category="heuristic", source_url="https://b"),
        ]
        assert build_cross_references(items) == 0

    def test_shared_skills_creates_linked_edge(self):
        items = [
            _item(
                "ki_1",
                "alpha beta gamma delta",
                source_url="https://a",
                affected_skills=[{"skill_name": "合同审核"}],
            ),
            _item(
                "ki_2",
                "alpha beta epsilon zeta",
                category="heuristic",
                source_url="https://b",
                affected_skills=[{"skill_name": "合同审核"}],
            ),
        ]

        edges = build_cross_references(items)

        assert edges == 1
        assert items[0].related_items[0]["relation_type"] == "linked"

    def test_idempotent_skips_existing_edges(self):
        items = [
            _item("ki_1", "alpha beta gamma delta", source_url="https://same"),
            _item("ki_2", "alpha beta epsilon zeta", source_url="https://same"),
        ]
        assert build_cross_references(items) == 1
        assert build_cross_references(items) == 0


class TestAppendItemsToLineage:
    def test_persists_session_and_cross_refs(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": True, "session_id": session_id},
        )

        items = [
            _item("ki_1", "alpha beta gamma delta", source_url="https://phase3.test/doc"),
            _item("ki_2", "alpha beta epsilon zeta", category="heuristic", source_url="https://phase3.test/doc"),
        ]
        result = append_items_to_lineage(
            items,
            source_url="https://phase3.test/doc",
            source_title="Phase3 Doc",
            sync_graph=True,
        )

        assert result["items_added"] == 2
        assert result["edges_created"] == 1
        assert result["linked_items"] == 1
        assert result["graph_sync"]["synced"] is True

        session_file = lineage_dir / f"{result['session_id']}.json"
        assert session_file.exists()
        saved = json.loads(session_file.read_text(encoding="utf-8"))
        assert saved["summary"]["total_items"] == 2

        loaded = load_lineage(result["session_id"])
        assert loaded is not None
        assert loaded.total_items == 2

    def test_incremental_append_reuses_session(self, tmp_path, monkeypatch):
        lineage_dir = tmp_path / "lineage"
        lineage_dir.mkdir()
        monkeypatch.setattr("skillos.knowledge.lineage.LINEAGE_DIR", lineage_dir)
        monkeypatch.setattr(
            "skillos.knowledge.lineage.sync_lineage_to_graph",
            lambda session_id: {"synced": False},
        )

        url = "https://phase3.test/incremental"
        batch1 = [_item("ki_1", "alpha beta gamma delta", source_url=url)]
        batch2 = [_item("ki_2", "alpha beta epsilon zeta", category="heuristic", source_url=url)]

        r1 = append_items_to_lineage(batch1, source_url=url, sync_graph=False)
        r2 = append_items_to_lineage(batch2, source_url=url, sync_graph=False)

        assert r1["session_id"] == r2["session_id"]
        assert r2["total_items"] == 2
        assert r2["edges_created"] == 1
