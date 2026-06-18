"""Phase 5 — team context: playbook bindings, lineage, variants."""

from skillos.knowledge.playbook import (
    bind_chat_playbook,
    get_playbook_context,
    load_playbook_for_chat,
)
from skillos.knowledge.lineage import (
    record_skill_precipitation,
    query_skill_precipitations,
    format_skill_lineage,
)
from skillos.skills.variants import find_archetype_for_skill, register_precipitation_variant


class TestPlaybookBindings:
    def test_two_chats_different_playbooks(self, tmp_path, monkeypatch):
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        (pb_dir / "team-a.md").write_text("## 风格偏好\n用语正式，称呼用户用「您」", encoding="utf-8")
        (pb_dir / "team-b.md").write_text("## 风格偏好\n用语轻松，称呼用「你」", encoding="utf-8")

        bindings = tmp_path / "bindings.json"
        monkeypatch.setattr("skillos.knowledge.playbook.PLAYBOOKS_DIR", pb_dir)
        monkeypatch.setattr("skillos.knowledge.playbook.BINDINGS_PATH", bindings)

        bind_chat_playbook("oc_team_a", "team-a.md", label="A")
        bind_chat_playbook("oc_team_b", "team-b.md", label="B")

        ctx_a = get_playbook_context(chat_id="oc_team_a")
        ctx_b = get_playbook_context(chat_id="oc_team_b")
        assert "您" in ctx_a
        assert "你" in ctx_b
        assert "您" not in ctx_b

    def test_session_id_resolves_chat(self, tmp_path, monkeypatch):
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        (pb_dir / "feishu.md").write_text("## 风格偏好\n飞书群专用术语：工单", encoding="utf-8")
        monkeypatch.setattr("skillos.knowledge.playbook.PLAYBOOKS_DIR", pb_dir)
        monkeypatch.setattr(
            "skillos.knowledge.playbook.BINDINGS_PATH",
            tmp_path / "bindings.json",
        )
        bind_chat_playbook("oc_feishu_1", "feishu.md")

        content = load_playbook_for_chat(session_id="feishu:oc_feishu_1:ou_user")
        assert "飞书群专用" in content


class TestSkillLineage:
    def test_record_and_query(self, tmp_path, monkeypatch):
        events_path = tmp_path / "events.jsonl"
        monkeypatch.setattr("skillos.knowledge.lineage.SKILL_EVENTS_PATH", events_path)

        record_skill_precipitation(
            "退款流程",
            session_id="feishu:oc_1:ou_alice",
            channel="feishu",
            chat_id="oc_1",
            user_id="ou_alice",
            source="dispatch",
        )
        rows = query_skill_precipitations(skill_name="退款流程")
        assert len(rows) == 1
        assert rows[0]["user_id"] == "ou_alice"
        assert rows[0]["chat_id"] == "oc_1"
        assert "feishu" in rows[0]["session_id"]

        text = format_skill_lineage("退款流程")
        assert "ou_alice" in text
        assert "oc_1" in text


class TestVariantRegistration:
    def test_register_variant_when_similar_exists(self, tmp_path, monkeypatch):
        from skillos.skills import skill_store

        skills_dir = tmp_path / "skills"
        monkeypatch.setenv("SKILLOS_SKILLS_DIR", str(skills_dir))

        body_a = "# Skill Name: 代码审查\n## S_body\n1. 阅读 PR 描述理解变更背景"
        body_b = "# Skill Name: 代码审查-严格版\n## S_body\n1. 必须先运行 CI 再审查"
        skill_store.save_skill("代码审查", body_a, epistemic=False)
        skill_store.save_skill("代码审查-严格版", body_b, epistemic=False)

        archetype = find_archetype_for_skill("代码审查-严格版")
        assert archetype == "代码审查"

        variants_path = tmp_path / "variants.json"
        monkeypatch.setattr("skillos.skills.variants.VARIANTS_PATH", variants_path)

        hint = register_precipitation_variant(
            "代码审查-严格版",
            body_b,
            creator="ou_bob",
            source="test",
        )
        assert "变体" in hint or hint == ""


class TestAgentTeamContext:
    def test_agent_uses_bound_playbook(self, tmp_path, monkeypatch):
        pb_dir = tmp_path / "playbooks"
        pb_dir.mkdir()
        (pb_dir / "ctx.md").write_text("## 风格偏好\nAgent注入测试：专用Playbook", encoding="utf-8")
        monkeypatch.setattr("skillos.knowledge.playbook.PLAYBOOKS_DIR", pb_dir)
        monkeypatch.setattr(
            "skillos.knowledge.playbook.BINDINGS_PATH",
            tmp_path / "bindings.json",
        )
        bind_chat_playbook("oc_agent", "ctx.md")

        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent.set_team_context(chat_id="oc_agent", session_id="feishu:oc_agent:ou_x")
        ctx = agent._playbook_ctx()
        assert "专用Playbook" in ctx
