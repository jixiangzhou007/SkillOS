"""Tests for skills engine modules."""

import pytest


class TestSkillAgent:
    def test_agent_creation(self):
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        assert agent._phase.name == 'IDLE'
        assert agent.is_active is False

    def test_agent_start(self):
        from skillos.skills.agent import SkillExtractionAgent
        agent = SkillExtractionAgent()
        reply = agent.start("test workflow")
        assert "test" in reply.lower() or "workflow" in reply.lower()


class TestAgentFactory:
    def test_create_agent(self):
        doc = "---\nname: test-agent\n---\n\n# Test\n## S_body\n1. Say hello"
        from skillos.skills.skill_store import save_skill
        save_skill("test-agent-factory", doc)
        from skillos.skills.agent_factory import create_agent
        agent = create_agent(doc, "hello")
        assert agent["name"] == "Test"


class TestSessionManager:
    def test_create_session(self):
        from skillos.skills.session_manager import SessionManager
        mgr = SessionManager(ttl=60)
        session = mgr.get_or_create("", "create", "deepseek-v4-flash")
        assert session.id
        assert session.mode == "create"

    def test_session_expiry(self):
        from skillos.skills.session_manager import SessionManager
        mgr = SessionManager(ttl=1)
        session = mgr.get_or_create("test-expire", "agent")
        import time; time.sleep(1.1)
        result = mgr.get("test-expire")
        assert result is None  # Expired


class TestDispatcher:
    def test_constants_defined(self):
        from skillos.skills.dispatcher import DISPATCHER_SYSTEM
        assert "skill" in DISPATCHER_SYSTEM.lower()


class TestMetaSkill:
    def test_parse_metaskill(self):
        from skillos.skills.metaskill import parse_metaskill
        doc = "---\ntype: metaskill\nname: test-pipeline\n---\n\n# Test\n## Goal\nTest pipeline\n## Pipeline\n```pipeline\nstep1: skill-a\nstep2: skill-b  # depends_on: [step1]\n```"
        ms = parse_metaskill(doc)
        assert ms is not None


class TestToolRegistry:
    def test_register_tool(self):
        from skillos.skills.tool_registry import Tool, ToolRegistry
        reg = ToolRegistry()
        t = Tool(name="test-tool", description="A test tool", tool_type="builtin")
        assert t.name == "test-tool"


class TestConversationStore:
    def test_save_and_load(self):
        from skillos.skills.conversation_store import save_message, load_history, delete_session_history
        sid = "test-session-123"
        save_message(sid, "user", "Hello")
        save_message(sid, "assistant", "Hi there")
        history = load_history(sid)
        assert len(history) >= 2
        delete_session_history(sid)


class TestPatternMiner:
    def test_profile_skills(self):
        from skillos.skills.pattern_miner import profile_all_skills
        profiles = profile_all_skills()
        assert isinstance(profiles, list)


class TestVariants:
    def test_register_variant(self):
        from skillos.skills.variants import VariantRegistry
        reg = VariantRegistry()
        v = reg.register_variant("test-archetype", "test-creator", "test content")
        assert v.archetype == "test-archetype"
        variants = reg.get_variants("test-archetype")
        assert len(variants) >= 1
