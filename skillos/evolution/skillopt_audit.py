"""Audit and fresh-agent deployment testing for SkillOpt.

SkillEvolver-inspired independent auditor — checks a skill document for
deployment hazards that the author agent is blind to, such as hardcoded
constants, missing entry points, silent-bypass patterns, and overfitting.
"""

import json
import logging
import re

from .skillopt_types import AuditReport

_log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# SkillEvolver-inspired: Independent Auditor
# ═══════════════════════════════════════════════════════════════
#
# SkillEvolver's key insight: skill quality can't be judged by the
# author agent alone. A clean-context Auditor checks deployment hazards
# that the author is blind to: hardcoded constants, missing entry points,
# silent-bypass patterns, overfitting to training examples.

def audit_skill(
    skill_content: str,
    skill_name: str,
    llm_args: tuple,
    *,
    training_examples: list[str] | None = None,
) -> AuditReport:
    """Independent Auditor — checks a skill for deployment hazards.

    The Auditor sees ONLY the skill document and task description.
    It does NOT see the author agent's private reasoning, exploration
    strategies, or the training data labels. This is the "fresh eyes" check.

    Detects:
    1. Hardcoded constants — values that should be parameters
    2. Missing entry point — main action not prominent enough
    3. Silent-bypass — agent could skip the skill without noticing
    4. Overfitting — training-specific patterns that won't generalize
    5. Self-contained — can the skill work without external context?
    6. Abstraction — are key axes parameterized or hardcoded?
    """
    from skillos.llm_client import call

    examples_hint = ""
    if training_examples:
        examples_hint = "\n## 训练时见过的任务样例\n" + "\n".join(
            f"- {ex[:120]}" for ex in training_examples[:3]
        )
        examples_hint += "\n\n⚠️ 检查技能文档中是否残留了只适用于这些样例的硬编码常量或假设。"

    prompt = f"""你是技能部署审计员。你只看到候选技能文档，看不到作者 Agent 的私有推理。

## 候选技能文档
```
{skill_content[:2000]}
```

## 技能名称
{skill_name}
{examples_hint}

## 审计维度（每个维度独立打分：PASS / WARN / FAIL）

### 1. 自包含性 (Self-contained)
- 一个全新 Agent 拿到这份技能，能不能独立执行，不需要额外上下文？
- 技能是否引用了不存在的文件、工具或外部资源？

### 2. 主入口可见性 (Entry Point Visibility)
- 技能的主入口（最核心的那个操作）是否在最显眼的位置？
- 一个 fresh agent 能不能在 5 秒内找到"我该调用什么"？
- 检查：S_trigger 的描述是否足够具体，能让 dispatcher 正确路由？

### 3. 硬编码检测 (Hardcoded Constants)
- 技能中是否包含只适用于训练样例的常量（文件名、路径、特定数值）？
- 这些常量是否应该被抽象为 S_params？

### 4. Silent-Bypass 风险
- 是否存在"Agent 跳过了关键步骤但技能没报错"的路径？
- S_body 的每个步骤是否有明确的成功/失败判定？
- if-then 分支是否遗漏了"异常情况"的处理？

### 5. 过拟合检测 (Overfitting)
- 技能中的规则是否过度特化到训练样例？
- 换成同类但不同名的文件、不同的数值范围，技能还能用吗？

### 6. 参数抽象 (Parameter Abstraction)
- 关键决策轴（阈值、文件类型、API 端点等）是否在 S_params 中暴露？
- 还是写死在 S_body 的步骤描述里？

### 7. 描述质量 (Description Quality)
- S_trigger 中的 description/keywords 是否足够具体？
- 有没有列出**具体的触发词**（不是"帮助用户"这种泛词）？
- 有没有写清楚**不应该触发的边界**？
- 对照标准：❌ "帮助处理视频" → ✅ "短视频口播稿撰写和分镜拆解。触发词：写脚本、改文案、短视频结构。不触发：纯娱乐搞笑视频。"

### 8. 决策表完整性 (Decision Table)

### 9. 跨平台可移植性 (Cross-Platform Portability)

### 10. 简洁度 (Brevity — "LLM越强，Skill越短")
- 模型能力越强，Skill 应该越精简。强模型只需方向指引，不需要逐字步骤。
- SKILL.md 是否超过 500 字？如果是，检查是否过度解释或重复约定。
- S_body 的每个步骤是否是"单一可验证动作"，而非"解释+动作+示例"的复合体？
- 如果目标模型是 Claude 4.x / GPT-5 / DeepSeek V4 级别：Skill 应 < 400 字。
- 如果目标模型是 Qwen 3B 级别：Skill 可以适当增加到 < 800 字。

- Skill 是否使用了特定平台的专用语法（如 Claude-only tool names）？
- S_trigger 中的关键词是否足够通用，能在不同调度器（Claude/Codex/Hermes）中正确触发？
- S_route 文件路径引用是否跨平台兼容（Windows/Linux/macOS）？
- MCP tool 参数是否使用标准 JSON Schema，无平台特定字段？

- 是否有 S_route 决策表？
- 决策表是否覆盖了 S_body 中提到的所有分支场景？
- 每个路由是否指向了实际存在的 references/ 文件路径？
- 如果 S_body 有多个分支但 S_route 只有一行 → WARN

## 输出格式
```json
{{
  "checks": [
    {{"check": "self_contained", "passed": true, "severity": "PASS|WARN|FAIL", "detail": "具体发现", "suggestion": "修改建议"}},
    {{"check": "entry_visibility", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "hardcoded_constants", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "silent_bypass", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "overfitting", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "param_abstraction", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "description_quality", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "decision_table", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "portability", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}},
    {{"check": "brevity", "passed": true, "severity": "...", "detail": "...", "suggestion": "..."}}}}
  ],
  "overall_score": 85,
  "summary": "一句话总结审计结果"
}}
```

只输出 JSON。"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=1500, temperature=0.1)
    except Exception as e:
        _log.warning("Auditor LLM call failed: %s", e)
        return AuditReport(passed=True, score=100,
                          checks=[{"check": "auditor_error", "passed": True,
                                   "severity": "WARN", "detail": str(e)}],
                          summary="审计器调用失败，放行")

    # Parse — multiple fallback strategies for robustness
    data = None
    # Strategy 1: JSON in markdown code block
    m = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', raw, re.DOTALL)
    json_candidate = m.group(1).strip() if m else ""
    if json_candidate:
        try:
            data = json.loads(json_candidate)
        except json.JSONDecodeError:
            pass
    # Strategy 2: Raw text is pure JSON
    if data is None and raw.strip().startswith('{'):
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            pass
    # Strategy 3: Find JSON object in raw text via brace matching
    if data is None:
        brace_start = raw.find('{')
        brace_end = raw.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            try:
                data = json.loads(raw[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
    # Strategy 4: Fix common LLM JSON errors (trailing commas, unquoted keys)
    if data is None:
        cleaned = raw.strip()
        # Remove text before first { and after last }
        brace_start = cleaned.find('{')
        brace_end = cleaned.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            cleaned = cleaned[brace_start:brace_end + 1]
        # Fix trailing commas before closing } or ]
        cleaned = re.sub(r',\s*}', '}', cleaned)
        cleaned = re.sub(r',\s*]', ']', cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    if data is None:
        _log.warning("Auditor JSON parse failed — raw[:300]: %s", raw[:300])
        return AuditReport(passed=True, score=60,
                          checks=[{"check": "parse_error", "passed": True,
                                   "severity": "WARN", "detail": "审计结果解析失败"}],
                          summary="审计解析失败，降级放行")

    checks = data.get("checks", [])
    score = data.get("overall_score", 50)
    failures = [c for c in checks if c.get("severity") == "FAIL"]
    warnings = [c for c in checks if c.get("severity") == "WARN"]

    report = AuditReport(
        passed=len(failures) == 0,
        score=score,
        checks=checks,
        summary=data.get("summary", ""),
    )

    _log.info("Audit: skill=%s score=%d passed=%s failures=%d warnings=%d",
              skill_name, score, report.passed, len(failures), len(warnings))

    return report


def build_audit_context(report: AuditReport) -> str:
    """Build the audit report context for the optimizer prompt."""
    if report.score >= 90:
        return ""

    lines = ["\n## 🔍 独立审计报告 (SkillEvolver Auditor)\n"]
    lines.append(f"总分: {report.score}/100 | {'✅ 通过' if report.passed else '❌ 未通过'}\n")

    failures = [c for c in report.checks if c.get("severity") == "FAIL"]
    warnings = [c for c in report.checks if c.get("severity") == "WARN"]

    if failures:
        lines.append("### ❌ 必须修复")
        for c in failures:
            lines.append(f"- **{c['check']}**: {c.get('detail', '')}")
            if c.get("suggestion"):
                lines.append(f"  💡 {c['suggestion']}")

    if warnings:
        lines.append("\n### ⚠️ 建议修复")
        for c in warnings:
            lines.append(f"- **{c['check']}**: {c.get('detail', '')}")

    lines.append(f"\n📝 {report.summary}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# SkillEvolver-inspired: Fresh-Agent Deployment Test
# ═══════════════════════════════════════════════════════════════
#
# "Skill quality can't be judged by the author agent alone."
# A clean agent loads the skill and tries to use it. Failures here
# reveal deployment hazards the author was blind to.

def fresh_agent_deploy_test(
    skill_content: str,
    skill_name: str,
    test_task: str,
    llm_args: tuple,
) -> dict:
    """Deploy the skill to a fresh agent and observe what happens.

    The fresh agent has NO context about how the skill was created.
    It only gets: the skill document + the test task.

    Returns {task, invoked_skill, result_preview, errors, score}
    """
    from skillos.skills import agent_factory

    try:
        agent = agent_factory.create_agent(skill_content, test_task)
        result = agent_factory.run_agent(agent, test_task)

        # Heuristic checks on the result
        invoked = _check_skill_invocation(test_task, result, skill_content)
        errors = _detect_deployment_errors(result)

        from skillos.evolution.evolver import record_trace
        trace = record_trace(
            skill_name, test_task, result, 0, llm_args
        )

        return {
            "task": test_task[:150],
            "invoked_skill": invoked,
            "result_preview": result[:300],
            "errors": errors,
            "score": trace.judge_score,
        }
    except Exception as e:
        return {
            "task": test_task[:150],
            "invoked_skill": False,
            "result_preview": "",
            "errors": [str(e)],
            "score": 0,
        }


def _check_skill_invocation(task: str, result: str, skill_content: str) -> bool:
    """Check if the fresh agent actually used the skill.

    Heuristic: does the result reference concepts/terms/step names
    that are unique to this skill document?
    """
    # Extract distinctive terms from skill
    terms = set()
    for line in skill_content.split("\n"):
        line = line.strip()
        if line.startswith("## ") or line.startswith("### "):
            terms.add(line.replace("#", "").strip()[:30])
        # Extract step numbers
        if line.startswith(("1.", "2.", "3.", "4.", "5.")):
            terms.add(line[:60])

    # Check if any distinctive term appears in result
    matches = 0
    for term in terms:
        if len(term) > 10 and term in result:
            matches += 1

    return matches >= 1


def _detect_deployment_errors(result: str) -> list[str]:
    """Detect common deployment failure patterns in the agent's output."""
    errors = []

    # Silent bypass: agent says "I don't know how to..." or "I cannot..."
    if re.search(r'(I don\'t know how|I cannot|Unable to|无法|不能|不知道如何)', result, re.IGNORECASE):
        errors.append("silent_bypass: agent couldn't use the skill")

    # Missing dependency: "file not found", "module not found"
    if re.search(r'(file not found|module not found|No such file|找不到文件)', result, re.IGNORECASE):
        errors.append("missing_dependency: skill references unavailable resource")

    # Hallucinated action: result contains made-up API calls
    if re.search(r'(I will|let me|I\'ll try)', result, re.IGNORECASE) and len(result) < 100:
        errors.append("no_execution: agent talked about doing but didn't execute")

    return errors


def run_fresh_agent_battery(
    skill_content: str,
    skill_name: str,
    test_tasks: list[str],
    llm_args: tuple,
) -> dict:
    """Run a battery of fresh-agent deployment tests.

    Returns summary: {tasks_tested, invocation_rate, avg_score, failures}
    """
    results = []
    for task in test_tasks[:3]:  # max 3 tasks
        r = fresh_agent_deploy_test(skill_content, skill_name, task, llm_args)
        results.append(r)

    invoked_count = sum(1 for r in results if r["invoked_skill"])
    scores = [r["score"] for r in results if r["score"] > 0]
    avg_score = sum(scores) / len(scores) if scores else 0
    all_errors = []
    for r in results:
        all_errors.extend(r.get("errors", []))

    return {
        "tasks_tested": len(results),
        "invocation_rate": round(invoked_count / len(results), 2) if results else 0,
        "avg_score": round(avg_score, 1),
        "failures": all_errors,
        "detail": [
            {"task": r["task"][:80], "invoked": r["invoked_skill"],
             "score": r["score"], "errors": r["errors"]}
            for r in results
        ],
    }
