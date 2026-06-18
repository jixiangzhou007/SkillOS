"""Phase 3 — multi-domain template competition and keyword governance."""

from __future__ import annotations

from skillos.knowledge.dna_context import build_dna_lineage, build_domain_template_context
from skillos.skills.domain_templates import (
    cross_template_conflict_check,
    get_template,
    match_domain_template,
    resolve_domain_competition,
    score_domain_templates,
)


class TestKeywordGovernance:
    def test_security_audit_not_finance(self):
        comp = resolve_domain_competition("安全审计 应急响应 合规检查")
        assert comp.primary is not None
        assert comp.primary.template_id == "security-audit"
        assert not any(
            s.template.template_id == "finance-expense-audit" for s in comp.secondary
        )

    def test_finance_still_matches_expense(self):
        comp = resolve_domain_competition("员工报销 发票 差旅费用 财务审计")
        assert comp.primary is not None
        assert comp.primary.template_id == "finance-expense-audit"

    def test_refund_not_law_contract(self):
        comp = resolve_domain_competition("电商客服退款处理 退款流程 工单 客服")
        assert comp.primary is not None
        assert comp.primary.template_id == "workflow-refund"
        assert not any(
            s.template.template_id == "law-contract-review" for s in comp.secondary
        )


class TestDomainCompetition:
    def test_security_audit_scores(self):
        scored = score_domain_templates("安全审计 渗透测试 漏洞")
        assert scored
        assert scored[0].template.template_id == "security-audit"
        assert scored[0].score >= 2

    def test_cross_template_conflict_finance_security(self):
        finance = get_template("finance-expense-audit")
        security = get_template("security-audit")
        assert finance and security
        conflicts = cross_template_conflict_check([finance, security])
        assert len(conflicts) >= 1

    def test_lineage_uses_competition_weights(self):
        lineage = build_dna_lineage("安全审计 应急响应", "渗透测试 漏洞 合规检查")
        assert lineage["domain"]
        assert lineage["domain"][0]["id"] == "security-audit"
        assert lineage["domain"][0]["primary"] is True

    def test_domain_template_context_includes_primary(self):
        ctx = build_domain_template_context("安全审计 应急响应")
        assert "security-audit" in ctx or "安全审计" in ctx


class TestAgentMultiTemplate:
    def test_start_security_audit_template(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        reply = agent.start("帮我沉淀安全审计流程 应急响应")
        assert agent._domain_template_id == "security-audit"
        assert "security-audit" in agent._domain_template_ids
        assert "安全审计" in reply or "模板" in reply

    def test_start_refund_single_primary(self):
        from skillos.skills.agent import SkillExtractionAgent

        agent = SkillExtractionAgent()
        agent.start("我想创建电商客服退款处理技能")
        assert agent._domain_template_id == "workflow-refund"
        assert agent._domain_template_ids[0] == "workflow-refund"
