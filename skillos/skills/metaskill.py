"""MetaSkill — Multi-skill pipeline orchestration with role assignment.

A MetaSkill chains multiple skills into a workflow where each step is
executed by a specialist role with defined acceptance criteria.

Philosophy: "卷 Harness，不卷模型" — compete on orchestration, not model size.
Role system inspired by Garry Tan's gstack (23 specialist personas).

Roles are not just labels — each role carries acceptance criteria that
the step output must satisfy before the pipeline can proceed.
"""


import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

_log = logging.getLogger(__name__)

META_MARKER = "type: metaskill"

# ── Built-in role templates (inspired by gstack 23 roles) ──

ROLE_TEMPLATES: dict[str, dict] = {
    "business_analyst": {
        "id": "business_analyst",
        "label": "业务分析师",
        "icon": "📋",
        "responsibility": "澄清需求，将模糊描述转化为可执行规格",
        "acceptance": "需求文档包含：触发场景、输入输出、边界条件、成功标准",
    },
    "process_designer": {
        "id": "process_designer",
        "label": "流程设计师",
        "icon": "🔧",
        "responsibility": "将需求转化为分步操作流程，识别决策点和异常路径",
        "acceptance": "流程包含：≥3 步骤、≥2 决策分支、异常处理路径",
    },
    "reviewer": {
        "id": "reviewer",
        "label": "审核员",
        "icon": "✅",
        "responsibility": "检查流程完整性，标记缺失步骤、模糊描述和逻辑漏洞",
        "acceptance": "审核报告包含：通过/需修改判定、具体问题位置、修改建议",
    },
    "qa_lead": {
        "id": "qa_lead",
        "label": "测试负责人",
        "icon": "🧪",
        "responsibility": "设计测试场景，验证流程在边界条件下的行为",
        "acceptance": "测试报告包含：≥3 个测试场景（含边界）、通过/失败、覆盖缺口",
    },
    "security_auditor": {
        "id": "security_auditor",
        "label": "安全审计员",
        "icon": "🛡️",
        "responsibility": "检查流程中的数据安全、权限控制和合规风险",
        "acceptance": "审计报告标记：敏感数据暴露、权限缺失、合规违规",
    },
    "tech_writer": {
        "id": "tech_writer",
        "label": "技术文档工程师",
        "icon": "📝",
        "responsibility": "将流程转化为用户友好的操作文档",
        "acceptance": "文档可被非专业人员独立执行，无歧义",
    },
    "release_manager": {
        "id": "release_manager",
        "label": "发布经理",
        "icon": "🚀",
        "responsibility": "最终验证技能包完整性，确认所有门禁通过",
        "acceptance": "发布清单全部勾选：文档齐全、测试通过、审核完成、资源就绪",
    },
}


@dataclass
class PipelineStep:
    """A single step in a MetaSkill pipeline, executed by a specialist role."""

    name: str                          # step identifier, e.g. "fact_check"
    skill_name: str                    # which skill to use
    task_template: str = ""            # the task to pass to this skill
    depends_on: list[str] = field(default_factory=list)  # steps that must complete first
    output_key: str = ""               # key to store output for downstream steps
    allowed_tools: list[str] = field(default_factory=list)  # tool whitelist for this step
    timeout: int = 120                 # max seconds
    # Role assignment (v0.3.0)
    role: str = ""                     # role ID from ROLE_TEMPLATES or custom
    acceptance_criteria: str = ""      # what must be true for this step to pass
    handoff_to: str = ""               # explicit role handoff (next role to receive output)


@dataclass
class MetaSkill:
    """A parsed MetaSkill document with role-assigned pipeline steps."""

    name: str
    goal: str                          # natural language description of the goal
    steps: list[PipelineStep] = field(default_factory=list)
    tool_whitelist: list[str] = field(default_factory=list)  # global tool whitelist
    risk_level: str = "low"            # low | medium | high
    raw_content: str = ""              # original markdown content

    @property
    def roles(self) -> list[str]:
        """Unique roles assigned in this pipeline, in execution order."""
        seen = set()
        result = []
        for s in self.steps:
            if s.role and s.role not in seen:
                seen.add(s.role)
                result.append(s.role)
        return result

    @property
    def role_count(self) -> int:
        return len(self.roles)

    def get_role_info(self, role_id: str) -> dict:
        """Get role template info, or a basic fallback for custom roles."""
        return ROLE_TEMPLATES.get(role_id, {
            "id": role_id,
            "label": role_id,
            "icon": "👤",
            "responsibility": f"Execute {role_id} tasks",
            "acceptance": "Step output meets quality threshold",
        })

    def to_markdown(self) -> str:
        """Serialize to MetaSkill Markdown format with role annotations."""
        lines = [
            "---",
            "type: metaskill",
            f"name: {self.name}",
            "---",
            "",
            f"# MetaSkill: {self.name}",
            "",
            "## Goal",
            self.goal,
            "",
        ]

        # Role overview
        if self.roles:
            lines.append("## Roles")
            for rid in self.roles:
                info = self.get_role_info(rid)
                lines.append(f"- {info['icon']} **{info['label']}** ({rid}) — {info['responsibility']}")
            lines.append("")

        lines.append("## Pipeline")
        lines.append("```pipeline")
        for step in self.steps:
            parts = []
            if step.depends_on:
                parts.append(f"depends_on: [{', '.join(step.depends_on)}]")
            if step.output_key:
                parts.append(f"output_key: {step.output_key}")
            if step.role:
                parts.append(f"role: {step.role}")
            if step.acceptance_criteria:
                parts.append(f"accept: {step.acceptance_criteria[:60]}")
            if step.handoff_to:
                parts.append(f"handoff_to: {step.handoff_to}")
            if step.allowed_tools:
                parts.append(f"tools: [{', '.join(step.allowed_tools)}]")
            meta = " | ".join(parts)
            line = f"{step.name}: {step.skill_name}"
            if meta:
                line += f"  # {meta}"
            lines.append(line)
        lines.append("```")
        lines.append("")
        if self.tool_whitelist:
            lines.append("## Tool Whitelist")
            for t in self.tool_whitelist:
                lines.append(f"- {t}")
            lines.append("")
        lines.append(f"## Risk Level: {self.risk_level}")

        # Role acceptance summary
        if self.roles:
            lines.append("")
            lines.append("## Acceptance Gates")
            for step in self.steps:
                if step.acceptance_criteria:
                    info = self.get_role_info(step.role) if step.role else {}
                    icon = info.get("icon", "👤")
                    label = info.get("label", step.role or step.name)
                    lines.append(f"- {icon} **{label}** → {step.name}: {step.acceptance_criteria}")

        return "\n".join(lines)

    def validate(self) -> tuple[bool, str]:
        """Validate that the pipeline is well-formed (no cycles, valid deps)."""
        if not self.steps:
            return False, "Pipeline has no steps"

        step_names = {s.name for s in self.steps}
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_names:
                    return False, f"Step '{step.name}' depends on unknown step '{dep}'"

        # Check for cycles via topological sort
        try:
            _topological_order(self.steps)
            return True, "Valid"
        except ValueError as e:
            return False, str(e)

    @property
    def is_metaskill(self) -> bool:
        return True


# ═══════════════════════════════════════════════════════════════
# Parser
# ═══════════════════════════════════════════════════════════════

def parse_metaskill(content: str) -> Optional[MetaSkill]:
    """Parse a MetaSkill Markdown document into a MetaSkill object."""
    # Check for meta marker
    if META_MARKER not in content[:200]:
        return None

    # Extract name from YAML frontmatter first, then heading
    name = "Unnamed MetaSkill"
    yaml_match = re.search(r'^---\s*\n.*?^name:\s*(.+?)\s*$', content, re.MULTILINE | re.DOTALL)
    if yaml_match:
        name = yaml_match.group(1).strip()
    else:
        name_match = re.search(r'^#\s*MetaSkill[：:]\s*(.+?)\s*$', content, re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip()

    # Extract goal
    goal = ""
    goal_match = re.search(r'##\s*Goal\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if goal_match:
        goal = goal_match.group(1).strip()

    # Extract pipeline
    steps: list[PipelineStep] = []
    pipeline_match = re.search(r'```pipeline\s*\n(.*?)```', content, re.DOTALL)
    if pipeline_match:
        for line in pipeline_match.group(1).strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            step = _parse_pipeline_line(line)
            if step:
                steps.append(step)

    # Extract tool whitelist
    tools: list[str] = []
    tools_match = re.search(r'##\s*Tool Whitelist\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if tools_match:
        for line in tools_match.group(1).strip().split("\n"):
            t = line.strip().lstrip("- ").strip()
            if t:
                tools.append(t)

    # Extract risk level
    risk = "low"
    risk_match = re.search(r'##\s*Risk Level[：:]\s*(.+?)\s*$', content, re.MULTILINE)
    if risk_match:
        risk = risk_match.group(1).strip().lower()

    return MetaSkill(
        name=name,
        goal=goal,
        steps=steps,
        tool_whitelist=tools,
        risk_level=risk,
        raw_content=content,
    )


def _parse_pipeline_line(line: str) -> Optional[PipelineStep]:
    """Parse a pipeline step line like:
    'fact_check: 事实核查  # depends_on: [] | output_key: fc_result'
    """
    # Split comment
    comment = ""
    if "#" in line:
        line, comment = line.split("#", 1)
        line = line.strip()

    parts = line.split(":", 1)
    if len(parts) != 2:
        return None

    name = parts[0].strip()
    skill_name = parts[1].strip()

    # Parse comment for metadata
    depends_on: list[str] = []
    output_key = ""
    allowed_tools: list[str] = []

    role = ""
    acceptance_criteria = ""
    handoff_to = ""

    if comment:
        for segment in comment.split("|"):
            segment = segment.strip()
            if segment.startswith("depends_on:"):
                deps_str = segment[len("depends_on:"):].strip()
                deps_str = deps_str.strip("[] ")
                if deps_str:
                    depends_on = [d.strip() for d in deps_str.split(",")]
            elif segment.startswith("output_key:"):
                output_key = segment[len("output_key:"):].strip()
            elif segment.startswith("tools:"):
                tools_str = segment[len("tools:"):].strip()
                tools_str = tools_str.strip("[] ")
                if tools_str:
                    allowed_tools = [t.strip() for t in tools_str.split(",")]
            elif segment.startswith("role:"):
                role = segment[len("role:"):].strip()
            elif segment.startswith("accept:"):
                acceptance_criteria = segment[len("accept:"):].strip()
            elif segment.startswith("handoff_to:"):
                handoff_to = segment[len("handoff_to:"):].strip()

    # Generate task template from skill name if not explicit
    task_template = f"Execute the [{skill_name}] skill for step [{name}]"
    if role:
        info = ROLE_TEMPLATES.get(role, {})
        role_label = info.get("label", role)
        task_template = f"As {role_label}, execute [{skill_name}] for step [{name}]"

    return PipelineStep(
        name=name,
        skill_name=skill_name,
        task_template=task_template,
        depends_on=depends_on,
        output_key=output_key,
        allowed_tools=allowed_tools,
        role=role,
        acceptance_criteria=acceptance_criteria,
        handoff_to=handoff_to,
    )


# ═══════════════════════════════════════════════════════════════
# Pipeline Engine
# ═══════════════════════════════════════════════════════════════

def _topological_order(steps: list[PipelineStep]) -> list[PipelineStep]:
    """Topological sort. Raises ValueError on cycle."""
    in_degree = {s.name: len(s.depends_on) for s in steps}
    for s in steps:
        for dep in s.depends_on:
            if dep not in in_degree:
                raise ValueError(f"Unknown dependency: {dep}")

    ordered = []
    queue = [s for s in steps if in_degree[s.name] == 0]

    while queue:
        node = queue.pop(0)
        ordered.append(node)
        for s in steps:
            if node.name in s.depends_on:
                in_degree[s.name] -= 1
                if in_degree[s.name] == 0:
                    queue.append(s)

    if len(ordered) != len(steps):
        raise ValueError("Pipeline contains a cycle")
    return ordered


@dataclass
class PipelineResult:
    """Result of executing a MetaSkill pipeline."""

    success: bool
    outputs: dict[str, str] = field(default_factory=dict)  # step_name → output
    errors: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)  # execution log


def run_pipeline(
    metaskill: MetaSkill,
    context: dict[str, Any] | None = None,
    *,
    llm_args: tuple | None = None,
) -> PipelineResult:
    """Execute a MetaSkill pipeline.

    Args:
        metaskill: The MetaSkill to execute.
        context: Initial context (user input, variables, etc.).
        llm_args: (api_key, base_url, model, chat_kwargs) for LLM calls.

    Returns:
        PipelineResult with outputs from each step.
    """
    valid, msg = metaskill.validate()
    if not valid:
        return PipelineResult(success=False, errors=[f"Validation failed: {msg}"])

    try:
        ordered = _topological_order(metaskill.steps)
    except ValueError as e:
        return PipelineResult(success=False, errors=[f"Topology error: {e}"])

    outputs: dict[str, str] = {}
    trace: list[str] = []

    ctx = context or {}
    _log.info("Running MetaSkill '%s' with %d steps", metaskill.name, len(ordered))

    for step in ordered:
        trace.append(f"→ {step.name} ({step.skill_name})")
        _log.info("MetaSkill step: %s → %s", step.name, step.skill_name)

        # Build task with context from dependencies
        task = step.task_template
        dep_context = ""
        for dep in step.depends_on:
            if dep in outputs:
                dep_context += f"\n\n[Output from '{dep}']:\n{outputs[dep][:1000]}"

        full_task = f"{task}\n{dep_context}"
        if ctx.get("user_input"):
            full_task += f"\n\n[User's original request]:\n{ctx['user_input']}"

        # Execute the skill
        try:
            result = _execute_skill_step(step.skill_name, full_task, llm_args, step.allowed_tools)
            outputs[step.name] = result
            trace.append(f"  ✓ {step.name} complete ({len(result)} chars)")
        except Exception as e:
            err_msg = f"Step '{step.name}' failed: {e}"
            _log.error(err_msg)
            outputs[step.name] = f"ERROR: {err_msg}"
            trace.append(f"  ✗ {err_msg}")
            if metaskill.risk_level == "high":
                # High risk: stop on first failure
                return PipelineResult(
                    success=False,
                    outputs=outputs,
                    errors=[err_msg],
                    trace=trace,
                )
            # Low/medium risk: continue with error

    return PipelineResult(success=True, outputs=outputs, trace=trace)


def _mermaid_node_id(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    return safe or "step"


def pipeline_to_mermaid(steps: list[PipelineStep]) -> str:
    """Render MetaSkill pipeline as Mermaid flowchart TD for portal DAG view."""
    if not steps:
        return "flowchart TD\n  empty([无步骤])"

    lines = ["flowchart TD"]
    id_map = {s.name: _mermaid_node_id(s.name) for s in steps}
    roots = [s for s in steps if not s.depends_on]

    if len(steps) > 1 and roots:
        lines.append("  start([开始])")

    for step in steps:
        nid = id_map[step.name]
        label = f"{step.name}: {step.skill_name}".replace('"', "'")
        lines.append(f'  {nid}["{label}"]')

    for step in steps:
        nid = id_map[step.name]
        if step.depends_on:
            for dep in step.depends_on:
                if dep in id_map:
                    lines.append(f"  {id_map[dep]} --> {nid}")
        elif len(steps) > 1:
            lines.append(f"  start --> {nid}")

    return "\n".join(lines)


def _execute_skill_step(
    skill_name: str,
    task: str,
    llm_args: tuple | None,
    allowed_tools: list[str],
) -> str:
    """Execute a single skill as part of a MetaSkill pipeline step."""
    from skillos.skills import skill_store

    # Check if skill exists
    if not skill_store.skill_exists(skill_name):
        return f"Skill '{skill_name}' not found. Available: {skill_store.list_skills()[:10]}"

    # Load and run the skill
    try:
        skill_doc = skill_store.get_skill_body(skill_store.load_skill(skill_name))
    except Exception as e:
        _log.warning("Non-critical in metaskill.py: %s", e)
        return f"Failed to load skill '{skill_name}'"

    # If we have LLM access, actually run the skill via the agent
    if llm_args:
        from skillos.skills import agent_factory
        try:
            agent = agent_factory.create_agent(skill_doc, task)
            result = agent_factory.run_agent(agent, task)
            return result or f"Skill '{skill_name}' returned empty result"
        except Exception as e:
            return f"Skill execution error: {e}"

    # No LLM: return the skill doc and task as context for manual execution
    return (
        f"[Skill '{skill_name}' loaded. Task: {task}]\n\n"
        f"Skill document:\n{skill_doc[:500]}"
    )


# ═══════════════════════════════════════════════════════════════
# MetaSkill Creator Prompt
# ═══════════════════════════════════════════════════════════════

CREATOR_SYSTEM_PROMPT = """你是 MetaSkill Creator。你的任务是把用户的自然语言需求，编排成一个多技能流水线（MetaSkill）。

## 你的能力
- 你可以查看所有可用的技能列表
- 你可以把多个技能串联成一条工作流
- 每个步骤可以依赖前面步骤的输出
- 你可以为每个步骤指定允许的工具

## 输出格式
生成一个 MetaSkill Markdown 文档：

```metaskill
---
type: metaskill
name: <技能名称>
---

# MetaSkill: <名称>

## Goal
<用户的目标，一句话>

## Pipeline
```pipeline
step_1_name: skill_name_for_step1  # output_key: result_1
step_2_name: skill_name_for_step2  # depends_on: [step_1_name] | output_key: result_2
...
```

## Tool Whitelist
- web_search
- read_file
...

## Risk Level: low
```

## 规则
1. 每个步骤必须使用已有的技能名
2. 步骤之间有依赖关系时，用 depends_on 标注
3. 只输出 metaskill 代码块，不要其他解释
4. 如果用户需求太模糊，先问清楚再生成
5. 步骤 3-7 个为宜，不要过多"""


def create_metaskill_prompt(
    user_goal: str,
    available_skills: list[str],
    context: str = "",
) -> str:
    """Build the prompt for MetaSkill creation."""
    skill_list = "\n".join(f"- {s}" for s in available_skills[:30])
    if len(available_skills) > 30:
        skill_list += f"\n- ... and {len(available_skills) - 30} more"

    ctx_block = f"\n## 对话上下文\n{context}\n" if context else ""

    return f"""{CREATOR_SYSTEM_PROMPT}

## 可用技能列表
{skill_list}

## 用户需求
{user_goal}
{ctx_block}
## 请生成 MetaSkill 流水线
```metaskill
...
```"""
