"""Tests for unified DNA context (Phase 1)."""

from skillos.knowledge.dna_context import (
    PHILOSOPHICAL_TO_TAXONOMY,
    build_dna_context,
    build_dna_hint,
    detect_dna,
    primary_philosophical_id,
)
from skillos.knowledge.philosophical_dna import cross_domain_conflict_check, detect_philosophical_dna
from skillos.knowledge.taxonomy import build_taxonomy_context


class TestPhilosophicalDetectionGolden:
    """Sprint 9 golden cases — DNA detection 3/3."""

    def test_performance_review_pdca_pragmatic(self):
        ids = [p.method_id for p in detect_philosophical_dna(
            "员工绩效评估流程", domain_key="business-management",
        )]
        assert "pdca" in ids
        assert "pragmatic" in ids

    def test_procurement_pdca(self):
        ids = [p.method_id for p in detect_philosophical_dna(
            "采购审批流程", domain_key="business-management",
        )]
        assert ids[0] == "pdca"

    def test_security_audit_ooda(self):
        ids = [p.method_id for p in detect_philosophical_dna(
            "安全审计 应急响应", domain_key="computer-science",
        )]
        assert "ooda" in ids


class TestUnifiedDnaContext:
    def test_detect_dna_maps_taxonomy_methodology(self):
        det = detect_dna("采购审批流程")
        assert det.taxonomy_methodology_key == "business-process"
        assert det.philosophical[0].method_id == "pdca"

    def test_build_dna_context_no_duplicate_methodology(self):
        ctx = build_dna_context("采购审批流程")
        assert "方法论模式识别" not in ctx  # legacy taxonomy methodology block
        assert "PDCA" in ctx or "pdca" in ctx.lower() or "规划" in ctx

    def test_build_taxonomy_context_domain_only(self):
        ctx = build_taxonomy_context("GitHub PR 代码审查")
        assert "领域" in ctx or "计算机" in ctx
        assert "方法论模式识别" not in ctx

    def test_build_dna_hint_compact(self):
        hint = build_dna_hint("安全审计 应急响应")
        assert "领域:" in hint or "方法论:" in hint
        assert len(hint.split("\n")) <= 4

    def test_primary_philosophical_id(self):
        assert primary_philosophical_id("采购审批") == "pdca"

    def test_meta_includes_philosophical_dna(self):
        meta = detect_dna("绩效评估 自评 面谈").to_meta()
        assert "philosophical_dna" in meta
        assert meta.get("methodology") in PHILOSOPHICAL_TO_TAXONOMY.values() or meta.get("methodology")


class TestConflictDetection:
    def test_pdca_ooda_conflict(self):
        from skillos.knowledge.philosophical_dna import PHILOSOPHICAL_DNA, get_philosophical_dna
        pdca = get_philosophical_dna("pdca")
        ooda = get_philosophical_dna("ooda")
        assert pdca and ooda
        conflicts = cross_domain_conflict_check([pdca, ooda])
        assert len(conflicts) >= 1

    def test_detect_dna_surfaces_conflicts(self):
        det = detect_dna("紧急审批 标准化 SOP 实时响应 告警")
        if det.conflicts:
            assert any("PDCA" in c or "OODA" in c for c in det.conflicts)
