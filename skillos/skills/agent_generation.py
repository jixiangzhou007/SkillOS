"""Skill generation pipeline — extracted from SkillExtractionAgent._generate().

Produces AgentSkills.io standard SKILL.md with YAML frontmatter, quality
self-check, epistemology recording, and resource flushing.
"""

import logging
import re

_log = logging.getLogger(__name__)


def run_skill_generation(
    agent,  # SkillExtractionAgent (duck-typed)
    existing_skills: list[str],
    llm_args: tuple,
) -> tuple[str, dict | None]:
    """Generate final installable SKILL.md (AgentSkills.io standard)."""
    from skillos.skills.portable_skill import finalize_portable_skill, load_portable_spec

    agent._phase = agent.Phase.GENERATING if hasattr(agent, 'Phase') else 4  # GENERATING=4
    context_text = agent._generation_context()
    skills_str = ", ".join(existing_skills[:8]) if existing_skills else "暂无"
    model = llm_args[2] if len(llm_args) > 2 else ""
    portable_spec = load_portable_spec()

    try:
        from skillos.skills.pattern_miner import ensure_bootstrap_skill_dna
        ensure_bootstrap_skill_dna()
    except Exception:
        _log.debug("Bootstrap DNA skipped", exc_info=True)

    dna_unified = ""
    dna_tpl_competition = ""
    try:
        from skillos.knowledge.dna_context import build_dna_context, build_domain_template_context
        dna_unified = build_dna_context(agent._goal, context_text[:2500])
        dna_tpl_competition = build_domain_template_context(agent._goal, context_text[:2000])
    except Exception:
        _log.debug("DNA context build skipped", exc_info=True)

    base_prompt = f"""你是技能创作助手。用户通过对话描述了一个工作流程，不懂什么是 Skill。
你的任务：生成一份**可直接安装到 Cursor、Claude Code、Trae** 的 SKILL.md 正文。

## 技能目标
{agent._goal[:300]}

## 对话记录（只使用其中明确提到的内容）
{context_text}

## 已有技能（交叉参考，勿抄袭）
{skills_str}

{portable_spec}
"""
    if dna_unified:
        base_prompt += f"\n## 🧬 哲学与领域 DNA（必须体现在 S_route / S_body 结构中）\n{dna_unified}\n"
    if dna_tpl_competition:
        base_prompt += f"\n## 🏗️ 领域模板竞争结果\n{dna_tpl_competition}\n"

    base_prompt += """
## 输出格式
```skill_doc
tool_name: <英文 kebab-case，如 contract-review，仅小写字母数字连字符>
tool_description: <第三人称描述：做什么 + 何时触发 + 触发词，一句话>

# 技能名称：<中文简称 2-6 字>
## 核心问题
<一句话：这个流程解决什么问题>

## S_body
1. <可执行步骤，含 if-then 分支>
2. ...

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| ... | ... | ... |

## S_trigger
- keywords: <触发词，逗号分隔>
- context: <什么场景下使用>
- excludes: <什么情况下不要用这个技能>

## S_params
- <参数名>: <类型，默认值，说明>
```

## 硬性要求
1. 步骤必须可落地执行，禁止空泛描述
2. **必须包含 `## S_body` 章节**（不要用 Instructions 代替；步骤写在 S_body 内）
3. S_route 至少 2 行；可用 S_trigger 或 When to use 描述触发条件
4. 未在对话中出现的细节标 [待确认]，禁止编造
5. tool_name 必须是合法 kebab-case（a-z0-9-）
6. tool_description 用第三人称（不用「我/你」）
7. 只输出 skill_doc 代码块

## 常见错误（生成前自查，skill-creator 总结）
| 错误 | 后果 | 正确做法 |
|------|------|---------|
| SKILL.md 塞太多内容（>3000字） | token 浪费，关键信息被稀释 | 核心步骤放 S_body，详细说明和示例放 references/ |
| 没有 S_route 决策表 | AI 不知道 references/ 下有文件可用 | 至少 2 行，每个分支对应一个 references/ 文件 |
| description 太模糊（"帮助处理X"） | Skill 不触发或误触发 | 第三人称 + 具体触发词 + 不触发的边界 |
| 引用不存在的 references/ 文件 | Agent 执行时报错 | 所有文件路径引用必须在 skill 目录下存在 |
| 步骤没有区分 [动作] 和 [门禁] | AI 可能跳过关键检查 | 需要验证的步骤标注 [门禁]，失败→中止或升级 |
| trigger keywords 太少（<3个） | skill 不被触发（undertrigger） | 中英文混合，至少 3 个，覆盖正式/口语/简写 |"""

    # Inject DNA principles
    try:
        from skillos.skills.pattern_miner import inject_dna_to_prompt
        prompt = inject_dna_to_prompt(base_prompt)
    except Exception as e:
        _log.warning("DNA injection failed: %s", e); prompt = base_prompt

    # Append playbook + purpose context
    try:
        ingest_ctx = agent._ingest_ctx()
        if ingest_ctx:
            prompt += f"\n{ingest_ctx}\n"
    except Exception:
        _log.debug("Non-critical operation skipped", exc_info=True)

    # Append domain authoritative references (laws, standards, guidelines)
    try:
        from skillos.knowledge.taxonomy import detect_domain
        from skillos.knowledge.domain_reference_registry import build_reference_context
        domain = detect_domain(agent._goal)
        if domain:
            ref_ctx = build_reference_context(domain.key)
            if ref_ctx:
                prompt += f"\n{ref_ctx}\n"
    except Exception:
        _log.debug("Domain reference injection skipped", exc_info=True)

    if agent._domain_template_id:
        try:
            from skillos.skills.domain_templates import get_generation_boost
            boost = get_generation_boost(agent._domain_template_id)
            if boost:
                prompt += (
                    "\n\n## 领域骨架模板（在对话事实基础上填充，勿删除 S_route/S_params 结构）\n"
                    f"{boost}\n"
                )
            secondary_ids = [
                tid for tid in agent._domain_template_ids
                if tid and tid != agent._domain_template_id
            ][:2]
            if secondary_ids:
                sec_lines = []
                for tid in secondary_ids:
                    sec_boost = get_generation_boost(tid)
                    if sec_boost:
                        sec_lines.append(f"### 次要继承 {tid}\n{sec_boost[:600]}…")
                if sec_lines:
                    prompt += (
                        "\n\n## 次要领域模板（仅参考，勿与主模板 S_route 混写）\n"
                        + "\n".join(sec_lines)
                    )
        except Exception:
            pass

    # Quality precheck
    try:
        agent._sync_probes_from_context()
        precheck = agent._optimize(existing_skills, llm_args)
        prompt += f"\n\n## 生成前质量预检（请尽量覆盖未达标项）\n{precheck}\n"
    except Exception:
        _log.debug("Precheck skipped", exc_info=True)

    locked_display = agent._resolve_skill_name()
    prompt += f"\n8. 技能中文名称必须固定为「{locked_display}」（不要用其他名称）\n"

    try:
        from skillos.llm_client import call
        raw = call(prompt, model=model, max_tokens=2500, temperature=0.3)
        m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        content = m.group(1).strip() if m else raw.strip()

        nm = re.search(r"^#\s*技能名称[：:]\s*(.+?)\s*$", content, re.MULTILINE)
        extracted = nm.group(1).strip() if nm else ""
        name = agent._resolve_skill_name(extracted or agent._draft_name or agent._goal)

        if "S_route" not in content:
            content = agent._ensure_s_route(content, llm_args)

        try:
            from skillos.skills.skill_structure import normalize_skill_body
            content = normalize_skill_body(content)
        except Exception:
            _log.debug("normalize_skill_body skipped", exc_info=True)

        content = agent._apply_dna_compliance_fix(content, llm_args)

        finalized = finalize_portable_skill(name, content)
        name = agent._resolve_skill_name(finalized["name"])
        content = finalized["body"]

        from skillos.skills.portable_skill import to_agent_skills_format
        standard_content = to_agent_skills_format(name, content,
            metadata={"skillos_version": "0.3.0"})

        agent._skill_dir = str(finalized["slug"])
        agent._flush_pending_resources()

        agent._draft_name = name
        agent._draft_content = standard_content
        agent._locked_name = name
        agent._clear_session_draft()

        # Feynman simplification
        try:
            from skillos.evolution.learning_theory import recursive_feynman
            simpler, deepened = recursive_feynman(content, llm_args)
            if deepened:
                _log.info("Feynman deepened: %s", name)
        except Exception:
            _log.debug("recursive_feynman skipped", exc_info=True)

        # Cross-domain analogies
        try:
            from skillos.evolution.learning_theory import find_analogies
            analogies = find_analogies(name, content, existing_skills, llm_args)
            if analogies:
                analogy_names = [a.get("skill","?") for a in analogies[:3]]
                _log.info("Analogies found for %s: %s", name, analogy_names)
        except Exception:
            _log.debug("find_analogies skipped", exc_info=True)

        # Knowledge diffusion
        diffusion_msg = ""
        try:
            diffusion_results = agent._diffuse_knowledge(name, content, existing_skills, llm_args)
            if diffusion_results:
                highlights = [r for r in diffusion_results if r.startswith("✅")]
                if highlights:
                    diffusion_msg = "\n\n### 🔄 知识扩散\n" + "\n".join(highlights[:3])
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)

        # Epistemic claim recording
        try:
            from skillos.knowledge.epistemology import record_claim
            for claim_text in agent._extract_claims_from_skill(content):
                record_claim(
                    content=claim_text,
                    source=f"skill_extraction:{name}",
                    source_type="llm_generated",
                    skill_name=name,
                )
            _log.info("Recorded claims from skill '%s'", name)
        except Exception:
            _log.debug("Epistemic claim recording skipped", exc_info=True)

        # Post-generation quality check
        quality_issues = agent._post_generation_check(name, content, finalized)
        quality_msg = ""
        if quality_issues:
            quality_msg = "\n\n### ⚠️ 质量建议\n" + "\n".join(
                f"- {i}" for i in quality_issues
            ) + "\n\n💡 回复「修复」我来帮你逐一处理。"
        else:
            quality_msg = (
                "\n\n---\n"
                "💡 质量检查通过！接下来可以：\n"
                "- 回复「**测试**」跑 4 个测试用例，看技能表现如何\n"
                "- 回复「**优化描述**」改进触发精确度（20 queries + 迭代优化）"
            )

        agent._phase = getattr(agent, 'Phase', type('',(),{'DONE':5})()).DONE or 5
        agent._finalized_name = name
        agent._awaiting_confirm = False
        doc = {
            "name": name,
            "slug": finalized["slug"],
            "description": finalized["description"],
            "content": standard_content,
            "body": content,
            "format": "agentskills.io/1.0",
            "install_paths": finalized["install_paths"],
            "dir_structure": {
                "root": finalized["slug"],
                "scripts": f"{finalized['slug']}/scripts/",
                "references": f"{finalized['slug']}/references/",
                "assets": f"{finalized['slug']}/assets/",
            },
        }
        return (
            f"✅ 已为你生成可安装的技能「**{name}**」！\n\n"
            f"```skill_doc\n{standard_content}\n```\n\n"
            f"这是 AgentSkills.io 标准格式，兼容 Claude Code / Cursor / Codex / Gemini CLI 等 30+ 平台。"
            f"{diffusion_msg}"
            f"{quality_msg}",
            doc,
        )
    except Exception as e:
        _log.error("Generation failed: %s", e)
        return f"生成失败: {e}", None
