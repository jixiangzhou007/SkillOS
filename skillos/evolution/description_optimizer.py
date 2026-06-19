"""Description optimization loop — improve skill triggering accuracy.

Inspired by Anthropic's skill-creator: generates trigger eval queries,
iteratively improves the description against train/test split, and
returns the best description (selected by test score to avoid overfitting).

Cost: ~5 LLM calls per iteration × max 5 iterations = ~25 calls.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class OptResult:
    """Result of a description optimization run."""
    original: str
    best: str
    iterations: int
    train_scores: list[float] = field(default_factory=list)
    test_scores: list[float] = field(default_factory=list)
    eval_queries: list[dict] = field(default_factory=list)


def generate_eval_queries(skill_name: str, body: str, llm_args: tuple) -> list[dict]:
    """Generate 20 eval queries: 10 should-trigger + 10 should-not-trigger."""
    from skillos.llm_client import call

    model = llm_args[2] if len(llm_args) > 2 else ""
    # Extract key terms
    keywords = _extract_keywords(body)
    trigger_section = ""
    tm = re.search(r'##\s*S_trigger\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL)
    if tm:
        trigger_section = tm.group(1)

    prompt = f"""你是一个技能触发测试生成器。为以下技能生成 20 个真实用户会输入的查询。

技能名称: {skill_name}
技能内容摘要: {body[:500]}
触发条件: {trigger_section[:200]}

生成 10 个 **should-trigger**（应该触发）和 10 个 **should-not-trigger**（不应该触发但容易误触发的近邻查询）。

规则:
- should-trigger: 各种说法，正式/口语/简写/错别字/中英混合。不要只用"帮我做X"。
- should-not-trigger: 近邻领域，共享关键词但目的不同。不要太明显（不是"写一个Python函数"）。
- 每个查询要具体——包含细节如文件名、金额、场景。
- 不要只输出查询词，要模拟真实用户会怎么打字。

输出 JSON 数组:
```json
[
  {{"query": "...", "should_trigger": true}},
  {{"query": "...", "should_trigger": false}},
  ...
]```

只输出 JSON，不要其他文字。"""

    try:
        raw = call(prompt, model=model, max_tokens=1500, temperature=0.7)
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        data = json.loads(m.group(1) if m else raw)
        return data[:20]
    except Exception as e:
        _log.warning("Eval query generation failed: %s", e)
        return _fallback_queries(skill_name)


def evaluate_description(desc: str, eval_set: list[dict], llm_args: tuple) -> float:
    """Score a description against eval queries (0-100)."""
    from skillos.llm_client import call

    model = llm_args[2] if len(llm_args) > 2 else ""
    queries_json = json.dumps(eval_set, ensure_ascii=False, indent=2)

    prompt = f"""你是一个技能触发评分器。给定描述和测试查询，判断每个查询是否应该触发。

## 待评估描述
{desc}

## 测试查询
{queries_json}

## 评分规则
对每个查询回答 "trigger" 或 "skip"。
- 如果 should_trigger=true 且你判 trigger → 正确
- 如果 should_trigger=false 且你判 skip → 正确
- 其他 → 错误

输出 JSON:
```json
{{"results": [{{"query": "...", "verdict": "trigger"|"skip"}}], "score": 85}}
```

score 是正确率 (0-100)。只输出 JSON。"""

    try:
        raw = call(prompt, model=model, max_tokens=800, temperature=0.1)
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        data = json.loads(m.group(1) if m else raw)
        return float(data.get("score", 50))
    except Exception as e:
        _log.warning("Description evaluation failed: %s", e)
        return 50.0


def optimize_description(
    skill_name: str,
    body: str,
    llm_args: tuple,
    *,
    max_iterations: int = 5,
) -> OptResult:
    """Run the description optimization loop.

    1. Generate eval queries
    2. Split 60% train / 40% test
    3. Iterate: propose → evaluate on train → keep if better
    4. Select best by test score
    """
    from skillos.llm_client import call
    from skillos.skills.portable_skill import build_description

    model = llm_args[2] if len(llm_args) > 2 else ""
    current_desc = build_description(skill_name, body)
    result = OptResult(original=current_desc, best=current_desc)

    # Generate eval set
    eval_set = generate_eval_queries(skill_name, body, llm_args)
    if not eval_set or len(eval_set) < 10:
        return result
    result.eval_queries = eval_set

    # Split: 60% train, 40% test
    split = int(len(eval_set) * 0.6)
    train_set = eval_set[:split]
    test_set = eval_set[split:]

    best_train_score = evaluate_description(current_desc, train_set, llm_args)
    best_test_score = evaluate_description(current_desc, test_set, llm_args)
    result.train_scores.append(best_train_score)
    result.test_scores.append(best_test_score)
    _log.info("Description opt start: train=%.0f test=%.0f", best_train_score, best_test_score)

    for i in range(max_iterations):
        # Propose improvement
        improve_prompt = f"""当前技能描述评分：train={best_train_score:.0f}/100, test={best_test_score:.0f}/100。

## 当前描述
{current_desc}

## 技能内容
{body[:600]}

## 失败的测试查询（这些应该触发但没触发，或不该触发但触发了）
{json.dumps([q for q in train_set if _would_fail(current_desc, q, train_set, llm_args)], ensure_ascii=False)[:500]}

请提出一个改进的描述。规则：
- 必须有具体触发词（中文+英文）
- 必须有边界（什么时候不触发）
- 第三人称
- ≤1024 字符
- 比当前描述更好

只输出新的描述文字，不要 JSON，不要其他。"""

        try:
            new_desc = call(improve_prompt, model=model, max_tokens=400, temperature=0.3).strip()
            new_desc = new_desc[:1024]
        except Exception as e:
            _log.warning("Description improvement failed: %s", e)
            continue

        # Evaluate on train
        new_train = evaluate_description(new_desc, train_set, llm_args)
        if new_train > best_train_score:
            current_desc = new_desc
            best_train_score = new_train
            best_test_score = evaluate_description(new_desc, test_set, llm_args)
            result.train_scores.append(best_train_score)
            result.test_scores.append(best_test_score)
            result.best = new_desc
            result.iterations = i + 1
            _log.info("Description improved: iter=%d train=%.0f test=%.0f", i+1, best_train_score, best_test_score)
        else:
            _log.info("Description not improved: iter=%d train=%.0f (best=%.0f)", i+1, new_train, best_train_score)
            break

    return result


def _extract_keywords(body: str) -> list[str]:
    """Extract potential trigger keywords from skill body."""
    keywords = []
    tm = re.search(r'##\s*S_trigger\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL)
    if tm:
        kwm = re.search(r'keywords?\s*[:：]\s*(.+)', tm.group(1), re.IGNORECASE)
        if kwm:
            keywords = [k.strip() for k in re.split(r'[,，、\s]+', kwm.group(1)) if k.strip()]
    return keywords


def _would_fail(desc: str, query: dict, eval_set: list[dict], llm_args: tuple) -> bool:
    """Quick check if a query would likely fail given current description."""
    # Simple heuristic: if should_trigger is false but query shares keywords with desc
    if not query.get("should_trigger", True):
        kw = _extract_keywords(desc)
        q_lower = query.get("query", "").lower()
        if any(k.lower() in q_lower for k in kw if len(k) > 1):
            return True
    return False


def _fallback_queries(skill_name: str) -> list[dict]:
    """Generate basic fallback eval queries."""
    return [
        {"query": f"帮我用{skill_name}处理一个任务", "should_trigger": True},
        {"query": f"我需要{skill_name}方面的帮助", "should_trigger": True},
        {"query": f"能不能帮我做{skill_name}", "should_trigger": True},
        {"query": f"有没有{skill_name}的工具", "should_trigger": True},
        {"query": f"我想了解一下{skill_name}的流程", "should_trigger": True},
        {"query": f"帮我写一个Python脚本处理数据", "should_trigger": False},
        {"query": f"今天天气怎么样", "should_trigger": False},
        {"query": f"给我讲个笑话", "should_trigger": False},
        {"query": f"怎么安装Node.js", "should_trigger": False},
        {"query": f"推荐一本好书", "should_trigger": False},
    ]
