"""Tests for domain skill templates (P2)."""

from skillos.skills.domain_templates import (
    DOMAIN_TEMPLATES,
    get_generation_boost,
    list_domain_templates,
    match_domain_template,
    resolve_domain_competition,
)


class TestDomainTemplates:
    def test_list_three_templates(self):
        items = list_domain_templates()
        assert len(items) >= 8
        ids = {i["template_id"] for i in items}
        assert "workflow-refund" in ids
        assert "code-review-pr" in ids
        assert "data-csv-clean" in ids
        assert "security-audit" in ids

    def test_security_audit_template_match(self):
        comp = resolve_domain_competition("安全审计 应急响应 合规检查")
        assert comp.primary is not None
        assert comp.primary.template_id == "security-audit"

    def test_match_refund(self):
        t = match_domain_template("我想做电商客服退款处理流程")
        assert t is not None
        assert t.template_id == "workflow-refund"

    def test_match_pr(self):
        t = match_domain_template("GitHub pull request code review")
        assert t is not None
        assert t.template_id == "code-review-pr"

    def test_match_csv(self):
        t = match_domain_template("运营 CSV 数据清洗 去重")
        assert t is not None
        assert t.template_id == "data-csv-clean"

    def test_no_match_short(self):
        assert match_domain_template("hi") is None

    def test_generation_boost_has_sections(self):
        boost = get_generation_boost("workflow-refund")
        assert "S_trigger" in boost
        assert "S_route" in boost

    def test_bench_categories_aligned(self):
        for tmpl in DOMAIN_TEMPLATES:
            assert len(tmpl.bench_categories) >= 1


class TestAgentTemplateHook:
    def test_start_sets_template_id(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        reply = agent.start("我想创建电商客服退款处理技能")
        assert agent._domain_template_id == "workflow-refund"
        assert "退款" in reply or "模板" in reply
