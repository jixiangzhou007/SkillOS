"""Tests for DNA lineage persistence (Phase 2)."""


from skillos.knowledge.dna_context import build_dna_lineage, build_skill_dna_meta
from skillos.knowledge.dna_store import (
    get_philosophical_stability,
    get_template_version,
    load_philosophical_stats,
    parse_lineage_from_meta,
    record_dna_contribution,
)


class TestBuildDnaLineage:
    def test_refund_skill_lineage(self):
        lineage = build_dna_lineage(
            "电商客服退款处理",
            "退款流程 工单 客服 审批 退货 SLA",
        )
        assert lineage["philosophical"]
        assert lineage["domain"]
        assert lineage["philosophical"][0]["id"] == "pdca"
        assert lineage["philosophical"][0]["weight"] >= 0.4
        assert lineage["domain"][0]["primary"] is True
        assert lineage["domain"][0]["version"] >= "1.0.0"
        assert "detected_at" in lineage

    def test_explicit_domain_template(self):
        lineage = build_dna_lineage(
            "PR审查",
            "github pull request",
            domain_template_id="code-review-pr",
        )
        assert lineage["domain"][0]["id"] == "code-review-pr"

    def test_skill_dna_meta_nested(self):
        meta = build_skill_dna_meta("采购审批流程", "审批 核对 归档")
        assert "dna_lineage" in meta


class TestDnaStore:
    def test_record_and_reload_stability(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skillos.knowledge.dna_store.PHILOSOPHICAL_STATS_PATH",
            tmp_path / "philosophical_stats.json",
        )
        monkeypatch.setattr(
            "skillos.knowledge.dna_store.DOMAIN_TEMPLATES_DIR",
            tmp_path / "domain_templates",
        )
        lineage = {
            "philosophical": [{"id": "pdca", "weight": 0.7}],
            "domain": [{"id": "workflow-refund", "version": "1.0.0", "weight": 1.0, "primary": True}],
        }
        record_dna_contribution("test-skill", lineage, moe_score=75)
        assert get_philosophical_stability("pdca") > 0.75
        stats = load_philosophical_stats()
        assert stats["methods"]["pdca"]["derived_from_skills"] == 1
        assert get_template_version("workflow-refund") == "1.0.0"

    def test_parse_lineage_from_meta(self):
        meta = {"dna_lineage": {"philosophical": [{"id": "ooda", "weight": 1.0}]}}
        assert parse_lineage_from_meta(meta)["philosophical"][0]["id"] == "ooda"


class TestBackfillScript:
    def test_backfill_writes_lineage(self, tmp_path):
        from skillos.knowledge.dna_store import backfill_skill_lineage

        md = tmp_path / "退款" / "SKILL.md"
        md.parent.mkdir()
        md.write_text(
            "---\nname: 退款处理\ndraft: false\n---\n# 退款 工单\n",
            encoding="utf-8",
        )
        row = backfill_skill_lineage(md)
        assert row["changed"] is True
        text = md.read_text(encoding="utf-8")
        assert "dna_lineage:" in text
        assert "philosophical:" in text
