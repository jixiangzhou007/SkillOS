"""Tests for epistemic_bridge — skill document ↔ epistemology engine."""

import pytest

SAMPLE_SKILL = """# 技能名称：测试审查

## S_body
1. 阅读 PR 描述和关联 Issue，理解变更背景与目标
2. 检查主流程逻辑是否正确，包含边界条件与异常处理
3. 验证测试覆盖核心路径、边界条件和错误分支

## S_route
| 用户意图 | 执行动作 |
| 开始审查 PR | 执行完整审查流程 |
| 只查逻辑 | 执行步骤 1-2 |

## S_trigger
- keywords: code review, 代码审查
- context: 收到他人提交的 PR 需要审查时
"""


class TestExtractClaims:
    def test_extract_claims_from_skill_body(self):
        from skillos.knowledge.epistemic_bridge import extract_claims_from_skill
        pairs = extract_claims_from_skill(SAMPLE_SKILL)
        assert len(pairs) >= 4
        sections = {s for s, _ in pairs}
        assert "s_body" in sections or any("body" in s for s in sections)

    def test_skips_short_lines(self):
        from skillos.knowledge.epistemic_bridge import extract_claims_from_skill
        body = "## S_body\n1. 短\n2. 这条规则足够长，应该被提取为一条可执行的审查步骤说明"
        pairs = extract_claims_from_skill(body)
        assert len(pairs) == 1


class TestApplyEpistemics:
    def test_apply_without_llm(self):
        from skillos.knowledge.epistemic_bridge import apply_epistemics_to_skill
        body, summary = apply_epistemics_to_skill(
            SAMPLE_SKILL,
            skill_name="epistemic-bridge-test",
            source="test://unit",
            source_type="test_result",
            llm_args=None,
            run_falsify=False,
        )
        assert summary.total >= 4
        assert summary.pending + summary.verified >= summary.total
        assert "## 认识论状态" in body

    def test_save_skill_writes_epistemic_meta(self):
        from skillos.skills.skill_store import save_skill, load_skill_raw, delete_skill
        name = "epistemic-bridge-save-test"
        try:
            save_skill(
                name, SAMPLE_SKILL,
                source="test://save",
                source_type="test_result",
                llm_args=None,
            )
            raw = load_skill_raw(name)
            ep = raw["meta"].get("epistemic", {})
            assert ep.get("total_claims", 0) >= 4
            assert "认识论状态" in raw["body"]
        finally:
            delete_skill(name)

    def test_draft_skips_epistemic(self):
        from skillos.skills.skill_store import save_skill, load_skill_raw, delete_skill
        name = "epistemic-draft-skip-test"
        try:
            save_skill(name, SAMPLE_SKILL, meta={"draft": True})
            raw = load_skill_raw(name)
            assert "epistemic" not in raw["meta"]
            assert "## 认识论状态" not in raw["body"]
        finally:
            delete_skill(name)


class TestConfirmClaims:
    def test_confirm_promotes_experience(self):
        from skillos.knowledge.epistemic_bridge import confirm_claims
        from skillos.knowledge.epistemology import get_store, EpistemicLevel

        store = get_store()
        claim = store.add_claim(
            "用户确认的规则：退款必须先验证订单状态",
            source="test", source_type="user_feedback",
            level=EpistemicLevel.EXPERIENCE,
            skill_name="confirm-test",
        )
        n = confirm_claims([claim.claim_id])
        assert n == 1
        refreshed = store.claims[claim.claim_id]
        assert refreshed.level == EpistemicLevel.KNOWLEDGE
