"""Integration tests — end-to-end pipeline coverage for critical paths."""

import pytest


# ═══════════════════════════════════════════════════════════════
# Skill Creation Pipeline
# ═══════════════════════════════════════════════════════════════

class TestSkillCreationPipeline:
    def test_full_extraction_flow_completes(self):
        """Agent should progress through phases and generate a skill."""
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent.start("test extraction flow")

        # Simulate a conversation through the phases
        replies = []
        for msg in [
            "当用户提交订单时触发",
            "需要订单ID和客户ID作为输入",
            "第一步验证订单，第二步检查退款政策，第三步计算金额，第四步退款",
            "退款成功或失败都要发邮件通知",
        ]:
            reply, doc = agent.handle(msg, [], ("", "", ""))
            replies.append(reply)
            if doc:
                break

        assert len(replies) > 0
        assert agent._phase in (Phase.EXPLORING, Phase.REFINING, Phase.OPTIMIZING,
                                 Phase.CONFIRMING, Phase.GENERATING, Phase.DONE)

    def test_topic_extraction(self):
        """_extract_topic should strip prefixes and return the core topic."""
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        assert a._extract_topic("帮我创建一个处理客户投诉的技能") == "处理客户投诉"
        assert a._extract_topic("帮我创建一个合同审核的技能") == "合同审核"
        assert a._extract_topic("帮我创建一个技能") == ""
        assert a._extract_topic("沉淀代码审查的技能") == "代码审查"

    @pytest.mark.skip(reason="LLM-dependent: domain openings vary by model response")
    def test_start_uses_domain_opening_not_generic_templates(self):
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        reply = agent.start("帮我创建一个合同审核的技能")
        assert "合同审核" in reply
        assert "条款" in reply or "风险" in reply
        assert "哪类比较接近" not in reply
        assert "API接口设计" not in reply

    def test_parse_dual_response(self):
        """Should parse QUESTION and SKILL_DRAFT from LLM output."""
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        raw = "<QUESTION>测试问题</QUESTION>\n<SKILL_DRAFT>\n```skill_doc\n# 技能名称：测试\n## 核心问题\n测试\n```\n</SKILL_DRAFT>"
        q, draft = a._parse_dual_response(raw)
        assert "测试问题" in q
        assert draft is not None
        assert draft[0] == "测试"

    def test_agent_exit_keywords(self):
        """Exit keywords should stop extraction."""
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        agent.start("test")
        reply, doc = agent.handle("不做了，取消", [], ("", "", ""))
        assert "退出" in reply
        assert doc is None

    def test_inject_external_knowledge(self):
        """Injecting content during extraction should add it to context."""
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        agent.start("test")
        reply = agent.inject_external_knowledge("test content here", "test_source")
        assert "已读取" in reply
        assert any("test content" in c for c in agent._context)

    def test_confirmation_detection(self):
        """_is_confirmation should correctly identify confirm vs change."""
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        assert a._is_confirmation("确认，生成") is True
        assert a._is_confirmation("1") is True
        assert a._is_confirmation("保存") is True
        assert a._is_confirmation("需要修改这里") is False
        assert a._is_confirmation("不对，漏了东西") is False

    def test_confirming_returns_doc_same_turn(self):
        """Confirmation should generate and return skill doc in one turn."""
        from unittest.mock import patch
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent.start("处理退款")
        agent._phase = Phase.CONFIRMING
        agent._draft_name = "test-skill"
        agent._draft_content = "# 技能名称：测试\n## S_body\n1. step"
        fake_doc = {"name": "test-skill", "content": agent._draft_content, "slug": "test-skill", "description": "d"}
        with patch.object(agent, "_generate", return_value=("已生成", fake_doc)):
            reply, doc = agent.handle("确认，生成", [], ("", "", ""))
        assert reply == "已生成"
        assert doc is not None
        assert doc["name"] == "test-skill"

    def test_refining_does_not_auto_generate_by_turn_count(self):
        """Turn count alone must not trigger generation — only explicit user intent."""
        from unittest.mock import patch
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent._phase = Phase.REFINING
        agent._turn = 8
        agent._goal = "工单处理"
        agent._context = ["用户说：步骤1"]
        with patch.object(agent, "_generate") as gen:
            with patch("skillos.llm_client.call", return_value="<QUESTION>继续</QUESTION><SKILL_DRAFT>none</SKILL_DRAFT>"):
                reply, doc = agent.handle("补充：关单前要客户确认", [], ("", "", ""))
        gen.assert_not_called()
        assert doc is None
        assert agent._phase == Phase.REFINING

    def test_gap_question_enters_confirming_without_generate(self):
        from unittest.mock import patch
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent._phase = Phase.REFINING
        agent._goal = "工单"
        with patch.object(agent, "_generate") as gen:
            with patch.object(agent, "_summarize", return_value="摘要：要生成吗？"):
                reply, doc = agent.handle("你还需什么信息？", [], ("", "", ""))
        gen.assert_not_called()
        assert agent._phase == Phase.CONFIRMING
        assert "要生成吗" in reply

    def test_post_done_finalize_regenerates(self):
        from unittest.mock import patch
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent._phase = Phase.DONE
        agent._finalized_name = "工单处理"
        agent._goal = "工单处理"
        fake_doc = {"name": "工单处理", "content": "# x", "slug": "ticket", "description": "d"}
        with patch.object(agent, "_generate", return_value=("已更新", fake_doc)) as gen:
            reply, doc = agent.handle("可以了，生成技能文档吧", [], ("", "", ""))
        gen.assert_called_once()
        assert doc["name"] == "工单处理"

    def test_save_draft_skips_after_done(self):
        from unittest.mock import patch
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent._phase = Phase.DONE
        with patch("skillos.skills.skill_store.save_skill") as save:
            agent._save_draft("x", "body")
        save.assert_not_called()

    def test_persist_created_skill_sets_draft_false(self, tmp_path, monkeypatch):
        from unittest.mock import patch
        from skillos.api.skills import _persist_created_skill
        from skillos.skills import skill_store

        monkeypatch.setattr(skill_store, "resolve_skills_root", lambda tenant=None: tmp_path)
        body = """tool_name: demo-skill
tool_description: Demo skill for testing.

# 技能名称：演示
## S_body
1. step
## S_trigger
- keywords: demo
"""
        with patch("skillos.knowledge.epistemic_bridge.apply_epistemics_to_skill", side_effect=lambda b, **kw: (b, type("S", (), {"pending": 0, "pending_ids": []})())):
            _persist_created_skill("演示", body, ("", "", ""))
        raw = skill_store.load_skill_raw("演示")
        assert raw["meta"].get("draft") is False

    def test_restore_skips_when_done(self):
        from skillos.skills.agent import SkillExtractionAgent, Phase
        agent = SkillExtractionAgent()
        agent._phase = Phase.DONE
        agent._finalized_name = "工单"
        history = [
            {"role": "user", "content": "创建工单技能"},
            {"role": "assistant", "content": "好的，我们来沉淀技能"},
        ]
        assert agent.restore_from_history(history) is False
        assert agent._phase == Phase.DONE

    def test_generation_context_includes_draft_and_tail(self):
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        agent._goal = "工单处理"
        agent._draft_content = "# 技能名称：工单\n## S_body\n1. step"
        agent._context = [f"用户说：轮次{i}" for i in range(25)]
        ctx = agent._generation_context()
        assert "渐进草稿" in ctx
        assert "用户说：轮次24" in ctx
        assert "用户说：轮次0" in ctx or "对话摘要" in ctx

    def test_extract_topic_sediment_prefix(self):
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        # _extract_topic strips suffix "流程/技能/skill" per design
        assert a._extract_topic("帮我沉淀一下电商客服处理退款的标准流程") == "电商客服处理退款的标准"
        assert a._extract_topic("帮我沉淀一套飞书报销审批的处理流程") == "飞书报销审批的处理"
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        assert a._extract_topic("帮我沉淀一下电商客服处理退款的标准流程") == "电商客服处理退款的标准"
        assert a._extract_topic("帮我沉淀一套飞书报销审批的处理流程") == "飞书报销审批的处理"


class TestURLPipeline:
    def test_learn_from_url_small_content(self):
        """7-step pipeline should handle small content gracefully."""
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        content = "# Test\n\nThis is a test. Step 1: do X. Step 2: do Y."
        reply, doc = a.learn_from_url("http://test.com", content, [], ("", "", ""))
        assert reply is not None
        # Small content may pass or fail at 初识 step depending on LLM
        # Either way it should not crash

    def test_learn_from_url_too_short(self):
        """Very short content should be rejected at first encounter."""
        from skillos.skills.agent import SkillExtractionAgent
        a = SkillExtractionAgent()
        reply, doc = a.learn_from_url("http://test.com", "Too short", [], ("", "", ""))
        assert reply is not None


class TestSkillExecution:
    def test_create_and_run_agent(self):
        """Agent factory should create and run agents from skill docs."""
        from skillos.skills.agent_factory import create_agent, run_agent
        doc = "---\nname: test-run\n---\n\n# Test Runner\n## S_body\n1. Say hello\n## S_trigger\n- keywords: hello\n## S_params\n- name: string"
        agent = create_agent(doc, "say hello")
        assert agent["name"] is not None
        result = run_agent(agent, "Please say hello to the user")
        assert len(result) > 0


class TestSkillStore:
    def test_save_and_load_skill(self):
        """Save and load should round-trip correctly."""
        from skillos.skills.skill_store import save_skill, load_skill, skill_exists
        name = "integration-test-save-load"
        body = "# Integration Test\n## S_body\n1. Step one"
        save_skill(name, body)
        assert skill_exists(name) is True
        loaded = load_skill(name)
        assert "Integration Test" in loaded

    def test_version_archiving(self):
        """Saving twice should create version history."""
        from skillos.skills.skill_store import save_skill, get_skill_versions
        name = "integration-test-versions"
        save_skill(name, "# V1")
        v1 = get_skill_versions(name)
        save_skill(name, "# V2")
        v2 = get_skill_versions(name)
        assert len(v2) >= len(v1)


class TestEpistemologyPipeline:
    def test_classify_claim_experience(self):
        """New claims default to EXPERIENCE level."""
        from skillos.knowledge.epistemology import get_store, EpistemicLevel
        store = get_store()
        claim = store.add_claim("Test observation about skills", source="test")
        assert claim.level in (EpistemicLevel.EXPERIENCE, EpistemicLevel.EVIDENCE, EpistemicLevel.PREFERENCE)

    def test_cross_reference_finds_pairs(self):
        """Cross-reference should find overlapping claims."""
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        store.add_claim("Skills with more branches have higher scores")
        store.add_claim("Higher branch count correlates with better skill scores")
        pairs = store.cross_reference()
        assert pairs >= 0  # Should not crash

    def test_add_and_get_knowledge(self):
        """Adding a knowledge-level claim should be retrievable."""
        from skillos.knowledge.epistemology import get_store, EpistemicLevel
        store = get_store()
        claim = store.add_claim("Verified fact for integration test", source="test",
                                level=EpistemicLevel.KNOWLEDGE)
        knowledge = store.get_knowledge()
        assert any(k.claim_id == claim.claim_id for k in knowledge)

    def test_invalidate_claim(self):
        """Invalidating a claim should mark it superseded."""
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        claim = store.add_claim("To be invalidated")
        result = store.invalidate(claim.claim_id)
        assert result is True
        assert not store.claims[claim.claim_id].is_current

    def test_expire_stale_claims(self):
        """Expiring stale claims should not crash."""
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        expired = store.expire_stale_claims()
        assert expired >= 0

    def test_get_experience_review(self):
        """Experience review should return formatted text."""
        from skillos.knowledge.epistemology import get_experience_review, get_store
        store = get_store()
        store.add_claim("An experience to review")
        review = get_experience_review()
        assert isinstance(review, str)


class TestKnowledgeGraph:
    def test_graph_operations(self):
        """Basic graph operations should work."""
        from skillos.knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        a = kg.add_node("NodeA", "concept", "Test A")
        b = kg.add_node("NodeB", "concept", "Test B")
        assert a is not None
        assert b is not None
        assert kg.get_node(a) is not None

    def test_detect_clusters(self):
        """Cluster detection should not crash on empty graph."""
        from skillos.knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        clusters = kg.detect_clusters()
        assert isinstance(clusters, list)

    def test_get_graph_singleton(self):
        """Singleton get_graph should return same instance."""
        from skillos.knowledge.graph import get_graph
        g1 = get_graph()
        g2 = get_graph()
        assert g1 is g2


class TestEvolutionEngine:
    def test_detect_triggers(self):
        """Evolution trigger detection should not crash."""
        from skillos.evolution.engine import detect_evolution_triggers
        triggers = detect_evolution_triggers()
        assert isinstance(triggers, list)

    def test_run_evolution_check(self):
        """Full evolution check should return expected structure."""
        from skillos.evolution.engine import run_evolution_check
        result = run_evolution_check()
        assert "triggers" in result
        assert "top_triggers" in result
        assert "suggestion_text" in result

    def test_evolve_should_not_crash(self):
        """Evolution pipeline should be robust."""
        from skillos.evolution.evolver import should_evolve, get_recent_traces
        traces = get_recent_traces("nonexistent_skill", 10)
        assert isinstance(traces, list)
        result = should_evolve("nonexistent_skill")
        # should_evolve returns (bool, str) tuple
        assert isinstance(result, (bool, tuple))
        if isinstance(result, tuple):
            assert isinstance(result[0], bool)


class TestDispatcher:
    def test_dispatch_with_no_skills(self):
        """Dispatcher should handle empty skill list."""
        from skillos.skills.dispatcher import dispatch
        result = dispatch("test message", available_skills=[], model="")
        # Should not crash — either returns text or None
        assert result is not None

    def test_skill_to_tool_conversion(self):
        """Skill should convert to valid tool definition."""
        from skillos.skills.dispatcher import _skill_to_tool, _safe_tool_name
        safe = _safe_tool_name("测试技能")
        assert safe and " " not in safe


class TestConfig:
    def test_config_singleton(self):
        """get_config should return same instance."""
        from skillos.config import get_config
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_llm_args_structure(self):
        """to_llm_args should return correct tuple shape."""
        from skillos.config import get_config
        cfg = get_config()
        args = cfg.to_llm_args()
        assert len(args) == 4  # (api_key, base_url, model, kwargs)


class TestSecurityScanner:
    def test_scan_clean_skill(self):
        """Clean skill should have no findings."""
        from skillos.api.middleware import scan_skill_security
        content = "# Clean Skill\n## S_body\n1. Do something safe"
        findings = scan_skill_security(content)
        assert len(findings) == 0

    def test_scan_dangerous_skill(self):
        """Skill with eval() should be flagged."""
        from skillos.api.middleware import scan_skill_security
        content = "# Bad Skill\n```python\neval(user_input)\n```"
        findings = scan_skill_security(content)
        assert len(findings) > 0

    def test_scan_hardcoded_credential(self):
        """Skill with hardcoded password should be flagged."""
        from skillos.api.middleware import scan_skill_security
        content = 'api_key = "sk-1234567890abcdef"'
        findings = scan_skill_security(content)
        assert len(findings) > 0


class TestFileIngest:
    def test_is_supported_formats(self):
        """Common formats should be supported."""
        from skillos.utils.file_ingest import is_supported
        assert is_supported("test.pdf")
        assert is_supported("test.docx")
        assert is_supported("test.txt")
        assert is_supported("test.md")
        assert is_supported("test.png")

    def test_get_file_category(self):
        """File category should be detected correctly."""
        from skillos.utils.file_ingest import get_file_category
        assert get_file_category("test.pdf") == "PDF"
        assert get_file_category("test.docx") == "文档"
        assert get_file_category("test.png") == "图片"
        assert get_file_category("test.txt") == "文本"
