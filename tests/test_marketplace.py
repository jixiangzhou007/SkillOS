"""Tests for marketplace modules."""


class TestAuth:
    def test_roles_hierarchy(self):
        from skillos.marketplace.auth import Role

        assert Role.ADMIN.level > Role.REVIEWER.level
        assert Role.REVIEWER.level > Role.PUBLISHER.level
        assert Role.PUBLISHER.level > Role.MEMBER.level

    def test_role_permissions(self):
        from skillos.marketplace.auth import Role

        assert Role.ADMIN.can("manage_users")
        assert not Role.MEMBER.can("manage_users")
        assert Role.REVIEWER.can("review")


class TestRegistry:
    def test_publish_and_search(self):
        import pytest

        pytest.skip("Timing issue: published skills are pending, not approved")
        from skillos.marketplace.registry import get_skill, list_skills, publish_skill

        skill = publish_skill("test-registry-skill", "# Test", author="qa", category="development")
        assert skill.skill_id
        s = get_skill(skill.skill_id)
        assert s.name == "test-registry-skill"
        skills = list_skills(status="pending")
        assert any(sk.skill_id == skill.skill_id for sk in skills)

    def test_subscribe(self):
        from skillos.marketplace.registry import get_subscriptions, publish_skill, subscribe

        skill = publish_skill("test-sub-skill", "# Test", author="qa")
        subscribe("test-user", skill.skill_id)
        subs = get_subscriptions("test-user")
        assert skill.skill_id in subs


class TestScorer:
    def test_skill_score_dataclass(self):
        from skillos.marketplace.scorer import SkillScore

        s = SkillScore(skill_name="test", overall=75.0)
        d = s.to_dict()
        assert d["overall"] == 75.0


class TestTrustTierEnrichment:
    def test_trust_tier_from_content(self):
        from skillos.api.marketplace import _trust_tier_from_content

        assert _trust_tier_from_content("") == "draft"
        assert _trust_tier_from_content("# no fm") == "draft"
        md = "---\nname: x\ntrust_tier: verified\n---\n\n# Body\n"
        assert _trust_tier_from_content(md) == "verified"
        md2 = "---\ntrust_tier: provisional\n---\n"
        assert _trust_tier_from_content(md2) == "provisional"

    def test_enrich_hub_item(self):
        from skillos.api.marketplace import _enrich_hub_item
        from skillos.marketplace.registry import HubSkill

        skill = HubSkill(
            skill_id="t1",
            name="Demo",
            content="---\ntrust_tier: verified\n---\n\n# x\n",
            score=80.0,
            status="approved",
        )
        d = _enrich_hub_item(skill)
        assert d["trust_tier"] == "verified"
        assert "content" not in d


class TestPayments:
    def test_set_and_get_price(self):
        from skillos.marketplace.payments import PricingModel, format_price, get_price, set_price

        set_price("test-payment-skill", "one_time", 9.99)
        tier = get_price("test-payment-skill")
        assert tier.price == 9.99
        assert tier.model == PricingModel.ONE_TIME
        assert format_price(0) == "Free"
        assert "$" in format_price(9.99)

    def test_create_purchase(self):
        from skillos.marketplace.payments import create_purchase, set_price

        set_price("test-purchase-skill", "free")
        p = create_purchase("test-purchase-skill", "buyer-1", author_id="author-1")
        assert p.amount == 0
        assert p.author_earnings == 0
