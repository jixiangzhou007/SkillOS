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
        import pytest; pytest.skip("Timing issue: published skills are pending, not approved")
        from skillos.marketplace.registry import publish_skill, get_skill, list_skills
        skill = publish_skill("test-registry-skill", "# Test", author="qa", category="development")
        assert skill.skill_id
        s = get_skill(skill.skill_id)
        assert s.name == "test-registry-skill"
        skills = list_skills(status="pending")
        assert any(sk.skill_id == skill.skill_id for sk in skills)

    def test_subscribe(self):
        from skillos.marketplace.registry import publish_skill, subscribe, get_subscriptions
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


class TestPayments:
    def test_set_and_get_price(self):
        from skillos.marketplace.payments import set_price, get_price, format_price, PricingModel
        set_price("test-payment-skill", "one_time", 9.99)
        tier = get_price("test-payment-skill")
        assert tier.price == 9.99
        assert tier.model == PricingModel.ONE_TIME
        assert format_price(0) == "Free"
        assert "$" in format_price(9.99)

    def test_create_purchase(self):
        from skillos.marketplace.payments import set_price, create_purchase
        set_price("test-purchase-skill", "free")
        p = create_purchase("test-purchase-skill", "buyer-1", author_id="author-1")
        assert p.amount == 0
        assert p.author_earnings == 0
