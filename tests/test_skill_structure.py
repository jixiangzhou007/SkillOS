"""Tests for skill_structure (P0: S_body normalization + heritage merge)."""

from __future__ import annotations

from pathlib import Path

from skillos.skills.pattern_miner import check_dna_compliance
from skillos.skills.skill_structure import (
    apply_structure_pipeline,
    extract_executable_body,
    merge_protected_sections,
    normalize_skill_body,
    sanitize_skill_body,
)

V3_REFUND = Path(__file__).resolve().parent.parent / "skills" / "电商客服退款处理" / "v3.md"


def _body_from_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    return raw.split("---", 2)[-1].strip() if raw.startswith("---") else raw


class TestExtractExecutableBody:
    def test_instructions_counts_as_body(self):
        body = "## Instructions\n1. Do step one with 操作执行检查验证\n2. Second step with 读取写入\n"
        assert "Do step one" in extract_executable_body(body)

    def test_s_body_preferred(self):
        body = "## S_body\n1. Alpha step with 操作执行\n## Instructions\nignored\n"
        assert "Alpha" in extract_executable_body(body)


class TestNormalizeSkillBody:
    def test_renames_instructions_to_s_body(self):
        raw = "# Title\n\n## Instructions\n1. First actionable step with 操作执行检查\n"
        out = normalize_skill_body(raw)
        assert "## S_body" in out
        assert "## Instructions" not in out

    def test_renames_decision_routes_to_s_route(self):
        raw = "# T\n\n## Decision routes\n| a | b |\n|---|---|\n| x | y |\n"
        out = normalize_skill_body(raw)
        assert "## S_route" in out


class TestHeritageMerge:
    def test_merge_应答速查_from_v3(self):
        if not V3_REFUND.is_file():
            return
        old = _body_from_file(V3_REFUND)
        new = "# Refund\n\n## When to use\n- keywords: refund\n- context: 客户在工单发起退款时\n\n## S_body\n1. 核实订单并执行退款操作检查验证\n"
        merged, names = merge_protected_sections(
            old, new, domain_template="workflow-refund",
        )
        assert any("应答速查" in n for n in names)
        assert "应答速查" in merged
        assert "禁止" in merged and "已为您发起退款" in merged


class TestComplianceAfterNormalize:
    def test_instructions_only_skill_passes_body_principle(self):
        """P0: Instructions must count as executable body (was: S_body 章节缺失)."""
        body = (
            "# Refund\n\n## When to use\n- keywords: refund\n"
            "- context: 客户在飞书或工单发起退款请求时使用\n\n"
            "## Instructions\n"
            "1. 查询订单状态并核实身份，执行退款操作检查验证\n"
            "2. 若金额超过500元则转人工复核，否则调用支付网关原路退回\n"
            "3. 同步 ERP 并发送短信通知客户退款结果\n"
        )
        report = check_dna_compliance(body)
        p3 = next(c for c in report["checks"] if c["principle"] == 3)
        assert p3["passed"] is True
        assert report["passed"] >= 4

    def test_v3_has_executable_body_after_normalize(self):
        if not V3_REFUND.is_file():
            return
        body = normalize_skill_body(_body_from_file(V3_REFUND))
        report = check_dna_compliance(body)
        p3 = next(c for c in report["checks"] if c["principle"] == 3)
        assert "章节缺失" not in p3.get("detail", "")
        assert "## S_body" in body


class TestDomainHeritageTemplates:
    def test_pr_template_inserted_when_missing(self):
        from skillos.skills.skill_structure import apply_domain_heritage_templates

        body = "# PR\n\n## S_trigger\n- keywords: pr\n- context: 审查 PR 时\n\n## S_body\n1. 检查 diff\n"
        out, merged = apply_domain_heritage_templates(body, domain_template="code-review-pr")
        assert "审查应答速查" in out
        assert merged


class TestSanitizeSkillBody:
    def test_strips_junk_inputs_and_inserts_s_params(self):
        body = (
            "# Refund\n\n## S_trigger\n- context: 退款时\n\n## S_body\n"
            "1. 核实订单并执行退款操作检查验证\n"
            "2. 计算金额并标记风险转人工\n"
            "3. 发起退款并同步 ERP 通知客户\n\n"
            "## Inputs\n#### 参数抽象度评委\njunk\n\n## 认识论状态\n> ok\n"
        )
        out, actions = sanitize_skill_body(body, domain_template="workflow-refund")
        assert "参数抽象度评委" not in out
        assert "## S_params" in out
        assert "order_id" in out
        assert any("removed" in a for a in actions)
