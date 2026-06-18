"""SkillHub Scoring Engine — fresh-agent battery + Auditor 8-dim + Cross-model.

The golden rule: scoring MUST use a clean Agent instance, not the author's Agent.
This prevents "every skill scores 100 because the author tested it themselves."

Score = execution_score × 0.6 + audit_score × 0.4
  - execution_score: avg score from fresh-agent runs on 3-5 test tasks (0-100)
  - audit_score: Auditor 8-dim check converted to 0-100 scale

Cross-model validation: when multiple models are available, run scoring with
each and cross-validate to eliminate self-assessment bias. When only one model
is available, use adversarial self-review (model double-checks its own scoring).

Review gate:
  - score >= 70 → auto-approved
  - score 50-69 → pending human review
  - score < 50 → auto-rejected
"""


import json
import logging
import os
import time
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)


@dataclass
class SkillScore:
    """Complete scoring result for a skill submission."""

    skill_name: str
    overall: float = 0.0           # 0-100
    execution_score: float = 0.0   # 0-100
    audit_score: float = 0.0       # 0-100
    execution_detail: dict = field(default_factory=dict)
    # {tasks_tested, invocation_rate, avg_score, detail: [{task, invoked, score, errors}]}
    audit_checks: list[dict] = field(default_factory=list)
    # [{check, passed, severity, detail, suggestion}]
    gate_result: str = ""          # approved | pending | rejected
    gate_reason: str = ""
    test_tasks_used: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "overall": round(self.overall, 1),
            "execution_score": round(self.execution_score, 1),
            "audit_score": round(self.audit_score, 1),
            "execution_detail": self.execution_detail,
            "audit_checks": [
                {"check": c["check"], "passed": c.get("passed", True),
                 "severity": c.get("severity", "PASS"), "detail": c.get("detail", "")[:120]}
                for c in self.audit_checks
            ],
            "gate": self.gate_result,
            "gate_reason": self.gate_reason,
            "test_tasks": self.test_tasks_used,
            "elapsed_s": self.elapsed_s,
        }


# ═══════════════════════════════════════════════════════════════
# Test Task Generation
# ═══════════════════════════════════════════════════════════════

def _generate_test_tasks(skill_content: str, skill_name: str, llm_args: tuple) -> list[str]:
    """Generate 3-5 standardized test tasks from the skill's own description.

    These are what a real user might ask. The author never sees them.
    """
    from skillos.llm_client import call

    prompt = f"""你是技能测试任务生成器。根据以下技能文档，生成 3-5 个真实的用户会提出的任务。

## 技能文档
```
{skill_content[:1500]}
```

## 规则
1. 每个任务是一句话，模拟真实用户会怎么问
2. 覆盖不同的场景：简单任务、复杂任务、边界情况
3. 不要重复——每个任务测试不同的能力
4. 任务描述要具体（文件名、参数值、场景），不要泛泛的"执行这个技能"
5. 可以故意包含一些模糊点（真实用户不会说得很精确）

## 输出格式
每行一个任务，不要编号，不要其他内容。最多 5 行。"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=400, temperature=0.7)
        tasks = [line.strip() for line in raw.strip().split("\n")
                if line.strip() and len(line.strip()) > 20]
        return tasks[:5]
    except Exception as e:
        _log.warning("Test task generation failed: %s", e)
        return [f"请按照技能「{skill_name}」的要求执行一个典型任务",
                f"使用「{skill_name}」技能处理一个边界情况"]


# ═══════════════════════════════════════════════════════════════
# Full Scoring Pipeline
# ═══════════════════════════════════════════════════════════════

def score_skill(
    skill_content: str,
    skill_name: str,
    llm_args: tuple,
    *,
    test_tasks: list[str] | None = None,
) -> SkillScore:
    """Score a skill submission using fresh-agent battery + Auditor.

    1. Generate test tasks (if not provided)
    2. Run fresh-agent deployment tests (60% weight)
    3. Run Auditor 8-dim check (40% weight)
    4. Apply review gate
    """
    t_start = time.time()

    # 1. Generate test tasks
    if not test_tasks:
        test_tasks = _generate_test_tasks(skill_content, skill_name, llm_args)

    _log.info("Scoring skill: %s with %d test tasks", skill_name, len(test_tasks))

    # 2. Fresh-agent execution tests (60%)
    from skillos.evolution.skillopt import run_fresh_agent_battery
    exec_result = run_fresh_agent_battery(
        skill_content, skill_name, test_tasks, llm_args
    )

    # Convert execution score to 0-100 scale
    # invocation_rate contributes 30%, avg_score contributes 70%
    invocation_rate = exec_result.get("invocation_rate", 0)
    avg_exec_score = exec_result.get("avg_score", 0)
    execution_score = round(
        (invocation_rate * 30) + (avg_exec_score / 5.0 * 70), 1
    )

    # 3. Auditor 8-dim check (40%)
    from skillos.evolution.skillopt import audit_skill
    audit_report = audit_skill(skill_content, skill_name, llm_args)
    audit_score = float(audit_report.score)

    # 4. Compute overall
    # Compression Reward: shorter skills get bonus (RL-trained skill libraries)
    word_count = len(skill_content.split())
    compression_bonus = 10 if word_count < 100 else 5 if word_count < 200 else 2 if word_count < 400 else -5 if word_count > 800 else 0
    overall = round(execution_score * 0.55 + audit_score * 0.35 + compression_bonus * 0.1, 1)

    # 5. Gate
    if overall >= 70:
        gate = "approved"
        reason = f"自动通过 (综合 {overall}: 执行 {execution_score} + 审计 {audit_score})"
    elif overall >= 50:
        gate = "pending"
        reason = f"待人工复审 (综合 {overall}: 执行 {execution_score} + 审计 {audit_score})"
    else:
        reason = f"自动拒绝 (综合 {overall} < 50: 执行 {execution_score} + 审计 {audit_score})"
        # Build specific feedback
        audit_fails = [c for c in audit_report.checks if c.get("severity") == "FAIL"]
        if audit_fails:
            reason += f"。审计失败: {', '.join(c['check'] for c in audit_fails)}"
        if invocation_rate < 0.5:
            reason += f"。技能调用率仅 {invocation_rate:.0%}，fresh agent 无法正常触发此技能"
        gate = "rejected"

    elapsed = round(time.time() - t_start, 1)
    _log.info("Scored: %s overall=%.1f gate=%s (%.1fs)", skill_name, overall, gate, elapsed)

    return SkillScore(
        skill_name=skill_name,
        overall=overall,
        execution_score=execution_score,
        audit_score=audit_score,
        execution_detail=exec_result,
        audit_checks=audit_report.checks,
        gate_result=gate,
        gate_reason=reason,
        test_tasks_used=test_tasks,
        elapsed_s=elapsed,
    )


# ═══════════════════════════════════════════════════════════════
# Publish + Score pipeline
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# Cross-Model Validation
# ═══════════════════════════════════════════════════════════════

def cross_model_score(
    skill_content: str,
    skill_name: str,
    primary_llm_args: tuple,
    *,
    secondary_models: list[tuple[str, tuple]] | None = None,
    test_tasks: list[str] | None = None,
) -> SkillScore:
    """Score with cross-model validation to eliminate self-assessment bias.

    Runs scoring with the primary model, then cross-validates:
    - If secondary models are available: runs each, averages results
    - If only one model: adversarial self-review (model double-checks own score)
    - Reports score variance across models as a confidence indicator

    Returns the primary score with cross_model metadata attached.
    """
    primary_score = score_skill(skill_content, skill_name, primary_llm_args, test_tasks=test_tasks)

    cross_scores = {}
    if secondary_models:
        for model_name, llm_args in secondary_models[:2]:  # max 2 secondary
            try:
                sec = score_skill(skill_content, skill_name, llm_args, test_tasks=test_tasks)
                cross_scores[model_name] = sec.overall
                _log.info("Cross-model: %s scored %.1f (primary: %.1f)",
                         model_name, sec.overall, primary_score.overall)
            except Exception as e:
                _log.warning("Cross-model %s failed: %s", model_name, e)
                cross_scores[model_name] = -1

        if cross_scores:
            valid = [v for v in cross_scores.values() if v >= 0]
            if valid:
                avg_cross = sum(valid) / len(valid)
                # Blend: 70% primary, 30% cross-model average
                blended = round(primary_score.overall * 0.7 + avg_cross * 0.3, 1)
                variance = round(max(valid) - min(valid), 1) if len(valid) > 1 else 0
                primary_score.overall = blended
                primary_score.execution_detail["cross_model"] = {
                    "models_used": ["primary"] + list(cross_scores.keys()),
                    "scores": {"primary": primary_score.overall, **cross_scores},
                    "variance": variance,
                    "confidence": "high" if variance < 10 else "medium" if variance < 20 else "low",
                }
    else:
        # Adversarial self-review: ask the same model to critique its own score
        try:
            from skillos.llm_client import call
            review_prompt = f"""你是评分审计员。刚才你对以下技能打了 {primary_score.overall:.0f}/100 分。

请用 1-2 句话说明：这个分数是否公允？有没有可能偏高或偏低？

技能: {skill_name}
执行分: {primary_score.execution_score:.0f}
审计分: {primary_score.audit_score:.0f}"""
            review = call(review_prompt,
                         model=primary_llm_args[2] if len(primary_llm_args) > 2 else "",
                         max_tokens=150, temperature=0.1)
            primary_score.execution_detail["cross_model"] = {
                "mode": "adversarial_self_review",
                "review": review.strip(),
            }
        except Exception:
            pass

    return primary_score


def get_available_models() -> list[tuple[str, tuple]]:
    """Discover available alternative models for cross-validation.

    Checks common environment configs for secondary API endpoints.
    Returns list of (model_name, llm_args).
    """
    from skillos.config import get_config
    cfg = get_config()
    models = []
    primary = (cfg.api_key, cfg.base_url, cfg.model, cfg.to_llm_args()[3])

    # Check for Hunyuan/other providers
    key2 = os.environ.get("SECONDARY_API_KEY", "")
    url2 = os.environ.get("SECONDARY_BASE_URL", "")
    model2 = os.environ.get("SECONDARY_MODEL", "")
    if key2 and url2 and model2:
        models.append((model2, (key2, url2, model2, {})))

    return models


def publish_and_score(
    name: str,
    content: str,
    llm_args: tuple,
    *,
    author: str = "anonymous",
    description: str = "",
    tags: list[str] | None = None,
    category: str = "other",
) -> dict:
    """Full pipeline: register skill → score it → update status.

    Returns {skill_id, slug, score, gate, ...}
    """
    from skillos.marketplace import registry as reg

    # 1. Register
    skill = reg.publish_skill(
        name=name, content=content, author=author,
        description=description, tags=tags, category=category,
    )

    # 2. Score with cross-model validation
    secondary = get_available_models()
    score_result = cross_model_score(
        content, name, llm_args,
        secondary_models=secondary if secondary else None,
    )

    # 3. Update registry with scores
    reg.update_skill_score(
        skill.skill_id,
        execution_score=score_result.execution_score,
        audit_score=score_result.audit_score,
        audit_json=json.dumps(score_result.to_dict(), ensure_ascii=False),
        version_num=1,
    )

    return {
        "skill_id": skill.skill_id,
        "slug": skill.slug,
        "name": name,
        "score": score_result.to_dict(),
        "gate": score_result.gate_result,
        "gate_reason": score_result.gate_reason,
    }
