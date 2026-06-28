"""Agent extraction data — constants, standalone helpers, and Phase enum.

Extracted from agent.py to break circular imports and reduce file size.
"""

import re
from enum import Enum, auto

URL_RE = re.compile(r'https?://[^\s，。！？、；：""''《》<>]+')

SKILL_START = ["技能", "skill", "工作流", "流程", "沉淀", "创建skill", "新建技能",
               "总结", "整理成", "提炼", "萃取", "写下来", "记下来", "帮我创建", "帮我写", "帮我整理"]
SKILL_EXIT = ["不做了", "取消", "算了", "不用了", "跳过全部", "换个话题", "聊别的"]

# ── Static examples shown in start() when topic is unknown ──
_EXAMPLES = [
    ("合同审核流程", "接收→条款检查→风险标记→修订→确认"),
    ("代码审查规范", "PR提交→静态检查→人工审查→合并"),
    ("数据报表生成", "数据获取→清洗→分析→可视化→交付"),
    ("故障排查流程", "告警接收→分级→定位→修复→复盘"),
]

# Domain-aware first-turn hints (keyword groups → natural storytelling invitation)
_DOMAIN_OPENINGS: list[tuple[tuple[str, ...], str]] = [
    (
        ("合同审核", "合同审查", "审合同", "合同合规", "合同", "协议", "条款", "法务", "合规"),
        "收到一份采购合同后，从初审到出具意见，你的标准流程是什么？请按步骤描述——触发条件、检查点、常见风险条款。",
    ),
    (
        ("投诉", "退款", "售后", "客服", "工单"),
        "处理一个客户投诉或退款请求，你通常经过哪些环节？从接收问题到最终解决，每一步的决策依据是什么？",
    ),
    (
        ("代码", "审查", "PR", "发布", "CI", "测试"),
        "进行一次代码审查时，你的检查清单是什么？先看什么，后看什么，什么情况下需要驳回？",
    ),
    (
        ("报销", "审批", "发票", "财务", "对账"),
        "你们公司的报销审批链路是怎样的？从提交到到账，经过哪些节点？有哪些容易卡住的环节？",
    ),
    (
        ("报表", "数据分析", "指标", "可视化"),
        "制作一份数据报表，从取数到交付，你的标准流程是什么？有哪些质量检查点？",
    ),
]


def _research_topic(topic: str, existing_skills: list[str] | None = None) -> str:
    """Search for industry best practices before starting extraction.

    Multi-source research:
    1. Web search for best practices
    2. GitHub AgentSkills libraries (community skills)
    3. Existing local skills (same domain)
    4. Precipitated knowledge (verified claims + knowledge graph + deep-digested patterns)

    Returns condensed research findings. Standalone function.
    """
    if not topic:
        return ""
    import re
    research_parts: list[str] = []

    # 1. Web search for best practices
    try:
        from skillos.utils.web_search import search
        q = f"{topic[:40]} 最佳实践 方法论 流程 步骤"
        raw = search(q, 2)
        if raw and "No results" not in raw:
            research_parts.append(f"### 网络搜索\n{raw[:400]}")
    except Exception:
        pass

    # 2. GitHub AgentSkills library search — community-curated skills
    try:
        from skillos.utils.web_search import search
        gh_q = f"site:github.com agentskills.io SKILL.md {topic[:30]}"
        gh_raw = search(gh_q, 2)
        if gh_raw and "No results" not in gh_raw:
            # Extract repo names from search results
            repos = re.findall(r'github\.com/([\w.-]+/[\w.-]+)', gh_raw)
            if repos:
                research_parts.append(f"### GitHub 社区技能库\n{', '.join(list(dict.fromkeys(repos))[:5])}")
    except Exception:
        pass

    # 3. Local existing skills
    try:
        from skillos.skills.skill_store import list_skills
        existing = existing_skills or list_skills()
        goal_words = set(re.findall(r'[\w一-鿿]{2,}', topic))
        related = []
        for sk in existing[:30]:
            sk_words = set(re.findall(r'[\w一-鿿]{2,}', sk))
            if len(goal_words & sk_words) >= 2 and sk not in ('brainstorming', 'skill-creator'):
                related.append(sk)
        if related:
            research_parts.append(f"### 本地已有技能\n{', '.join(related[:5])}")
    except Exception:
        pass

    # 4. Precipitated knowledge — verified claims from past extractions
    try:
        knowledge_parts = []
        # 4a. Verified knowledge claims on this topic
        from skillos.knowledge.epistemology import get_store
        store = get_store()
        verified = [c for c in store.get_knowledge() if any(
            kw in c.content for kw in re.findall(r'[\w一-鿿]{2,}', topic)
        )]
        if verified:
            knowledge_parts.append(
                "**已验证知识**（来自历史沉淀）：\n" +
                "\n".join(f"- {c.content[:120]}" for c in verified[:5])
            )
        # 4b. Knowledge graph — related nodes
        try:
            from skillos.knowledge.graph import get_graph
            g = get_graph()
            for _nid, node in list(g.nodes.items())[:50]:
                if any(kw in node.name for kw in re.findall(r'[\w一-鿿]{2,}', topic)):
                    knowledge_parts.append(f"📊 知识图谱节点: {node.name}")
        except Exception:
            pass
        # 4c. Deep-digested patterns from knowledge packages
        try:
            from skillos.knowledge.deep_digest import SKILLS_DIR
            for digest_dir in sorted(SKILLS_DIR.glob("*/patterns.md")):
                try:
                    pat_content = digest_dir.read_text(encoding="utf-8")[:1000]
                    if any(kw in pat_content for kw in re.findall(r'[\w一-鿿]{2,}', topic)):
                        name = digest_dir.parent.name
                        # Extract pattern names
                        patterns = re.findall(r'^## (.+)$', pat_content, re.MULTILINE)
                        if patterns:
                            knowledge_parts.append(f"📖 知识包「{name}」模式: {', '.join(patterns[:5])}")
                except Exception:
                    pass
        except Exception:
            pass
        if knowledge_parts:
            research_parts.append("### 🧠 历史沉淀知识\n" + "\n".join(knowledge_parts))
    except Exception:
        pass

    # 5–6. Unified DNA context (domain + philosophical methodology)
    try:
        from skillos.knowledge.dna_context import build_dna_context, build_domain_template_context
        dna_ctx = build_dna_context(topic)
        if dna_ctx:
            research_parts.append(dna_ctx)
        tpl_ctx = build_domain_template_context(topic)
        if tpl_ctx:
            research_parts.append(tpl_ctx)
    except Exception:
        pass

    return "\n\n".join(research_parts) if research_parts else ""


def _build_taxonomy_hint(topic: str) -> str:
    """Compact domain + methodology hint for explore/refine prompts."""
    try:
        from skillos.knowledge.dna_context import build_dna_hint
        return build_dna_hint(topic)
    except Exception:
        return ""


def _domain_opening_for_topic(topic: str) -> str:
    """First-turn reply tailored to the extracted topic (no generic template picker)."""
    for keywords, body in _DOMAIN_OPENINGS:
        if any(kw in topic for kw in keywords):
            return body
    try:
        from skillos.intelligence.role_templates import ROLE_TEMPLATES

        best, best_score = None, 0.0
        for role in ROLE_TEMPLATES:
            score = sum(1.5 for kw in role.keywords if kw in topic)
            if score > best_score:
                best_score = score
                best = role
        if best and best_score >= 1.5:
            return (
                f"听起来和 **{best.title}** 场景相关（{best.description}）。\n\n"
                f"请描述「{topic}」的 **触发场景**、**主要步骤** 和 **交付结果**。"
            )
    except Exception:
        pass
    return (
        f"你平时做「{topic}」的时候，是怎么一步步搞定的？不用列提纲，就当跟朋友聊天——随便说说都行。"
    )


class Phase(Enum):
    IDLE = auto()
    EXPLORING = auto()
    REFINING = auto()
    OPTIMIZING = auto()
    METASKILL = auto()
    CONFIRMING = auto()
    GENERATING = auto()
    DONE = auto()
