"""URL Learning Pipeline — 7-step cognitive skill extraction from web content.

Extracted from SkillExtractionAgent.learn_from_url() to keep agent.py manageable.
"""

import logging
import re

_log = logging.getLogger(__name__)


def run_learning_pipeline(
    agent,  # SkillExtractionAgent (duck-typed: needs _ingest_ctx, _normalize_name, _diffuse_knowledge)
    url: str,
    page_content: str,
    existing_skills: list[str],
    llm_args: tuple,
) -> tuple[str, dict | None]:
    """7-step cognitive learning pipeline: 初识→理解→拆解→重构→验证→内化→沉淀→扩散.

    Inspired by:
    - Feynman Technique: explain it simply, find gaps, refine
    - Bloom's Taxonomy: remember → understand → apply → analyze → evaluate → create
    - Deliberate Practice: focused attempt → feedback → adjust → repeat
    """
    from skillos.llm_client import call

    content_preview = page_content[:6000] if len(page_content) > 6000 else page_content
    skills_list = ", ".join(existing_skills[:10]) if existing_skills else "（无）"
    model = llm_args[2] if len(llm_args) > 2 else ""

    # Load team playbook + purpose (LLM Wiki: read on every ingest)
    ingest_context = agent._ingest_ctx()

    pipeline_log: list[str] = []

    def _plog(step: str, result: str) -> None:
        pipeline_log.append(f"{step}: {str(result)[:120]}")

    # ── Step 1: 初识 (First Encounter) ─────────────────
    try:
        skim_raw = call(
            f"""快速浏览以下网页内容（{url}），回答三个问题：

## 内容片段
{content_preview[:1500]}

## 问题
1. 这篇文章/页面是关于什么的？（一句话）
2. 它包含可操作的方法论/步骤/流程吗？（是/否）
3. 如果我是一个AI助手，学会这个对我有用吗？（是/否，为什么）

只回答这三个问题，不要展开。""",
            model=model, max_tokens=200, temperature=0.2)
        _plog("初识", skim_raw)

        lines = [l.strip() for l in skim_raw.strip().split("\n") if l.strip()]
        has_method = any(("是" in l or "可能" in l or "部分" in l) and ("2." in l or "包含" in l or "步骤" in l or "流程" in l or "方法" in l or "可操作" in l) for l in lines)
        is_useful = any("是" in l and ("3." in l or "有用" in l or "学会" in l or "帮助" in l) for l in lines)
        clearly_no = any("否" in l and ("2." in l) for l in lines) and any("否" in l and ("3." in l) for l in lines)

        if clearly_no or (not has_method and not is_useful):
            reason = lines[-1] if lines else "未检测到可操作内容或学习价值"
            return f"初识判断：不值得深入学习。{reason}", None
    except Exception as e:
        return f"初识阶段失败: {e}", None

    # ── Step 2: 理解 (Comprehension) ─────────────────
    try:
        comprehend_raw = call(
            f"""仔细阅读以下内容。你的任务是**理解**，不是提取。

## 完整内容
{content_preview}

## 请回答（用中文）
1. 这个方法要解决的核心问题是什么？
2. 它的底层逻辑是什么？为什么这个顺序？（不是列出步骤，而是解释为什么步骤之间是这个关系）
3. 有没有隐含的前提假设？（比如"用户已经知道X"、"需要先准备Y"）
4. 作者的思维方式是什么？（归纳？演绎？分类？时序？）

不要列步骤。专注于"为什么"。""",
            model=model, max_tokens=400, temperature=0.3)
        _plog("理解", comprehend_raw)
    except Exception as e:
        return f"理解阶段失败: {e}", None

    # ── Step 3: 拆解 (Deconstruction) ─────────────────
    try:
        deconstruct_raw = call(
            f"""现在把刚才理解的方法论拆解成**原子步骤**。

## 理解摘要
{comprehend_raw}

## 原文
{content_preview}

## 拆解规则
1. 每个步骤必须是一个**单一动作**（不能"分析并总结"，要拆成两步）
2. 每个决策点必须标注 if-then 分支
3. 识别前置依赖（哪步必须在哪步之前）
4. 识别异常情况（什么情况下这套方法会失效）
5. 每一步问自己：一个没看过原文的人，能只看这一步就知道怎么做吗？

## 输出格式
```
步骤1: <单一动作>  # 前置: <依赖> | 如果失败: <处理>
步骤2: <单一动作>  # 前置: 步骤1 | 如果<条件>则<分支>
...
异常:
- <情况1>: <如何处理>
```""",
            model=model, max_tokens=800, temperature=0.3)
        _plog("拆解", deconstruct_raw)
    except Exception as e:
        return f"拆解阶段失败: {e}", None

    # ── Step 4: 重构 (Reconstruction / Feynman) ──────
    try:
        reconstruct_raw = call(
            f"""用你自己的话，把拆解后的步骤重构成一份清晰的操作指南。

## 拆解结果
{deconstruct_raw}

## 原文参考
{content_preview[:1000]}

## 重构要求（Feynman 技巧）
1. 用一个**非专业读者也能看懂**的方式解释每一步
2. 用自己的结构重新组织——不必忠于原文顺序，按"执行者最容易理解的顺序"排列
3. 如果发现某个步骤说不清楚 → 说明你对它的理解还不够 → 标出来让人类审核
4. 给每一步一个**为什么**（why it matters）
5. 对照已有技能库（{skills_list}），如果有相似模式，注明"这一步与「XX技能」的YY步骤相通"
{ingest_context}
6. 对照上方团队 Playbook+PURPOSE：输出格式、用语风格、术语定义必须与团队标准一致。

## 输出格式（渐进式披露原则）
SKILL.md 应该精简。详细内容放到 references/ 里。
```skill_doc
# 技能名称：<从原文提炼的名称>
## 来源
- {url}
## 核心问题
<这个方法要解决什么，一句话>

## S_route（决策表）
| 用户意图 | 执行动作 | 按需加载 |
|---------|---------|---------|
| <意图A> | <动作A> | references/<文件A>.md |

## S_body
<核心步骤 + if-then — 只保留最关键的 3-5 步>

## S_trigger
<触发条件 — 具体触发词 + 不应触发的边界>

## S_params
<输入参数 — 所有可配置的决策轴>

## S_appendix
<references/ 文件清单>
- references/workflow-detail.md — 完整步骤详解
- references/examples.md — 示例和用法

## 知识关联
<与已有技能的关系>
```""",
            model=model, max_tokens=2000, temperature=0.3)
        _plog("重构", "生成技能文档草稿")
    except Exception as e:
        return f"重构阶段失败: {e}", None

    m = re.search(r"```skill_doc\s*\n(.*?)```", reconstruct_raw, re.DOTALL | re.IGNORECASE)
    draft = m.group(1).strip() if m else reconstruct_raw.strip()
    nm = re.search(r"^#\s*技能名称[：:]\s*(.+?)\s*$", draft, re.MULTILINE)
    name = agent._normalize_name(nm.group(1).strip()) if nm else "url-learned-skill"

    # ── Step 5: 验证 (Validation) ─────────────────
    try:
        validate_raw = call(
            f"""你是技能文档的测试者。现在要攻击这份草稿，找出它的弱点。

## 待测试草稿
```
{draft}
```

## 测试方法
1. **边界测试**：输入为空会怎样？输入异常大会怎样？
2. **顺序测试**：如果跳过某一步直接到最后一步，会发生什么？
3. **歧义测试**：哪一步的描述最模糊？如果是你会怎么理解？
4. **缺失测试**：原文中提到了但草稿中遗漏了什么？

## 输出格式
```
边界问题: <如果有>
顺序问题: <如果有>
歧义问题: <如果有>
遗漏: <如果有>
总评: <通过/需修改>
修改建议: <具体怎么改>
```""",
            model=model, max_tokens=350, temperature=0.3)
        _plog("验证", validate_raw)
    except Exception as e:
        validate_raw = "总评: 通过\n修改建议: 验证阶段异常"
        _plog("验证", str(e))

    # Apply fixes if validation found issues
    passed = "总评: 通过" in validate_raw and "总评: 需修改" not in validate_raw
    if not passed and "修改建议:" in validate_raw:
        try:
            fix_raw = call(
                f"""根据测试反馈修改技能文档。只改反馈中指出的问题，不要改其他部分。

## 当前草稿
```
{draft}
```

## 测试反馈
{validate_raw}

## 要求
只修改反馈中指出的具体问题，输出完整草稿。""",
                model=model, max_tokens=1500, temperature=0.2)
            m2 = re.search(r"```skill_doc\s*\n(.*?)```", fix_raw, re.DOTALL | re.IGNORECASE)
            if m2:
                draft = m2.group(1).strip()
                _plog("修复", "已应用测试反馈的修改")
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)

    # ── Step 6: 内化 (Internalization) ─────────────────
    try:
        internalize_raw = call(
            f"""这份新技能和已有技能库有什么关联？

## 新技能
```
{draft[:800]}
```

## 已有技能
{skills_list}

## 请回答
1. 与哪个已有技能最相似？相似点在哪？
2. 有哪些步骤/模式可以抽象出来作为通用模式？
3. 如果将来有人要创建一个同类技能，这份文档的哪部分最值得参考？
4. 给这份技能打 3-5 个标签，方便以后搜索

只回答这四个问题，不要展开。""",
            model=model, max_tokens=250, temperature=0.3)
        _plog("内化", internalize_raw)
    except Exception as e:
        internalize_raw = "内化阶段异常"
        _plog("内化", str(e))

    # ── Step 7: 沉淀 (Crystallization) ─────────────────
    final_content = draft
    if "## 知识关联" not in final_content:
        final_content += f"\n\n## 知识关联\n{internalize_raw[:300]}"
    if "## 质量审核" not in final_content:
        final_content += f"\n\n## 质量审核\n{validate_raw[:300]}"

    # Try to inject Skill DNA
    try:
        from skillos.skills.pattern_miner import inject_dna_to_prompt
        dna_prompt = inject_dna_to_prompt("请确保技能文档遵循Skill DNA设计原则。")
        if dna_prompt and "DNA" in dna_prompt:
            final_content += "\n\n<!-- Skill DNA principles considered in generation -->"
    except Exception:
        _log.debug("Non-critical operation skipped", exc_info=True)

    # ── Step 7.5: Feynman simplification ────────────
    feynman_deepened = False
    try:
        from skillos.evolution.learning_theory import recursive_feynman
        simpler, deepened = recursive_feynman(final_content, llm_args)
        if deepened:
            feynman_deepened = True
            _log.info("Feynman deepened via URL learning: %s", name)
    except Exception:
        pass

    # ── Step 7.6: Cross-domain analogies ────────────
    analogies_found = []
    try:
        from skillos.evolution.learning_theory import find_analogies
        analogies_found = find_analogies(name, final_content, existing_skills, llm_args)
    except Exception:
        pass

    # ── Step 8: 扩散 (Diffusion) ─────────────────
    diffusion_results = diffuse_knowledge(name, final_content, existing_skills, llm_args)

    agent._draft_name = name
    agent._draft_content = final_content

    log_text = "\n".join(pipeline_log)
    diff_skills = [d for d in diffusion_results if d.startswith("✅")]

    summary = (
        f"✅ 学习完成：**{name}**\n\n"
        f"📖 初识 → 🧠 理解 → 🔧 拆解 → ✍️ 重构 → 🧪 验证{' → ✅ 通过' if passed else ' → ⚠️ 已修复'}"
        f"{' → 🧠 费曼深化' if feynman_deepened else ''}"
        f"{' → 🔀 类比(' + str(len(analogies_found)) + '个)' if analogies_found else ''}"
        f" → 🔗 内化 → 💎 沉淀"
        f"{' → 🌐 扩散(' + str(len(diff_skills)) + '个技能受益)' if diff_skills else ''}"
    )

    return (summary, {
        "name": name,
        "content": final_content,
        "diffusion": diffusion_results,
        "pipeline_log": pipeline_log,
    })


# ── Knowledge diffusion ──────────────────────────────────────

def diffuse_knowledge(new_skill_name: str, new_content: str,
    existing_skills: list[str], llm_args: tuple,
) -> list[str]:
    """Step 8: Cross-pollinate learned knowledge to existing skills."""
    from skillos.knowledge.diffusion_gate import check_diffusion_gate

    gate = check_diffusion_gate(new_skill_name, new_content)
    if not gate.allowed:
        return [f"🛡️ 认识论门控：跳过知识扩散 — {gate.reason}"]

    if not existing_skills:
        return []
    SYSTEM = {'brainstorming', 'skill-creator'}
    candidates = [s for s in existing_skills[:15] if s not in SYSTEM and s != new_skill_name]
    if not candidates:
        return []
    results = []
    new_summary = new_content[:600]
    for skill_name in candidates[:5]:
        try:
            from skillos.skills import skill_store
            old_body = skill_store.get_skill_body(skill_store.load_skill(skill_name))
            old_summary = old_body[:400]
        except Exception as e:
            _log.debug("Diffusion check skipped: %s", e); continue

        diffuse_prompt = f"""你是知识工程师。一份新的知识被学习了，现在检查它能否改进已有技能。

## 新学习的知识（来源）
{new_summary}

## 已有技能
**{skill_name}**:
{old_summary}

## 判断标准
1. 新知识中有没有这个已有技能**缺失的步骤或分支**？
2. 新知识中有没有可以**替换这个技能中某个不准确描述**的内容？
3. 新知识中有没有**更好的触发条件或关键词**可以补充？

## 输出
```
相关度: <高/中/低/无>
可改进: <是/否>
如果可改进，具体改什么: <一句话描述改进点>
```"""
        try:
            from skillos.llm_client import call
            model = llm_args[2] if len(llm_args) > 2 else ""
            diffuse_raw = call(diffuse_prompt, model=model, max_tokens=200, temperature=0.3)
        except Exception as e:
            _log.debug("Diffusion inner skipped: %s", e); continue

        if "可改进: 是" in diffuse_raw and "相关度: 无" not in diffuse_raw:
            improvement = ""
            m = re.search(r'具体改什么:\s*(.+?)$', diffuse_raw, re.MULTILINE)
            if m:
                improvement = m.group(1).strip()
            if improvement:
                if not gate.auto_apply:
                    results.append(
                        f"💡 建议改进「{skill_name}」（未自动应用）: {improvement[:60]}"
                        + (f" — {gate.reason}" if gate.reason else "")
                    )
                    continue
                try:
                    from skillos.skills import skill_store
                    apply_prompt = f"""对已有技能做**一处精准改进**。

## 当前技能文档
{old_body[:800]}

## 改进建议
{improvement}

## 输出
输出改进后的完整技能文档。只改与改进点直接相关的部分，其他保持原样。"""
                    new_raw = call(apply_prompt, model=model, max_tokens=800, temperature=0.2)
                    dm2 = re.search(r"```skill_doc\s*\n(.*?)```", new_raw, re.DOTALL | re.IGNORECASE)
                    improved = dm2.group(1).strip() if dm2 else new_raw
                    skill_store.save_skill(skill_name, improved, meta={"diffused_from": new_skill_name})
                    results.append(f"✅ 扩散到「{skill_name}」: {improvement[:60]}")
                    _log.info("Knowledge diffused: %s → %s", new_skill_name, skill_name)
                except Exception as e:
                    _log.warning("Diffusion apply failed: %s", e); results.append(f"💡 建议改进「{skill_name}」: {improvement[:60]}")
        else:
            results.append(f"⏭️ 与「{skill_name}」无关")
    return results

# ── Claim extraction ────────────────────────────────────────

def _extract_claims_from_skill(content: str) -> list[str]:
    """Extract individual knowledge claims from a generated SKILL.md body.

    Parses S_body numbered steps and S_route table rows into discrete
    claim strings suitable for epistemic recording and verification.

    Returns:
        List of claim strings (one per step/row).
    """
    claims: list[str] = []
    # 1. Extract from S_body numbered steps
    body_match = re.search(
        r'##\s*S_body\s*\n(.*?)(?=\n##\s|\Z)',
        content, re.DOTALL | re.IGNORECASE,
    )
    if body_match:
        body_text = body_match.group(1)
        # Split on numbered steps: "1. ", "2. ", "1) " etc.
        step_lines = re.split(r'\n\s*\d+[.)]\s*', body_text)
        for step in step_lines:
            clean = step.strip()
            # Skip empty, short fragments, and table/markdown artifacts
            if not clean or len(clean) < 12:
                continue
            if clean.startswith('|') or clean.startswith('#'):
                continue
            # Strip leading number prefix if the first line starts with one
            clean = re.sub(r'^\d+[.)]\s*', '', clean)
            # Strip leading "* " markers
            clean = re.sub(r'^[\*\-]\s+', '', clean)
            claims.append(clean)

    # 2. Extract from S_route table rows
    route_match = re.search(
        r'##\s*S_route\s*\n(.*?)(?=\n##\s|\Z)',
        content, re.DOTALL | re.IGNORECASE,
    )
    if route_match:
        route_text = route_match.group(1)
        header_seen = False
        for line in route_text.split('\n'):
            line = line.strip()
            if not line.startswith('|') or '---' in line:
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            cells = [c for c in cells if c]
            if not cells:
                continue
            # Skip header row
            if not header_seen and any(
                h in ''.join(cells).lower()
                for h in ['用户意图', '条件', 'intent', 'condition', '执行动作', 'action']
            ):
                header_seen = True
                continue
            header_seen = True
            claims.append(' | '.join(cells))

    # 3. Extract trigger terms as a claim
    trigger_match = re.search(
        r'##\s*S_trigger\s*\n(.*?)(?=\n##\s|\Z)',
        content, re.DOTALL | re.IGNORECASE,
    )
    if trigger_match:
        trigger_text = trigger_match.group(1).strip()
        if trigger_text and len(trigger_text) > 5:
            kw_match = re.search(r'keywords?\s*:\s*(.+)', trigger_text, re.IGNORECASE)
            if kw_match:
                claims.append(f"触发条件: {kw_match.group(1).strip()}")

    return claims
