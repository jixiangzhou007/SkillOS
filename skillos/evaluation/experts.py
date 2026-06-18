"""Six independent expert judges for skill quality evaluation.

Each expert scores 1-2 focused dimensions. The narrow scope gives better LLM
accuracy than one judge trying to evaluate 10 dimensions at once.

Designed for cross-model validation: each expert can optionally be re-run on a
different (cheaper) model. If both models agree within a threshold, confidence
increases. If they disagree, the score is flagged for human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpertDefinition:
    """One expert judge — name, dimension(s) scored, and evaluation prompt."""
    name: str
    key: str                # e.g. "structure", "security", "brevity"
    description: str        # human-readable
    weight: float = 1.0     # importance weight in aggregation (0.0-2.0)
    max_tokens: int = 300   # LLM response budget


# ── Expert definitions ───────────────────────────────────────

EXPERTS: list[ExpertDefinition] = [
    ExpertDefinition(
        name="结构完整性评委",
        key="structure",
        description="自包含性 + 主入口可见性",
        weight=1.2,
        max_tokens=350,
    ),
    ExpertDefinition(
        name="安全性与健壮性评委",
        key="security",
        description="注入风险 + 凭据泄露 + 命令执行风险",
        weight=1.5,
        max_tokens=350,
    ),
    ExpertDefinition(
        name="参数抽象度评委",
        key="params",
        description="硬编码检测 + 参数抽象 + 决策轴暴露",
        weight=1.2,
        max_tokens=350,
    ),
    ExpertDefinition(
        name="决策覆盖度评委",
        key="routing",
        description="S_route/Decision routes 完整性 + 分支覆盖 + 边界处理",
        weight=1.3,
        max_tokens=350,
    ),
    ExpertDefinition(
        name="内容质量评委",
        key="content",
        description="过拟合检测 + 描述质量 + 跨平台可移植性",
        weight=1.0,
        max_tokens=350,
    ),
    ExpertDefinition(
        name="简洁度评委",
        key="brevity",
        description="奥卡姆剃刀 + 冗余检测 + 步骤合并建议",
        weight=0.8,
        max_tokens=300,
    ),
]


# ── Expert prompts (focused, single-topic) ────────────────────

def build_expert_prompt(expert: ExpertDefinition, skill_content: str, skill_name: str) -> str:
    """Build the evaluation prompt for a specific expert."""

    prompts = {
        "structure": f"""你是技能结构审计专家。只评「自包含性」和「主入口可见性」。

## 技能文档
```
{skill_content[:2000]}
```

## 评分维度
1. **自包含性** (self-contained): 一个全新Agent拿到这份技能，能不能独立执行？是否引用了不存在的文件/工具？
2. **主入口可见性** (entry visibility): 技能的入口是否在第一屏？新用户5秒内能找到吗？

## 输出JSON
```json
{{"self_contained": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "entry_visibility": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "overall": <0-100>,
  "summary": "<1句话总结>"}}
```""",

        "security": f"""你是技能安全审计专家。只评安全风险。

## 技能文档
```
{skill_content[:2000]}
```

## 检查项
1. **注入风险**: 是否有 `<script>`、`onerror=`、隐藏指令？
2. **凭据泄露**: 是否有硬编码的 API key、password、token？
3. **命令执行风险**: 是否包含 `subprocess`、`os.system`、`eval`、`exec`？是否包含 `curl ... | bash` 模式？

## 输出JSON
```json
{{"injection_risk": {{"score": <0-100越高越安全>, "passed": <true/false>, "detail": "<1句话>"}},
  "credential_leak": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "command_exec_risk": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "overall": <0-100>,
  "summary": "<1句话总结>"}}
```""",

        "params": f"""你是技能参数化审计专家。只评参数抽象度。

## 技能文档
```
{skill_content[:2000]}
```

## 检查项
1. **硬编码检测**: 是否有具体值应该被提取为参数？(如硬编码的阈值、URL、超时时间)
2. **参数抽象**: 所有可配置的决策轴是否暴露在参数区？是否有类型和默认值标注？

## 输出JSON
```json
{{"hardcoded": {{"score": <0-100越高越少硬编码>, "passed": <true/false>, "detail": "<1句话>", "examples": ["<具体硬编码例子>"]}},
  "abstraction": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "overall": <0-100>,
  "summary": "<1句话总结>"}}
```""",

        "routing": f"""你是技能路由审计专家。只评决策覆盖度。

## 技能文档
```
{skill_content[:2000]}
```

## 检查项
1. **决策表完整性**: 是否覆盖了正常流程+异常流程+边界情况？分支数是否≥3？
2. **边界处理**: 空输入、超大数据、并发冲突等极端情况是否有处理？

## 输出JSON
```json
{{"decision_table": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>", "branch_count": <N>}},
  "edge_cases": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "overall": <0-100>,
  "summary": "<1句话总结>"}}
```""",

        "content": f"""你是技能内容质量审计专家。只评描述质量和可移植性。

## 技能文档
```
{skill_content[:2000]}
```

## 检查项
1. **过拟合检测**: 技能中是否有只适用于特定训练样例的描述？是否过度特化到某个场景？
2. **描述质量**: 每步是否包含"为什么"而不仅是"做什么"？if-then分支是否具体？
3. **可移植性**: 这个技能能否在Claude Code/Cursor/Codex等不同平台使用？是否有平台绑定？

## 输出JSON
```json
{{"overfitting": {{"score": <0-100越高越通用>, "passed": <true/false>, "detail": "<1句话>"}},
  "description_quality": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "portability": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>"}},
  "overall": <0-100>,
  "summary": "<1句话总结>"}}
```""",

        "brevity": f"""你是技能简洁度审计专家。只评长度控制和冗余。

## 技能文档
```
{skill_content[:2000]}
```

## 检查项
1. **奥卡姆剃刀**: 有没有相邻的短步骤可以合并？有没有多余的解释？
2. **长度控制**: 技能总长度是否控制在合理范围？核心步骤是否≤7步？

## 输出JSON
```json
{{"occam_razor": {{"score": <0-100越高越精简>, "passed": <true/false>, "detail": "<1句话>", "merge_suggestion": "<可合并的步骤，没有就填none>"}},
  "length_control": {{"score": <0-100>, "passed": <true/false>, "detail": "<1句话>", "total_steps": <N>}},
  "overall": <0-100>,
  "summary": "<1句话总结>"}}
```""",
    }

    return prompts.get(expert.key, prompts["structure"])
