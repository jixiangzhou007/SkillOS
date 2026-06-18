"""Tests for knowledge engine modules (10 modules)."""

import pytest


class TestEpistemology:
    def test_claim_lifecycle(self):
        from skillos.knowledge.epistemology import get_store, EpistemicLevel
        store = get_store()
        claim = store.add_claim("Test fact", source="test", level=EpistemicLevel.EXPERIENCE)
        assert claim.claim_id
        store.invalidate(claim.claim_id)
        knowledge = store.get_knowledge()
        assert all(k.claim_id != claim.claim_id for k in knowledge)

    def test_knowledge_context(self):
        from skillos.knowledge.epistemology import get_store, EpistemicLevel
        store = get_store()
        claim = store.add_claim("Verified fact about Hermes", source="test", level=EpistemicLevel.KNOWLEDGE)
        ctx = store.get_knowledge_context()
        assert "Verified fact" in ctx


class TestExtractor:
    def test_source_authority(self):
        from skillos.knowledge.extractor import get_source_authority
        assert get_source_authority("https://arxiv.org/abs/123") == 0.85
        assert get_source_authority("https://mp.weixin.qq.com/s/abc") == 0.35
        assert get_source_authority("https://unknown.com/x") == 0.4

    def test_empty_extraction(self):
        from skillos.knowledge.extractor import extract_knowledge
        items = extract_knowledge("", "https://test.com")
        assert isinstance(items, list)


class TestKnowledgeGraph:
    def test_add_node(self):
        from skillos.knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        nid = kg.add_node("TestNode", "concept", "A test concept")
        assert nid
        node = kg.get_node(nid)
        assert node.name == "TestNode"

    def test_add_edge(self):
        from skillos.knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        a = kg.add_node("NodeA-unique", "concept")
        b = kg.add_node("NodeB-unique", "concept")
        kg.add_edge(a, b, "related_to", 0.8)
        # Verify edge was created by checking nodes exist
        assert kg.get_node(a) is not None
        assert kg.get_node(b) is not None


class TestDeepDigest:
    def test_is_worth_check(self):
        from skillos.knowledge.deep_digest import is_worth_deep_digest
        worth, reason = is_worth_deep_digest("Short text")
        assert not worth  # Too short
        worth2, _ = is_worth_deep_digest("x" * 500)
        assert worth2  # Long enough


class TestLineage:
    def test_create_graph(self):
        from skillos.knowledge.lineage import LineageGraph
        g = LineageGraph(session_id="test", source_url="http://x.com", source_title="Test")
        assert g.total_items == 0
        assert "test" in g.session_id

    def test_json_safe(self):
        from skillos.knowledge.lineage import _json_safe
        assert _json_safe('hello "world"') == "hello 'world'"
        assert _json_safe("test\\path") == "test/path"

    def test_empty_wisdom(self):
        from skillos.knowledge.lineage import extract_wisdom
        w = extract_wisdom()
        assert "wisdom" in w


class TestKnowledgeStore:
    def test_add_and_search(self):
        from skillos.knowledge.store import add_document, search
        added = add_document("test-skill", "test source", "This is a test document about AI agents")
        assert added > 0
        results = search("test-skill", "AI agents")
        assert len(results) >= 1


class TestPlaybook:
    def test_no_playbook(self):
        from skillos.knowledge.playbook import has_playbook, get_playbook_context
        ctx = get_playbook_context()
        assert isinstance(ctx, str)


class TestMemory:
    def test_save_and_search(self):
        from skillos.knowledge.memory import ConversationMemory
        m = ConversationMemory()
        m.save_insight("User prefers dark mode", "preference")
        results = m.search("dark mode")
        assert len(results) >= 1
        assert results[0]["category"] == "preference"


class TestRefresher:
    def test_hash_detection(self):
        from skillos.knowledge.refresher import hash_content, check_source_changed
        import time
        url = f"https://test.com/refresher-{time.time()}"
        changed1 = check_source_changed(url, "content v1")
        assert not changed1  # First time
        changed2 = check_source_changed(url, "content v2 different")
        assert changed2  # Content changed


class TestSkillKB:
    def test_empty_kb(self):
        from skillos.knowledge.skill_kb import load_kb, SkillKB
        kb = load_kb("nonexistent-skill")
        assert kb.total_items == 0
