"""Skill Extraction Agent — the 7-step cognitive learning pipeline.

Ported from Skill Distiller's skill_agent.py. Core innovation:
  Human-inspired learning: 初识→理解→拆解→重构→验证→内化→沉淀→扩散

This is the heart of SkillOS's competitive advantage over raw Hermes skills.
Hermes creates skills from execution traces; SkillOS creates skills by
deeply understanding domain knowledge.
"""

import json
import logging
import re
from enum import Enum, auto
from typing import Optional

_log = logging.getLogger(__name__)

URL_RE = re.compile(r'https?://[^\s，。！？、；：""''《》<>]+')

SKILL_START = ["技能", "skill", "工作流", "流程", "沉淀", "创建skill", "新建技能",
               "总结", "整理成", "提炼", "萃取", "写下来", "记下来", "帮我创建", "帮我写", "帮我整理"]
SKILL_EXIT = ["不做了", "取消", "算了", "不用了", "跳过全部", "换个话题", "聊别的"]

# ── Static examples shown in start() when topic is unknown ──
_EXAMPLES = [
    ("处理客户投诉", "投诉接收→分类→升级→解决→回访"),
    ("代码审查流程", "PR提交→静态检查→人工审查→合并"),
    ("数据分析报告", "数据获取→清洗→分析→可视化→出报告"),
    ("API接口设计", "需求分析→接口定义→文档→联调→上线"),
]

# Domain-aware first-turn hints (keyword groups → natural storytelling invitation)
_DOMAIN_OPENINGS: list[tuple[tuple[str, ...], str]] = [
    (
        ("合同审核", "合同审查", "审合同", "合同合规", "合同", "协议", "条款", "法务", "合规"),
        "上次同事找你审合同，从收到合同到给出意见，你是怎么一步一步帮他搞定的？随便聊聊就行，不用列提纲。",
    ),
    (
        ("投诉", "退款", "售后", "客服", "工单"),
        "你碰到过最头疼的一个客户投诉或退款，是怎么处理的？从接到问题到最后解决，中间都发生了什么？",
    ),
    (
        ("代码", "审查", "PR", "发布", "CI", "测试"),
        "你最近一次做代码审查，打开那个PR之后，你第一眼看什么？然后一步步怎么查的？",
    ),
    (
        ("报销", "审批", "发票", "财务", "对账"),
        "你们公司的报销审批，从员工填单子到钱到账，中间经过哪些人、哪些环节？有没有碰到过特别麻烦的单子？",
    ),
    (
        ("报表", "数据分析", "指标", "可视化"),
        "你每周出的那个数据报表，从拿到数据到发给老板，中间都做了什么？有没有哪次数据特别难处理？",
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
        from skillos.skills import skill_store
        existing = existing_skills or skill_store.list_skills()
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
            for nid, node in list(g.nodes.items())[:50]:
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

# ── Probe order for progressive exploration ──
_PROBE_ORDER = ["trigger", "input", "steps", "output", "edge_cases"]

_PROBE_DESCRIPTIONS = {
    "trigger": "触发场景（何时/什么条件下触发这个流程）",
    "input": "输入/前置条件（需要什么输入或前置条件）",
    "steps": "执行步骤（具体怎么做，分几步）",
    "output": "输出/产出（流程的产出物是什么格式）",
    "edge_cases": "边界情况（特殊情况、异常怎么处理）",
}


class Phase(Enum):
    IDLE = auto()
    EXPLORING = auto()
    REFINING = auto()
    OPTIMIZING = auto()
    METASKILL = auto()
    CONFIRMING = auto()
    GENERATING = auto()
    DONE = auto()


class SkillExtractionAgent:
    """Consultative skill extraction agent — Socratic, not form-based."""

    def __init__(self):
        self._phase = Phase.IDLE
        self._turn = 0
        self._goal = ""
        self._context: list[str] = []
        self._name = ""
        self._research_done = False
        self._draft_name = ""
        self._draft_content = ""
        self._team_context: dict[str, str] = {}
        # New fields for progressive exploration
        self._probes_completed: set[str] = set()
        self._refinement_rounds: int = 0
        self._research_cache: str = ""  # Industry best practices for the current topic
        self._finalized_name: str = ""
        self._awaiting_confirm: bool = False
        self._locked_name: str = ""
        self._domain_template_id: str = ""
        self._domain_template_ids: list[str] = []

    def set_team_context(
        self,
        *,
        channel: str = "",
        chat_id: str = "",
        user_id: str = "",
        session_id: str = "",
    ) -> None:
        """Attach IM/session metadata for Playbook binding and lineage (Phase 5)."""
        if channel:
            self._team_context["channel"] = channel
        if chat_id:
            self._team_context["chat_id"] = chat_id
        if user_id:
            self._team_context["user_id"] = user_id
        if session_id:
            self._team_context["session_id"] = session_id

    def _ingest_ctx(self) -> str:
        try:
            from skillos.knowledge.knowledge_context import get_ingest_context
            return get_ingest_context(
                chat_id=self._team_context.get("chat_id", ""),
                session_id=self._team_context.get("session_id", ""),
            )
        except Exception:
            return ""

    def _playbook_ctx(self) -> str:
        return self._ingest_ctx()

    @property
    def is_active(self) -> bool:
        return self._phase not in (Phase.IDLE, Phase.DONE)

    @property
    def draft_name(self) -> str:
        return self._draft_name or self._locked_name

    @property
    def locked_name(self) -> str:
        return self._locked_name

    def _lock_skill_name(self, name: str, *, force: bool = False) -> str:
        """Pin display/save name for the whole session (first valid name wins)."""
        normalized = self._normalize_name(name.strip()) if name else ""
        if not normalized or normalized == "未命名技能":
            return self._locked_name or self._draft_name
        if force or not self._locked_name:
            self._locked_name = normalized
        if not self._draft_name or force:
            self._draft_name = self._locked_name
        return self._locked_name

    def _resolve_skill_name(self, candidate: str = "") -> str:
        """Return the session-locked skill name, falling back to topic/goal."""
        if self._locked_name:
            return self._locked_name
        for raw in (candidate, self._draft_name, self._extract_topic(self._goal), self._goal):
            if raw and str(raw).strip():
                locked = self._lock_skill_name(str(raw))
                if locked:
                    return locked
        return self._normalize_name(candidate) if candidate else "extracted-skill"

    def _session_id(self) -> str:
        return self._team_context.get("session_id", "")

    def _persist_session_draft(self) -> None:
        sid = self._session_id()
        if not sid or not self._draft_content.strip():
            return
        try:
            from skillos.skills.session_draft import save_session_draft
            save_session_draft(
                sid,
                self._resolve_skill_name(self._draft_name),
                self._draft_content,
                goal=self._goal,
            )
        except Exception:
            _log.debug("Session draft persist skipped", exc_info=True)

    def _clear_session_draft(self) -> None:
        sid = self._session_id()
        if not sid:
            return
        try:
            from skillos.skills.session_draft import clear_session_draft
            clear_session_draft(sid)
        except Exception:
            _log.debug("Session draft clear skipped", exc_info=True)

    def _maybe_summarize_context(self) -> None:
        """Compress old context turns when conversation grows beyond 20 rounds.

        Prevents context window overflow in long refinement sessions while
        preserving key process details. Last 10 turns kept verbatim.
        """
        if len(self._context) <= 20:
            return
        old = self._context[:-10]
        if not old or (old[0] if old else "").startswith("[摘要]"):
            return
        try:
            from skillos.llm_client import call
            prompt = "将以下对话要点压缩成一段简短摘要，保留所有涉及流程步骤、触发条件、边界情况、参数格式的关键信息：\n\n" + "\n".join(old[-15:])
            summary = call(prompt, max_tokens=200, temperature=0.1)
            if summary and len(summary) > 20:
                self._context = [f"[摘要] {summary}"] + self._context[-10:]
        except Exception:
            pass

    def should_start(self, text: str) -> bool:
        """True when user explicitly asks to start a new skill topic."""
        msg = text.strip()
        if self._wants_to_finalize(msg):
            return False
        # Confirmation / finalize phrases must not restart an active extraction.
        finalize_kw = (
            "可以了", "确认", "生成吧", "保存", "没问题", "就这样", "开始生成",
            "直接生成", "生成文档", "生成最终", "够了",
        )
        if any(kw in msg for kw in finalize_kw):
            return False
        return any(kw in msg for kw in SKILL_START)

    def start_metaskill(self, available_skills: list[str]) -> str:
        """Enter MetaSkill creation mode (SD-compatible entry)."""
        self._phase = Phase.METASKILL
        self._turn = 0
        self._goal = ""
        self._context = []
        self._draft_name = ""
        self._draft_content = ""
        self._locked_name = ""
        preview = ", ".join(available_skills[:12])
        if len(available_skills) > 12:
            preview += f" … (+{len(available_skills) - 12})"
        return (
            f"🔗 **MetaSkill 模式** — 把多个技能编排成一条流水线。\n\n"
            f"当前可用技能 ({len(available_skills)} 个): {preview}\n\n"
            f"告诉我你想完成什么任务？我会帮你挑选技能、安排顺序。\n\n"
            f"例如：「先搜索资料，再按写作风格改写，最后做事实核查」"
        )

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def start(self, goal: str = "", *, quick_mode: bool = False) -> str:
        """Begin the skill extraction conversation with examples and guidance."""
        self._goal = goal
        topic = self._extract_topic(goal)

        if quick_mode and goal and len(goal.strip()) >= 400:
            self._phase = Phase.REFINING
            self._turn = 1
            self._context = [goal.strip()]
            self._probes_completed = set(_PROBE_ORDER)
            self._refinement_rounds = 0
            label = topic or "该流程"
            self._lock_skill_name(label)
            return (
                f"⚡ **快速模式**：已收到 {len(goal.strip())} 字详细描述，跳过探索轮次。\n\n"
                f"我将直接整理「**{label}**」的技能草稿。"
                f"请补充遗漏的分支或边界；若无补充，回复「可以了」或「保存」生成文档。"
            )

        self._phase = Phase.EXPLORING
        self._turn = 1

        examples_text = "\n".join(
            f"  {i}. **{name}**：{desc}"
            for i, (name, desc) in enumerate(_EXAMPLES, 1)
        )

        if topic:
            self._goal = topic
            self._lock_skill_name(topic)
            # Domain template detection (internal, not shown to user)
            try:
                from skillos.skills.domain_templates import resolve_domain_competition
                comp = resolve_domain_competition(goal or topic, top_k=3)
                if comp and comp.primary:
                    self._domain_template_id = comp.primary.template_id
                    self._context.append(f"[domain:{comp.primary.template_id}]")
            except Exception:
                pass
            # Research silently — shown naturally in follow-ups, not in opening
            self._research_cache = _research_topic(topic)
            opening = _domain_opening_for_topic(topic)
            return f"好的，聊聊「**{topic}**」这个流程——{opening}"
            return (
                f"好的，我们来沉淀「**{topic}**」的技能。\n\n"
                f"{opening}"
            )

        return (
            f"嘿，跟我聊聊你平时工作里的一个流程吧——比如每次都按固定套路处理的那种事。\n\n"
            f"举个栗子：{examples_text}\n\n"
            f"你有类似的事吗？随便说说就行。"
        )

    def restore_from_history(self, history: list[dict[str, str]]) -> bool:
        """Rehydrate extraction state from persisted conversation turns."""
        if self.is_active or not history or self._phase == Phase.DONE:
            return False

        user_msgs = [h["content"] for h in history if h.get("role") == "user" and h.get("content")]
        assistant_msgs = [h["content"] for h in history if h.get("role") == "assistant" and h.get("content")]
        if not user_msgs:
            return False

        extraction_markers = ("沉淀", "技能萃取", "我们来沉淀", "萃取助手", "好的，我们来")
        in_extraction = any(
            any(m in a for m in extraction_markers) for a in assistant_msgs
        )
        if not in_extraction:
            from skillos.skills.intent_router import DispatchIntent, classify_message_intent
            if classify_message_intent(user_msgs[0]) != DispatchIntent.EXTRACT:
                return False

        goal = user_msgs[0]
        topic = self._extract_topic(goal)
        self._goal = topic or goal.strip()
        self._lock_skill_name(self._goal)
        self._phase = Phase.EXPLORING
        self._turn = max(1, len(user_msgs))
        self._context = list(user_msgs)
        sid = self._session_id()
        if sid:
            try:
                from skillos.skills.session_draft import load_session_draft
                sd = load_session_draft(sid)
                if sd and sd.get("content"):
                    self._draft_content = sd["content"]
                    self._lock_skill_name(sd.get("name", "") or self._goal)
            except Exception:
                _log.debug("Session draft restore skipped", exc_info=True)
        return True

    def reply_to_meta_question(self) -> str:
        """Answer when user asks whether we are still extracting a skill."""
        topic = self._goal
        if not topic and self._context:
            topic = self._extract_topic(self._context[0])
        label = topic or "当前流程"
        return (
            f"是的，我们正在沉淀「**{label}**」的技能。\n\n"
            "我会根据你前面的描述继续追问细节；你可以继续补充触发条件、步骤和注意事项，"
            "或回复「可以了」生成草稿。"
        )

    def handle(self, message: str, existing_skills: list[str], llm_args: tuple) -> tuple[str, Optional[dict]]:
        """Handle one turn — SD-style phased Socratic extraction."""
        self._turn += 1

        if any(exit_word in message for exit_word in SKILL_EXIT):
            self._phase = Phase.DONE
            return "好的，已退出技能萃取。如果想重新开始，随时找我。", None

        if self._wants_to_finalize(message):
            if self._should_block_finalize(message):
                return ("信息还太少，请再多描述一下这个流程。"
                        "至少说出：什么时候触发？需要什么输入？分几步？"), None
            if self._phase in (Phase.EXPLORING, Phase.REFINING, Phase.CONFIRMING, Phase.OPTIMIZING):
                return self._generate(existing_skills, llm_args)

        if self._phase == Phase.EXPLORING:
            return self._explore(message, existing_skills, llm_args)
        if self._phase == Phase.REFINING:
            return self._refine(message, existing_skills, llm_args)
        if self._phase == Phase.OPTIMIZING:
            return self._optimize_turn(message, existing_skills, llm_args)
        if self._phase == Phase.METASKILL:
            return self._metaskill_turn(message, existing_skills, llm_args)
        if self._phase == Phase.CONFIRMING:
            return self._confirm_turn(message, existing_skills, llm_args)
        if self._phase == Phase.DONE:
            return self._post_done_turn(message, existing_skills, llm_args)

        # IDLE → first turn: set goal and enter Socratic explore (SD create mode)
        topic = self._extract_topic(message)
        self._goal = topic or message.strip()
        self._phase = Phase.EXPLORING
        return self._explore(message, existing_skills, llm_args)

    def _confirm_turn(
        self, text: str, existing_skills: list[str], llm_args: tuple,
    ) -> tuple[str, Optional[dict]]:
        if self._is_gap_question(text):
            self._phase = Phase.CONFIRMING
            self._awaiting_confirm = True
            return self._summarize(llm_args), None
        if self._wants_to_finalize(text):
            return self._generate(existing_skills, llm_args)
        self._phase = Phase.REFINING
        self._awaiting_confirm = False
        return self._refine(text, existing_skills, llm_args)

    def _post_done_turn(
        self, text: str, existing_skills: list[str], llm_args: tuple,
    ) -> tuple[str, Optional[dict]]:
        """After final skill saved — continuous refinement mode.

        User can keep chatting to improve the skill indefinitely.
        Each supplement is contextually incorporated. User says "生成" to regenerate.
        """
        label = self._finalized_name or self._draft_name or self._goal

        # URL/file reference during refinement: inject and continue
        import re
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            try:
                from skillos.utils.web_fetch import fetch
                content = fetch(urls[0])
                if content and len(content) > 100:
                    self._context.append(f"[参考资料] {urls[0]}: {content[:500]}")
                    self._research_cache = (self._research_cache or "") + f"\n用户补充参考: {content[:300]}"
                    return (
                        f"📖 已读取这篇资料，我会对照里面的做法来优化「**{label}**」。"
                        f"请继续说你的想法，或者回复「生成」更新技能文档。",
                        None,
                    )
            except Exception:
                pass

        # Regenerate on explicit request
        if self._wants_to_finalize(text):
            # Feed accumulated supplements into the refine pipeline before generating
            if len(self._context) > 0:
                self._phase = Phase.REFINING
                self._refinement_rounds = 0
            return self._generate(existing_skills, llm_args)

        # New topic request
        if self.should_start(text) and not self._wants_to_finalize(text):
            return (
                f"当前技能「**{label}**」还在优化中。"
                f"若要沉淀新主题，请说「新建xxx技能」或发送 __reset__ 开始新会话。",
                None,
            )

        # Continuous refinement: absorb supplement, feed back into context
        self._context.append(f"用户补充：{text[:300]}")
        # Re-enter refining to smartly incorporate the supplement
        self._phase = Phase.REFINING
        self._refinement_rounds = max(0, self._refinement_rounds - 1)  # Allow more refinement rounds

        # If this is a substantial addition, try a mini-refine
        if len(text.strip()) > 30:
            try:
                reply = self._refine(text, existing_skills, llm_args)
                return reply, None
            except Exception:
                pass

        return (
            f"收到，已更新「**{label}**」的上下文。继续补充或者回复「生成」更新文档。",
            None,
        )

    def _optimize_turn(
        self, text: str, existing_skills: list[str], llm_args: tuple,
    ) -> tuple[str, Optional[dict]]:
        report = self._optimize(existing_skills, llm_args)
        self._phase = Phase.CONFIRMING
        confirm = self._confirm(existing_skills, llm_args)
        return f"{report}\n\n---\n\n{confirm}", None

    def _metaskill_turn(
        self, text: str, existing_skills: list[str], llm_args: tuple,
    ) -> tuple[str, Optional[dict]]:
        if self._turn >= 4 or any(kw in text for kw in ["生成", "够了", "可以了", "保存"]):
            return self._generate_metaskill(existing_skills, llm_args)
        reply = self._metaskill(existing_skills, llm_args)
        return reply, None

    def _summarize(self, llm_args: tuple) -> str:
        """Summarize collected context and ask to generate (SD REFINING → CONFIRMING)."""
        context = "\n".join(self._context)
        model = llm_args[2] if len(llm_args) > 2 else ""
        prompt = f"""根据以下对话，用中文写一段简洁的技能摘要，然后问用户「要生成技能文档吗？」

## 技能目标
{self._goal[:200]}

## 对话记录
{context}

请用3-5句话概括这个技能的核心设计，然后询问是否可以生成文档。"""
        try:
            from skillos.llm_client import call
            return call(prompt, model=model, max_tokens=300, temperature=0.7).strip()
        except Exception as e:
            _log.warning("Summarize failed: %s", e)
            return "我已经了解了这个技能的核心设计。要生成技能文档吗？"

    def learn_from_url(self, url: str, page_content: str, existing_skills: list[str], llm_args: tuple) -> tuple[str, Optional[dict]]:
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
        ingest_context = self._ingest_ctx()

        pipeline_log: list[str] = []

        def _log(step: str, result: str) -> None:
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
            _log("初识", skim_raw)

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
            _log("理解", comprehend_raw)
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
            _log("拆解", deconstruct_raw)
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
            _log("重构", "生成技能文档草稿")
        except Exception as e:
            return f"重构阶段失败: {e}", None

        m = re.search(r"```skill_doc\s*\n(.*?)```", reconstruct_raw, re.DOTALL | re.IGNORECASE)
        draft = m.group(1).strip() if m else reconstruct_raw.strip()
        nm = re.search(r"^#\s*技能名称[：:]\s*(.+?)\s*$", draft, re.MULTILINE)
        name = self._normalize_name(nm.group(1).strip()) if nm else "url-learned-skill"

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
            _log("验证", validate_raw)
        except Exception as e:
            validate_raw = "总评: 通过\n修改建议: 验证阶段异常"
            _log("验证", str(e))

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
                    _log("修复", "已应用测试反馈的修改")
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
            _log("内化", internalize_raw)
        except Exception as e:
            internalize_raw = "内化阶段异常"
            _log("内化", str(e))

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
        diffusion_results = self._diffuse_knowledge(name, final_content, existing_skills, llm_args)

        self._draft_name = name
        self._draft_content = final_content

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

    # ═══════════════════════════════════════════════════════════════
    # Phase Methods
    # ═══════════════════════════════════════════════════════════════

    # ── EXPLORING phase ──

    def _explore(
        self, message: str, existing_skills: list[str], llm_args: tuple,
    ) -> tuple[str, Optional[dict]]:
        """Deep-dive into user's need. Research + Socratic question + progressive draft."""
        self._context.append(f"用户说：{message[:200]}")

        if self._name:
            try:
                from skillos.knowledge.memory import record_conversation
                record_conversation(self._name, "user", message)
            except Exception:
                _log.debug("Non-critical operation skipped", exc_info=True)

        research = ""
        if not self._research_done and existing_skills:
            self._research_done = True
            research = self._do_research(self._goal, existing_skills, llm_args)

        draft_ctx = ""
        if self._draft_content:
            draft_ctx = f"""\n## 当前技能草稿（在此基础上增量完善）
```skill_doc
{self._draft_content[:1000]}
```
请保留已有的正确内容，补充新了解到的信息。不确定的部分继续标注 [待补充]。\n"""

        similar_hint = ""
        if existing_skills and self._turn <= 2:
            goal_words = set(re.findall(r'[\w一-鿿]{2,}', self._goal))
            similar = []
            for sk in existing_skills[:20]:
                sk_words = set(re.findall(r'[\w一-鿿]{2,}', sk))
                if len(goal_words & sk_words) >= 2:
                    similar.append(sk)
            if similar:
                similar_hint = f"""\n## 🔗 可参考的已有技能
检测到以下技能可能与当前目标相关：{', '.join(similar[:5])}
如果它们的某些步骤或模式可以复用，主动向用户建议。\n"""

        model = llm_args[2] if len(llm_args) > 2 else ""
        ingest_ctx = self._ingest_ctx()
        prompt = f"""你是一个善于倾听的同事。用户正在描述一个工作流程，你的任务是**自然地接话追问**，就像朋友聊天一样。

## 用户描述的工作
「{self._goal[:100]}」

## 对话风格要求
- **口语化**：像微信聊天，不要教科书式的结构化提问
- **不说术语**：绝不使用 S_trigger、S_body、S_params、参数、输入格式等词
- **自然的共鸣追问**：比如"哦那如果…"、"你碰到过…吗"、"我理一下看对不对…"
- **不要列选项**：不要用 [选项] | action_key 格式。用自然语言描述即可
- **一次只聊一个点**：不要一口气问三个问题

## 追问策略
把用户说的话补完整。如果用户说了"怎么开始的"，就顺着聊。如果说了步骤，就问"然后呢"。
从对话中找"用户没说明白的点"自然追问——比如触发条件模糊就问触发，边界没提就问边界。

{similar_hint}
{ingest_ctx}
## 对话历史
{chr(10).join(self._context[-6:])}

{research}
{draft_ctx}

## 任务
做两件事：① 自然接话追问 ② 在后台更新技能草稿。
草稿规则：只增不改，不确定标[待补充]，不编造用户没提到的内容。

## 输出
<QUESTION>自然口语追问（2-4句话，不列选项）</QUESTION>
<SKILL_DRAFT>
```skill_doc
# 技能名称：<名称>
...
```
</SKILL_DRAFT>"""

        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=1200, temperature=0.7)
            question, draft = self._parse_dual_response(raw)
            reply = question.strip()
        except Exception as e:
            _log.warning("LLM explore failed: %s", e)
            reply = self._fallback_explore()
            draft = None

        if self._turn <= 1:
            reply = reply  # No more "Skill" preamble — just talk naturally

        if draft:
            self._save_draft(draft[0], draft[1])

        if self._turn >= 2 and len(self._context) >= 3:
            self._phase = Phase.REFINING

        return reply, None

    def _fallback_explore(self) -> str:
        """Static fallback when LLM is unavailable."""
        next_probe = next((p for p in _PROBE_ORDER if p not in self._probes_completed), None)

        fallback_questions = {
            "trigger": (
                "这个流程通常在什么情况下触发？\n\n"
                "[选项] 收到特定请求时触发 | trigger_on_request\n"
                "[选项] 定期执行（每天/每周） | trigger_scheduled\n"
                "[选项] 某个条件满足时触发 | trigger_conditional"
            ),
            "input": (
                "流程开始前需要什么输入或前置条件？\n\n"
                "1. 需要用户提交数据/表单\n"
                "2. 需要前置审批\n"
                "3. 需要外部系统数据\n"
                "4. 我自己描述"
            ),
            "steps": (
                "这个流程大概分几步？每步做什么？\n\n"
                "1. 3步以内的简单流程\n"
                "2. 4-6步的常规流程\n"
                "3. 7步以上的复杂流程\n"
                "4. 我自己描述"
            ),
            "output": (
                "流程结束后产出什么？\n\n"
                "1. 文字报告/文档\n"
                "2. 结构化数据/表格\n"
                "3. 代码/配置文件\n"
                "4. 我自己描述"
            ),
            "edge_cases": (
                "有没有需要特别注意的边界情况？\n\n"
                "1. 数据异常或缺失怎么处理\n"
                "2. 超时或失败需要重试\n"
                "3. 权限不足的兜底方案\n"
                "4. 我自己描述"
            ),
        }

        if next_probe and next_probe in fallback_questions:
            self._probes_completed.add(next_probe)
            return fallback_questions[next_probe]
        return "还有什么要补充的吗？\n\n1. 没有了，继续下一步\n2. 还有要补充的"

    # ── REFINING phase ──

    def _refine(
        self, text: str, existing_skills: list[str], llm_args: tuple,
    ) -> tuple[str, Optional[dict]]:
        """Help user refine details — steps, params, edge cases + update draft (SD-style).

        No hard turn limit — conversation can continue indefinitely.
        Only transitions forward when user explicitly requests generation.
        """
        self._context.append(f"用户说：{text[:200]}")
        # Long-context summarization: when context grows beyond 20 turns, compress older ones
        self._maybe_summarize_context()

        finish_kw = ("生成", "就这样", "够了", "可以了", "没问题", "保存")
        if self._is_gap_question(text):
            self._phase = Phase.CONFIRMING
            self._awaiting_confirm = True
            return self._summarize(llm_args), None
        if self._wants_to_finalize(text):
            return self._generate(existing_skills, llm_args)

        draft_ctx = ""
        if self._draft_content:
            draft_ctx = f"""\n## 当前技能草稿（在此基础上增量完善）
```skill_doc
{self._draft_content[:1000]}
```
请保留已有的正确内容，补充新了解到的信息。不确定的部分标注 [待补充]。\n"""

        # Internal quality self-check (not shown to user — used only for gap detection)
        quality_hint = ""
        if self._draft_content and self._turn >= 3:
            quality_hint = "\n## 内部草稿自检（仅用于判断缺口，不要告诉用户得分）\n对草稿的 trigger/body/params 完整性做内部评估，找出最薄弱的环节。"

        model = llm_args[2] if len(llm_args) > 2 else ""
        prompt = f"""你是一个善于倾听的同事，正在帮朋友理清一个工作流程。

## 用户的目标
**{self._goal[:200]}**

## 对话风格
- **口语化自然**：像微信聊天，不说 S_trigger/S_body/S_params/参数/输入格式 等术语
- **用"我理解对了吗"代替打分**：比如"我帮你理一下——先做A再B然后C，登录前用验证码验证。有没有漏的？"
- **不要列选项按钮**：不要用 [选项] | action_key 格式
- **一次只聊一个缺口**：从对话中找出一个还没聊清楚的点，自然追问

## 对话历史
{chr(10).join(self._context[-8:])}
{draft_ctx}
{quality_hint}
📚 背景参考：
{self._research_cache or '（暂无）'}

## 任务
做两件事：① 用"我理一下"的方式自然确认+追问一个缺口 ② 后台增量更新草稿。
草稿规则：只增不改，不确定标[待补充]，不编造。

## 输出
<QUESTION>自然口语追问（我理一下…有没有漏的？或者 你碰到过…吗？）</QUESTION>
<SKILL_DRAFT>
```skill_doc
...
```
</SKILL_DRAFT>"""

        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=1200, temperature=0.7)
            question, draft = self._parse_dual_response(raw)
            reply = question.strip()
        except Exception as e:
            _log.warning("LLM refine failed: %s", e)
            reply = self._fallback_refine()
            draft = None

        if draft:
            self._save_draft(draft[0], draft[1])

        return reply, None

    def _fallback_refine(self) -> str:
        """Static fallback for refinement."""
        return (
            "好的。这个流程中有没有容易出错的地方？\n\n"
            "1. 数据校验方面容易出错\n"
            "2. 边界情况处理不完整\n"
            "3. 步骤之间的衔接容易断开\n"
            "4. 我自己描述"
        )

    def _enter_confirming(self, existing_skills: list[str], llm_args: tuple) -> tuple[str, None]:
        """Merge quality precheck + confirmation draft in one assistant turn."""
        self._phase = Phase.CONFIRMING
        self._sync_probes_from_context()
        report = self._optimize(existing_skills, llm_args)
        confirm = self._confirm(existing_skills, llm_args)
        return f"{report}\n\n---\n\n{confirm}", None

    def _sync_probes_from_context(self) -> None:
        """Backfill probe coverage from conversation and draft content."""
        for msg in self._context:
            dim = self._detect_dimension(msg)
            if dim:
                self._probes_completed.add(dim)
        dc = self._draft_content
        if not dc:
            return
        if "S_trigger" in dc or "触发" in dc:
            self._probes_completed.add("trigger")
        if "S_params" in dc or "参数" in dc or "输入" in dc or "前置" in dc:
            self._probes_completed.add("input")
        if "S_body" in dc or re.search(r"^\d+\.", dc, re.MULTILINE):
            self._probes_completed.add("steps")
        if "输出" in dc or "产出" in dc or "交付" in dc:
            self._probes_completed.add("output")
        if "边界" in dc or "异常" in dc or "if " in dc.lower():
            self._probes_completed.add("edge_cases")

    def _context_saturated(self) -> bool:
        """True when most dimensions are covered and a draft exists."""
        self._sync_probes_from_context()
        return len(self._probes_completed) >= 4 and bool(self._draft_content.strip())

    @staticmethod
    def _is_gap_question(message: str) -> bool:
        msg = message.strip()
        return any(
            p in msg
            for p in (
                "还需什么", "还要什么", "需要什么信息", "缺什么",
                "还需要什么", "还要补充", "还缺什么",
            )
        )

    @staticmethod
    def _is_explicit_finalize(message: str) -> bool:
        """Strong generate/save intent — not a bare 「好/行/确认」."""
        msg = message.strip()
        explicit = (
            "可以了", "就这样", "没问题", "确认生成", "生成吧", "生成技能",
            "生成文档", "开始生成", "直接生成", "保存吧", "保存技能",
            "够了", "不要再问", "不要继续问", "直接保存", "不要再提问",
        )
        if any(p in msg for p in explicit):
            return True
        if "确认" in msg and any(k in msg for k in ("生成", "保存", "文档", "终稿")):
            return True
        return False

    def _should_block_finalize(self, message: str) -> bool:
        """Block only ambiguous finalize when conversation context is thin."""
        if self._is_explicit_finalize(message):
            return False
        if not self._wants_to_finalize(message):
            return False
        user_turns = sum(1 for c in self._context if c.startswith("用户"))
        depth = max(self._turn, user_turns, len(self._context))
        if depth >= 4 or self._context_saturated():
            return False
        if self._draft_content.strip() and depth >= 2:
            return False
        return depth < 2

    @staticmethod
    def _wants_to_finalize(message: str) -> bool:
        """Explicit user intent to produce the final SKILL.md."""
        msg = message.strip()
        phrases = (
            "可以了", "就这样", "没问题", "确认生成", "生成吧", "生成技能",
            "生成文档", "开始生成", "直接生成", "保存吧", "保存技能",
            "生成", "够了",  # SD original finish keywords that were missing
        )
        if any(p in msg for p in phrases):
            return True
        if msg in ("好", "行", "确认", "是的", "可以", "保存", "生成"):
            return True
        if "确认" in msg and any(k in msg for k in ("生成", "保存", "文档", "终稿")):
            return True
        return False

    @staticmethod
    def _wants_to_finish(message: str) -> bool:
        """User signals readiness to enter confirm phase (REFINING only)."""
        return SkillExtractionAgent._wants_to_finalize(message)

    # ── OPTIMIZING phase ──

    def _optimize(self, existing_skills: list[str], llm_args: tuple) -> str:
        """Run compliance checks and present optimization report."""
        # Build a working draft for compliance checking
        context_text = "\n".join(self._context)

        report_parts = ["## 🔍 技能质量预检\n"]

        # 1. Structure check (no LLM needed)
        report_parts.append("### 📋 结构完整性")
        dims_found = len(self._probes_completed)
        dims_total = len(_PROBE_ORDER)
        report_parts.append(f"- 已覆盖维度：{dims_found}/{dims_total}")
        for probe in _PROBE_ORDER:
            icon = "✅" if probe in self._probes_completed else "⚠️"
            report_parts.append(f"  {icon} {_PROBE_DESCRIPTIONS.get(probe, probe)}")

        # 2. Playbook / PURPOSE compliance (if available)
        try:
            ingest_ctx = self._ingest_ctx()
            if ingest_ctx:
                report_parts.append("\n### 🏢 团队 Playbook / PURPOSE 已加载")
                report_parts.append("生成时将按团队标准与知识体系目标输出。")
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)

        # 3. DNA context (if available)
        try:
            from skillos.skills.pattern_miner import get_skill_dna_context
            dna_ctx = get_skill_dna_context()
            if dna_ctx:
                report_parts.append("\n### 🧬 Skill DNA 已加载")
                report_parts.append("生成时将遵循系统学习到的设计原则。")
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)

        report_parts.append("\n---\n进入确认阶段，我会根据对话内容生成技能草稿供你确认。")

        return "\n".join(report_parts)

    # ── CONFIRMING phase ──

    def _confirm(self, existing_skills: list[str], llm_args: tuple) -> str:
        """LLM-generated structured summary for user confirmation."""
        context_text = "\n".join(self._context)
        skills_str = ", ".join(existing_skills[:5]) if existing_skills else "暂无"
        model = llm_args[2] if len(llm_args) > 2 else ""

        prompt = f"""根据以下对话，生成一个结构化的技能文档草稿供用户确认。

## 对话记录
{context_text}

## 已有技能（交叉参考）
{skills_str}

## 输出格式
```markdown
# 技能名称：<从对话中提炼的名称（2-6字最佳）>
## 核心问题
<一句话描述：这个技能解决什么问题？>

## S_body
1. <步骤一>（如果XX则YY）
2. <步骤二>
...

## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| <条件或意图1> | <对应 S_body 步骤或分支> | |
| <条件或意图2> | <对应动作> | |

## S_trigger
- keywords: <关键词列表，逗号分隔>
- context: <触发场景描述>

## S_params
- <参数名>: <类型，默认值，说明>
```

## 要求
1. 只提炼对话中明确提到的内容，不要编造
2. 如果某个部分信息不足，标注「[待补充]」
3. 名称简明扼要
4. 核心问题一句话说清
5. S_route 必须包含至少 2 行决策表，映射 S_body 中的主要 if-then 分支
6. 输出完草稿后，以「---\n请确认以上内容是否准确？\n1. ✅ 确认，生成最终版本\n2. ✏️ 需要修改」结尾。"""

        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=900, temperature=0.3)
            return raw
        except Exception as e:
            _log.warning("LLM confirm failed, using fallback: %s", e)
            return self._fallback_confirm()

    def _fallback_confirm(self) -> str:
        """Static fallback for confirmation."""
        summary = "\n".join(f"- {c[:120]}" for c in self._context[-4:])
        return (
            f"根据对话提取的技能概要：\n\n{summary}\n\n"
            "是否确认生成最终版本？\n"
            "1. ✅ 确认，生成\n"
            "2. ✏️ 需要补充修改"
        )

    # ── GENERATING phase ──

    def _ensure_s_route(self, content: str, llm_args: tuple) -> str:
        """Inject S_route decision table when the LLM omitted it."""
        if "S_route" in content:
            return content
        model = llm_args[2] if len(llm_args) > 2 else ""
        prompt = f"""以下技能文档缺少 S_route 决策表。请根据 S_body 中已有的 if-then 分支补充，不要添加新事实。

{content[:2000]}

只输出以下格式（不要其他文字）：
## S_route
| 用户意图/条件 | 执行动作 | 备注 |
|------------|---------|------|
| ... | ... | ... |

至少 2 行，每行对应 S_body 中一个主要分支。"""
        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=400, temperature=0.2)
            route_m = re.search(r"(## S_route\s*\n(?:\|.*\n)+)", raw, re.MULTILINE)
            if route_m:
                block = route_m.group(1).strip()
                trigger_m = re.search(r"\n## S_trigger", content)
                if trigger_m:
                    pos = trigger_m.start()
                    return content[:pos] + "\n" + block + "\n" + content[pos:].lstrip("\n")
                return content.rstrip() + "\n\n" + block + "\n"
        except Exception as e:
            _log.warning("S_route injection failed: %s", e)
        return content

    def _generation_context(self, max_chars: int = 14000) -> str:
        """Assemble full extraction context for final SKILL.md generation."""
        parts: list[str] = []
        if self._draft_content.strip():
            parts.append(
                "## 渐进草稿（优先保留其中已确认内容）\n"
                f"```skill_doc\n{self._draft_content[:6000]}\n```"
            )
        if self._context:
            full = "\n".join(self._context)
            if len(full) <= max_chars:
                parts.append(f"## 完整对话\n{full}")
            else:
                head = "\n".join(self._context[:3])
                tail = "\n".join(self._context[-40:])
                parts.append(f"## 对话摘要\n{head}\n...\n{tail}")
        return "\n\n".join(parts) if parts else self._goal

    def _generate(self, existing_skills: list[str], llm_args: tuple) -> tuple[str, Optional[dict]]:
        """Generate final installable SKILL.md (Cursor / Claude Code / Trae compatible)."""
        from skillos.skills.portable_skill import finalize_portable_skill, load_portable_spec

        self._phase = Phase.GENERATING
        context_text = self._generation_context()
        skills_str = ", ".join(existing_skills[:8]) if existing_skills else "暂无"
        model = llm_args[2] if len(llm_args) > 2 else ""
        portable_spec = load_portable_spec()

        try:
            from skillos.skills.pattern_miner import ensure_bootstrap_skill_dna
            ensure_bootstrap_skill_dna()
        except Exception:
            _log.debug("Bootstrap Skill DNA skipped", exc_info=True)

        dna_unified = ""
        dna_tpl_competition = ""
        try:
            from skillos.knowledge.dna_context import build_dna_context, build_domain_template_context
            dna_unified = build_dna_context(self._goal, context_text[:2500])
            dna_tpl_competition = build_domain_template_context(self._goal, context_text[:2000])
        except Exception:
            _log.debug("DNA context build skipped", exc_info=True)

        base_prompt = f"""你是技能创作助手。用户通过对话描述了一个工作流程，不懂什么是 Skill。
你的任务：生成一份**可直接安装到 Cursor、Claude Code、Trae** 的 SKILL.md 正文。

## 技能目标
{self._goal[:300]}

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
7. 只输出 skill_doc 代码块"""

        # Inject DNA principles
        try:
            from skillos.skills.pattern_miner import inject_dna_to_prompt
            prompt = inject_dna_to_prompt(base_prompt)
        except Exception as e:
            _log.warning("DNA injection failed: %s", e); prompt = base_prompt

        # Append playbook + purpose context
        try:
            ingest_ctx = self._ingest_ctx()
            if ingest_ctx:
                prompt += f"\n{ingest_ctx}\n"
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)

        if self._domain_template_id:
            try:
                from skillos.skills.domain_templates import get_generation_boost
                boost = get_generation_boost(self._domain_template_id)
                if boost:
                    prompt += (
                        "\n\n## 领域骨架模板（在对话事实基础上填充，勿删除 S_route/S_params 结构）\n"
                        f"{boost}\n"
                    )
                secondary_ids = [
                    tid for tid in self._domain_template_ids
                    if tid and tid != self._domain_template_id
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

        # Quality precheck (structure coverage, no LLM)
        try:
            self._sync_probes_from_context()
            precheck = self._optimize(existing_skills, llm_args)
            prompt += f"\n\n## 生成前质量预检（请尽量覆盖未达标项）\n{precheck}\n"
        except Exception:
            _log.debug("Precheck skipped", exc_info=True)

        locked_display = self._resolve_skill_name()
        prompt += f"\n8. 技能中文名称必须固定为「{locked_display}」（不要用其他名称）\n"

        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=2500, temperature=0.3)
            m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
            content = m.group(1).strip() if m else raw.strip()

            nm = re.search(r"^#\s*技能名称[：:]\s*(.+?)\s*$", content, re.MULTILINE)
            extracted = nm.group(1).strip() if nm else ""
            name = self._resolve_skill_name(extracted or self._draft_name or self._goal)

            if "S_route" not in content:
                content = self._ensure_s_route(content, llm_args)

            try:
                from skillos.skills.skill_structure import normalize_skill_body
                content = normalize_skill_body(content)
            except Exception:
                _log.debug("normalize_skill_body skipped", exc_info=True)

            content = self._apply_dna_compliance_fix(content, llm_args)

            finalized = finalize_portable_skill(name, content)
            name = self._resolve_skill_name(finalized["name"])
            content = finalized["body"]

            self._draft_name = name
            self._draft_content = content
            self._locked_name = name
            self._clear_session_draft()

            # Feynman simplification: verify understanding depth, flag gaps
            feynman_msg = ""
            try:
                from skillos.evolution.learning_theory import recursive_feynman
                simpler, deepened = recursive_feynman(content, llm_args)
                if deepened:
                    feynman_msg = "\n\n### 🧠 费曼简化检测\n> ⚠️ 简化版与原文差异较大——以下步骤可能需要补充说明：「[这里我需要再想想]」标记的部分建议人工复核。"
                    _log.info("Feynman deepened: %s (simpler=%d chars, original=%d)", name, len(simpler), len(content))
            except Exception:
                _log.debug("recursive_feynman skipped", exc_info=True)

            # Cross-domain analogies: find structurally similar skills
            analogy_msg = ""
            try:
                from skillos.evolution.learning_theory import find_analogies
                analogies = find_analogies(name, content, existing_skills, llm_args)
                if analogies:
                    analogy_names = [a.get("skill","?") for a in analogies[:3]]
                    analogy_msg = f"\n\n### 🔀 跨领域类比\n> 检测到与以下技能存在结构同构：{', '.join(analogy_names)}。可参考其优化经验。"
                    _log.info("Analogies found for %s: %s", name, analogy_names)
            except Exception:
                _log.debug("find_analogies skipped", exc_info=True)

            # Knowledge diffusion: check if new skill can improve existing ones
            diffusion_msg = ""
            try:
                diffusion_results = self._diffuse_knowledge(name, content, existing_skills, llm_args)
                if diffusion_results:
                    highlights = [r for r in diffusion_results if r.startswith("✅")]
                    if highlights:
                        diffusion_msg = "\n\n### 🔄 知识扩散\n" + "\n".join(highlights[:3])
            except Exception:
                _log.debug("Non-critical operation skipped", exc_info=True)

            # Epistemic claim recording: extract claims from generated skill,
            # classify and cross-reference for Plato/Popper verification
            try:
                from skillos.knowledge.epistemology import record_claim
                for claim_text in self._extract_claims_from_skill(content):
                    record_claim(
                        content=claim_text,
                        source=f"skill_extraction:{name}",
                        source_type="llm_generated",
                        skill_name=name,
                    )
                _log.info("Recorded %d claims from skill '%s'",
                          sum(1 for _ in self._extract_claims_from_skill(content)), name)
            except Exception:
                _log.debug("Epistemic claim recording skipped", exc_info=True)

            self._phase = Phase.DONE
            self._finalized_name = name
            self._awaiting_confirm = False
            doc = {
                "name": name,
                "content": content,
                "slug": finalized["slug"],
                "description": finalized["description"],
                "install_paths": finalized["install_paths"],
            }
            return (
                f"✅ 已为你生成可安装的技能「**{name}**」！\n\n"
                f"```skill_doc\n{content}\n```\n\n"
                f"这是标准 SKILL.md，可复制到 Cursor / Claude Code / Trae 直接使用。"
                f"{diffusion_msg}",
                doc,
            )
        except Exception as e:
            _log.error("Generation failed: %s", e)
            return f"生成失败: {e}", None

    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════

    def _apply_dna_compliance_fix(
        self,
        content: str,
        llm_args: tuple,
        *,
        max_rounds: int = 2,
        min_passed: int = 5,
    ) -> str:
        from skillos.skills.pattern_miner import apply_dna_compliance_fix
        return apply_dna_compliance_fix(
            content, llm_args, max_rounds=max_rounds, min_passed=min_passed,
        )

    @staticmethod
    def _extract_topic(goal: str) -> str:
        """Extract the actual skill topic from a user request.
        Returns empty string for generic 'create a skill' requests."""
        if not goal or not goal.strip():
            return ""
        from skillos.skills.intent_router import is_meta_extraction_question
        if is_meta_extraction_question(goal):
            return ""
        topic = goal
        for prefix in [
            "帮我创建一个", "帮我创建", "我想创建一个", "我想创建",
            "创建一个", "创建", "帮我写一个", "帮我写", "写一个", "写",
            "新建一个", "新建", "做一个", "做", "生成一个", "生成",
            "帮我沉淀一套", "帮我沉淀一下", "帮我沉淀", "沉淀一下", "沉淀一套", "沉淀一个", "沉淀",
            "萃取一个", "萃取", "提炼一个", "提炼",
            "帮我整理一个", "帮我整理", "整理一个", "整理",
        ]:
            if topic.startswith(prefix):
                topic = topic[len(prefix):]
                break
        # Truncate at first sentence-ending punctuation (user added details after the topic)
        for sep in ("。", "？", "！", "，", ".", "?", "!"):
            pos = topic.find(sep)
            if pos > 0:
                topic = topic[:pos]
                break
        for suffix in ["的技能", "的skill", "技能", "skill", "流程", "的方法", "的方案"]:
            if topic.endswith(suffix):
                topic = topic[:-len(suffix)]
                break
        topic = topic.strip("的个一个一下。！？ ")
        if topic.startswith("一套"):
            topic = topic[2:].lstrip()
        return topic

    @staticmethod
    def _detect_dimension(message: str) -> Optional[str]:
        """Detect which exploration dimension a user message addresses."""
        triggers = ["触发", "场景", "什么时候", "当", "如果", "条件", "原因", "前提"]
        inputs = ["输入", "前置", "参数", "数据", "素材", "资料", "收到", "拿到"]
        steps = ["步骤", "第一步", "首先", "然后", "接着", "最后", "流程", "操作", "执行"]
        outputs = ["输出", "产出", "结果", "格式", "文档", "报告", "表格", "代码", "交付"]
        edges = ["异常", "错误", "边界", "特殊", "失败", "超时", "意外", "兜底"]

        for dim, kws in [
            ("trigger", triggers), ("input", inputs), ("steps", steps),
            ("output", outputs), ("edge_cases", edges),
        ]:
            if any(kw in message for kw in kws):
                return dim
        return None

    def _build_probe_status(self) -> str:
        """Build a status string of exploration progress."""
        lines = []
        for key in _PROBE_ORDER:
            desc = _PROBE_DESCRIPTIONS.get(key, key)
            status = "✅ 已覆盖" if key in self._probes_completed else "⬜ 待探索"
            lines.append(f"- {status}: {desc}")
        return "\n".join(lines)

    @staticmethod
    def _is_confirmation(message: str) -> bool:
        """Detect if the user confirms (vs requests changes)."""
        msg = message.lower().strip()

        confirm_kw = ["确认", "可以", "生成", "好的", "是", "对", "yes", "y",
                       "confirm", "没错", "就这样", "可以了", "没问题", "行", "保存"]
        change_kw = ["修改", "补充", "添加", "改一下", "不对", "错了", "缺少",
                      "漏了", "调整", "重做", "重新", "改改"]

        # Changes take priority
        if any(kw in msg for kw in change_kw):
            return False

        # Check confirmation
        if any(kw in msg for kw in confirm_kw):
            negations = ["不", "没", "别"]
            if all(neg not in msg for neg in negations):
                return True

        # Short affirmative
        if msg in ("1", "确认", "可以", "是"):
            return True

        return False

    def _parse_dual_response(self, raw: str) -> tuple[str, tuple[str, str] | None]:
        """Parse combined LLM response into (question, optional (name, content))."""
        question = raw
        draft = None
        qm = re.search(r'<QUESTION>\s*\n?(.*?)\n?\s*</QUESTION>', raw, re.DOTALL | re.IGNORECASE)
        if qm:
            question = qm.group(1).strip()
        sm = re.search(r'<SKILL_DRAFT>\s*\n?(.*?)\n?\s*</SKILL_DRAFT>', raw, re.DOTALL | re.IGNORECASE)
        if sm and sm.group(1).strip().lower() != 'none':
            draft_raw = sm.group(1).strip()
            dm = re.search(r"```skill_doc\s*\n(.*?)```", draft_raw, re.DOTALL | re.IGNORECASE)
            content = dm.group(1).strip() if dm else draft_raw
            nm = re.search(r"^#\s*技能名称[：:]\s*(.+?)\s*$", content, re.MULTILINE)
            raw_name = nm.group(1).strip() if nm else (self._draft_name or "未命名技能")
            name = self._resolve_skill_name(raw_name)
            draft = (name, content)
        return question, draft

    def _save_draft(self, name: str, content: str) -> None:
        """Keep progressive draft in session only — never write to skills/ until finalize."""
        if self._phase in (Phase.DONE, Phase.GENERATING):
            return
        locked = self._resolve_skill_name(name)
        self._draft_name = locked
        self._draft_content = content
        self._persist_session_draft()

    def inject_external_knowledge(self, content: str, source: str = "") -> str:
        """Inject external content (URL/file) into an active extraction conversation.

        Called during skill extraction when the user drops a URL or file.
        The content becomes research material for the agent's questions.
        """
        if not self.is_active:
            return ""
        preview = content[:3000]
        self._context.append(f"[外部资料: {source}] {preview[:500]}")
        self._research_done = True  # Mark as researched so _explore won't re-search

        # Also record to skill memory
        if self._draft_name:
            try:
                from skillos.knowledge.memory import record_conversation
                record_conversation(self._draft_name, "system", f"外部资料注入: {source} ({len(content)} chars)")
            except Exception:
                _log.debug("Non-critical operation skipped", exc_info=True)

        return f"📖 已读取「{source[:60]}」({len(content)} 字符)，这些内容将用于技能萃取。请继续描述或回答刚才的问题。"

    def _do_research(self, goal: str, existing: list[str], _llm_args: tuple) -> str:
        """Background research — existing skills + web search."""
        parts = []
        # Existing skills
        try:
            from skillos.skills import skill_store
            refs = []
            for sk in existing[:5]:
                try:
                    body = skill_store.get_skill_body(skill_store.load_skill(sk))
                    if body and len(body) > 50:
                        refs.append(f"「{sk}」: {body[:300]}")
                except Exception:
                    _log.debug("Non-critical operation skipped", exc_info=True)
            if refs:
                parts.append("## 已有技能参考\n" + "\n\n".join(refs[:3]))
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)
        # Web search
        try:
            from skillos.utils.web_search import search as ws
            r = ws(f"{goal[:60]} 最佳实践 方法论 怎么做", 2)
            if r and "No results" not in r:
                parts.append(f"## 网络搜索\n{r[:600]}")
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)
        return "\n\n".join(parts) if parts else ""

    def _diffuse_knowledge(
        self, new_skill_name: str, new_content: str,
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

    # ── MetaSkill pipeline creation ──

    def _metaskill(self, existing_skills: list[str], llm_args: tuple) -> str:
        """Guide the user through creating a MetaSkill pipeline."""
        skills_str = ", ".join(existing_skills[:12]) if existing_skills else "（暂无可用技能）"
        model = llm_args[2] if len(llm_args) > 2 else ""

        context_text = "\n".join(self._context[-4:]) if self._context else self._goal
        prompt = f"""你是 MetaSkill 管道架构师。用户的流程包含多个独立步骤，适合用 MetaSkill 流水线来编排。

## 用户目标
{self._goal[:200]}

## 对话
{context_text[:500]}

## 可用技能
{skills_str}

## 任务
提出一个引导问题帮助用户设计管道：
1. 哪些步骤可以复用已有技能？
2. 哪些步骤需要新建技能？
3. 步骤之间的依赖关系是什么？
4. 这个管道需要哪些工具？

引导用户用自然语言描述管道，格式：步骤名: 需要的技能  # 依赖: [前一步]

只问一个问题，给 2-3 个选项。"""

        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=400, temperature=0.7)
            return raw.strip()
        except Exception as e:
            _log.warning("MetaSkill LLM failed: %s", e); return f"你的流程包含多个独立步骤，适合用 MetaSkill 流水线来编排。\n\n可用技能：{skills_str}\n\n请描述你的管道，例如：\n`代码扫描: 代码安全扫描  # output_key: scan_result`\n`报告生成: 安全报告生成  # depends_on: [代码扫描]`"

    def _generate_metaskill(self, existing_skills: list[str], llm_args: tuple) -> tuple[str, dict | None]:
        """Generate the MetaSkill pipeline document."""
        from skillos.skills.metaskill import parse_metaskill
        from skillos.skills.skill_store import save_skill

        model = llm_args[2] if len(llm_args) > 2 else ""
        skills_str = ", ".join(existing_skills[:12]) if existing_skills else "暂无"
        context_text = "\n".join(self._context[-6:]) if self._context else self._goal

        prompt = f"""根据对话生成一个 MetaSkill 管道文档。

## 对话
{context_text}

## 可用技能
{skills_str}

## 输出格式
```markdown
---
type: metaskill
name: <管道名称>
---

# MetaSkill: <名称>

## Goal
<一句话描述管道目标>

## Pipeline
```pipeline
step_name: skill_name  # depends_on: [dep] | output_key: key | tools: [tool]
```

## Tool Whitelist
- tool_name

## Risk Level: low
```"""

        try:
            from skillos.llm_client import call
            raw = call(prompt, model=model, max_tokens=800, temperature=0.3)
            m = re.search(r"```(?:markdown)?\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
            content = m.group(1).strip() if m else raw.strip()
        except Exception as e:
            _log.warning("MetaSkill generation failed: %s", e); return "MetaSkill 生成失败。", None

        # Parse and validate
        ms = parse_metaskill(content)
        name = "metaskill"

        if ms and ms.name:
            name = ms.name
            if ms.steps:
                try:
                    save_skill(name, content, meta={"type": "metaskill"})
                except Exception:
                    _log.debug("Non-critical operation skipped", exc_info=True)
                self._draft_name = name
                self._draft_content = content
                self._phase = Phase.DONE
                return f"✅ MetaSkill 管道「{name}」已生成（{len(ms.steps)}个步骤）！\n\n```\n{content[:500]}\n```", {"name": name, "content": content}

        save_skill(name, content)
        self._draft_name = name
        self._draft_content = content
        self._phase = Phase.DONE
        return f"✅ MetaSkill「{name}」已生成！", {"name": name, "content": content}

    def _get_zpd_context(self) -> str:
        """Get ZPD learning records context for the current skill."""
        try:
            from skillos.evolution.learning_records import get_zpd_context
            return get_zpd_context(self._draft_name) if self._draft_name else ""
        except Exception as e:
            _log.debug("ZPD context unavailable: %s", e); return ""

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Parse JSON from LLM response (may be in markdown code block or raw)."""
        m = re.search(r'```(?:json)?\s*\n(.*?)```', raw, re.DOTALL | re.IGNORECASE)
        text = m.group(1) if m else raw
        # Find the first { ... } block
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end+1]
        return json.loads(text)

    @staticmethod
    def _normalize_name(raw_name: str, max_len: int = 12) -> str:
        """Normalize skill name: clean, concise, consistent.

        Rules:
        - Max 12 Chinese chars (fits UI sidebars and CLI listings)
        - Remove quotes, brackets, punctuation, special chars
        - Remove filler words like 指南/教程/入门 unless essential
        """
        import re
        name = raw_name.strip()
        name = re.sub(r'^#\s*技能名称[：:]\s*', '', name)
        name = re.sub(r'[*_#~`]', '', name)
        # Remove trailing punctuation fragments (e.g. "流程。收集各部门数据" → "流程")
        name = re.sub(r'[。．.！!？?，,、；;：:]+.*$', '', name)
        name = re.sub(r'\s*[。．.！!？?，,、；;：:]\s*$', '', name)
        for q in ['"', '"', '"', '"', ''', ''', '「', '」']:
            name = name.replace(q, '')
        name = re.sub(r'[（(]\s*[A-Za-z0-9\s]+\s*[)）]', '', name)
        name = re.sub(r'\s*[（(][^)）]*[)）]\s*$', '', name)
        name = re.sub(r'\s*[\[【][^\]]*[\]】]\s*$', '', name)
        for filler in ['指南', '教程', '入门', '详解', '完全指南', '使用说明', '操作手册', '流程', '自动化']:
            if name.endswith(filler) and len(name) > len(filler) + 1:
                name = name[:-len(filler)]
        name = re.sub(r'^[A-Za-z0-9\s]+[-—–]\s*', '', name)
        name = re.sub(r'\s+Skill\s*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*[-—–]\s*$', '', name)
        name = re.sub(r'[-—–]{2,}', '', name)
        name = name.strip().strip('。．.，, -—–-')
        if len(name) > max_len:
            cut = max_len
            for sep in ['——', '—', '，', '、', ' ', '·']:
                pos = name[:max_len].rfind(sep)
                if pos > max_len // 2:
                    cut = pos
                    break
            name = name[:cut]
        return name.strip() if name else "未命名技能"

    @staticmethod
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
