"""Unit tests for extraction quality assessment — no LLM required."""

from skillos.skills.agent import SkillExtractionAgent


class TestAssessDraftQuality:
    def test_empty_draft_returns_zero(self):
        agent = SkillExtractionAgent()
        q = agent._assess_draft_quality()
        assert q["pct"] == 0
        assert len(q["gaps"]) >= 1  # has at least one gap item

    def test_minimal_steps_gives_score(self):
        agent = SkillExtractionAgent()
        agent._draft_content = """# Test Skill
## Steps
1. First step with enough detail to pass the length check
2. Second step also with enough detail here
3. Third step has sufficient length
4. Fourth step meets the minimum requirement
5. Fifth step is here as well for testing
"""
        q = agent._assess_draft_quality()
        assert q["pct"] >= 18  # steps alone give 18%

    def test_full_draft_scores_high(self):
        agent = SkillExtractionAgent()
        agent._draft_content = """# API Rate Limiter
## S_trigger
- trigger: every API request passes through middleware
- keywords: rate limit, throttle, api

## S_body
1. Check Redis counter for this user with key prefix ratelimit:{user_id}
2. If counter exceeds limit of 100 requests per minute, return HTTP 429
3. If under limit, increment counter and set TTL of 60 seconds
4. Set response headers X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
5. For premium users with subscription active, double the base limit to 200

## S_route
| Condition | Action |
|-----------|--------|
| premium user | double limit to 200/min |
| internal service | bypass rate limiting |
| Redis down | fallback to in-memory counter |

## S_params
- rate_limit: int = 100 (requests per minute per user)
- burst_allowance: int = 120

## Gotchas
- Redis network partition causes double-counting
- Clock skew between application servers
- Distributed rate limiting needs consensus
"""
        q = agent._assess_draft_quality()
        assert q["pct"] >= 50, f"Expected >=50%, got {q['pct']}%"
        assert q["md_pct"] >= 45  # steps + branches + trigger + gotchas

    def test_branch_detection_with_if_then(self):
        agent = SkillExtractionAgent()
        agent._draft_content = """# Test
1. Step one with good amount of detail here yes
2. Step two with also enough description text
3. Step three meets the minimum length
4. Step four has sufficient detail as well
5. Fifth step for good measure here

if premium_user then double_limit
"""
        q = agent._assess_draft_quality()
        assert q["pct"] >= 30  # steps + branches

    def test_gotcha_detection(self):
        agent = SkillExtractionAgent()
        agent._draft_content = """# Test
1. Step one with good detail text here for testing
2. Step two also has enough characters now
3. Step three meets minimum length requirement
4. Step four provides sufficient detail text
5. Fifth step completes the minimum set

Common pitfall: Redis network partition causes double-counting
"""
        q = agent._assess_draft_quality()
        assert q["pct"] >= 27  # steps + gotchas (15%)

    def test_chinese_trigger_detection(self):
        agent = SkillExtractionAgent()
        agent._draft_content = """# 测试技能
## 触发条件
- 每次API请求经过中间件时触发

1. 检查Redis计数器带用户ID前缀
2. 如果超过限制返回429状态码
3. 未超限则递增计数器并设置60秒TTL
4. 设置响应头X-RateLimit信息
5. 对高级用户双倍限制额度
"""
        q = agent._assess_draft_quality()
        assert q["pct"] >= 30  # steps + trigger via Chinese keywords

    def test_knowledge_counter_init_zero(self):
        agent = SkillExtractionAgent()
        assert agent._knowledge_items == 0

    def test_asked_probes_init_empty(self):
        agent = SkillExtractionAgent()
        assert len(agent._asked_probes) == 0
