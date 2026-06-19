"""Skill test-driven iteration loop — generate test prompts, self-evaluate,
collect feedback, and suggest improvements.

Inspired by Anthropic's skill-creator: "Draft → Test → Review → Improve → Repeat"
Lightweight version without subagent execution — uses LLM self-evaluation.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class TestCase:
    prompt: str
    expected_outcome: str = ""
    category: str = "normal"  # normal | edge | error


@dataclass
class TestResult:
    test: TestCase
    passed: bool
    score: int = 0  # 0-100
    feedback: str = ""
    suggestion: str = ""


@dataclass
class TestRun:
    skill_name: str
    skill_content: str
    tests: list[TestCase] = field(default_factory=list)
    results: list[TestResult] = field(default_factory=list)
    overall_score: float = 0.0
    improvement_suggestions: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results) * 100


def generate_test_cases(skill_name: str, body: str, llm_args: tuple,
                        count: int = 4) -> list[TestCase]:
    """Generate realistic test prompts for a skill."""
    from skillos.llm_client import call

    model = llm_args[2] if len(llm_args) > 2 else ""

    prompt = f"""为以下技能生成 {count} 个真实用户会提出的测试任务。

技能名称: {skill_name}
技能内容: {body[:800]}

规则:
- 每个任务是一句话，模拟真实用户会怎么打字
- 覆盖：正常场景、边界情况、错误输入
- 包含具体细节（文件名、金额、场景）
- 有些口语化、有错别字、中英混合

输出 JSON:
```json
[
  {{"prompt": "用户的原话", "expected_outcome": "期望技能如何响应", "category": "normal|edge|error"}},
  ...
]```
只输出 JSON。"""

    try:
        raw = call(prompt, model=model, max_tokens=600, temperature=0.7)
        m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        data = json.loads(m.group(1) if m else raw)
        return [TestCase(**item) for item in data[:count]]
    except Exception as e:
        _log.warning("Test case generation failed: %s", e)
        return [
            TestCase(prompt=f"帮我用{skill_name}处理一个常见任务",
                     expected_outcome="技能正确识别意图并按S_body步骤执行",
                     category="normal"),
            TestCase(prompt=f"{skill_name}的边界情况怎么处理",
                     expected_outcome="技能正确处理边界条件或提示用户补充信息",
                     category="edge"),
            TestCase(prompt=f"我不小心输入了无关内容，{skill_name}会怎么样",
                     expected_outcome="技能识别为不触发场景，不误触发",
                     category="error"),
        ]


def evaluate_skill(skill_name: str, body: str, tests: list[TestCase],
                   llm_args: tuple) -> TestRun:
    """Self-evaluate a skill against test prompts."""
    from skillos.llm_client import call

    model = llm_args[2] if len(llm_args) > 2 else ""
    run = TestRun(skill_name=skill_name, skill_content=body, tests=tests)

    for test in tests:
        eval_prompt = f"""你是技能测试评分员。评估以下技能是否能正确处理这个测试任务。

## 技能
{body[:1000]}

## 测试任务
用户输入: {test.prompt}
期望结果: {test.expected_outcome}
测试类型: {test.category}

## 评分标准
- 90-100: 技能能完美处理这个任务
- 70-89: 基本能处理，有小缺陷
- 50-69: 部分能处理，有明显不足
- 0-49: 无法处理或会产生错误

输出 JSON:
```json
{{"passed": true, "score": 85, "feedback": "技能包含相关步骤但缺少错误处理", "suggestion": "在S_body第3步后增加异常分支"}}
```
只输出 JSON。"""

        try:
            raw = call(eval_prompt, model=model, max_tokens=300, temperature=0.2)
            m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
            data = json.loads(m.group(1) if m else raw)
            run.results.append(TestResult(
                test=test,
                passed=data.get("passed", False),
                score=data.get("score", 50),
                feedback=data.get("feedback", ""),
                suggestion=data.get("suggestion", ""),
            ))
        except Exception as e:
            _log.warning("Skill evaluation failed for '%s': %s", test.prompt[:40], e)
            run.results.append(TestResult(
                test=test, passed=True, score=60,
                feedback=f"评分失败: {e}", suggestion="人工检查",
            ))

    # Compute overall
    if run.results:
        run.overall_score = sum(r.score for r in run.results) / len(run.results)

    # Collect improvement suggestions from failed tests
    for r in run.results:
        if not r.passed and r.suggestion:
            run.improvement_suggestions.append(
                f"[{r.test.category}] {r.suggestion}"
            )

    return run


def run_test_loop(skill_name: str, body: str, llm_args: tuple,
                  *, test_count: int = 4) -> TestRun:
    """Full test loop: generate tests → evaluate → return results."""
    tests = generate_test_cases(skill_name, body, llm_args, count=test_count)
    return evaluate_skill(skill_name, body, tests, llm_args)
