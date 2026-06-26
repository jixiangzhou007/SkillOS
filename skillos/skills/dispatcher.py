"""SkillDispatcher — intent routing and skill execution via LLM function calling.

Converts saved skills into OpenAI-compatible tool definitions and lets the LLM
decide whether a user message should trigger a skill. If no skill matches, falls
through to normal conversation / skill extraction.

**Precipitation protocol (Phase 3)** — IM/API message intents (extract, confirm
pending claims, playbook, etc.) are defined in ``skillos/skills/intent_router.py``
and documented in ``docs/USER_GUIDE.md``.  This module handles *skill execution*
after a skill is already saved; do not duplicate trigger tables here.
"""


import json
import logging
from typing import Any, Optional

from openai import OpenAI

from skillos.config import get_config
from skillos.skills import agent_factory, skill_store

logger = logging.getLogger(__name__)

# Max number of skill tools to send per request (to manage token usage).
MAX_TOOLS_PER_REQUEST = 20

# System prompt for the dispatcher's routing decision.
DISPATCHER_SYSTEM = """\
You are the routing layer of an AI companion. Your job is to decide whether the \
user's message should be handled by a specific skill (tool) or handled as a \
normal conversation.

Rules:
1. If the user's intent CLEARLY matches one of the available skills, call that skill.
   - The skill's description tells you when to use it.
   - Pass the user's exact request as the "task" parameter.
2. If no skill matches, or you're unsure, respond normally (no tool call).
   - This is a conversation, not a forced match. When in doubt, just chat.
3. Only call ONE skill at a time. Pick the best match.
4. Be conversational in your responses. You are a companion, not a search engine.
5. Always respond in Chinese (中文) unless explicitly asked otherwise.
"""

# Extra instructions for voice conversation mode
VOICE_SYSTEM_EXTRA = """\
VOICE MODE — You are speaking aloud through TTS.

- The user's input is from speech recognition and may contain errors. Infer intent from context, silently correct homophone errors.
- Always respond in spoken Chinese, 1-3 short sentences.
- Be warm and natural, like talking to a friend on the phone.
- No markdown, no formatting, no gestures/expression descriptions.
"""

# Prompt template when skills are available — lists tool descriptions.
ROUTING_PROMPT_WITH_TOOLS = """\
You have access to the following skills. Only use them when the user's request \
clearly matches the skill's purpose.

{skill_summaries}

When responding normally (no tool call), help the user with their request or \
guide them toward clarifying what they need."""

# Prompt template when NO skills are available.
ROUTING_PROMPT_NO_TOOLS = """\
You don't have any saved skills yet. Help the user naturally. If they describe \
a repeatable process or workflow, suggest creating a skill for it. \
Always respond in Chinese (中文) unless the user explicitly asks for another language."""


def _build_client() -> OpenAI:
    from skillos.llm_client import get_client
    return get_client()


def _skill_to_tool(skill: dict[str, Any]) -> dict[str, Any]:
    """Convert a skill dict (from skill_store.load_skill_raw) to an OpenAI tool definition."""
    name = skill["name"]
    body = skill["body"]

    # Check if this is a MetaSkill
    is_metaskill = "type: metaskill" in body[:200]

    # Extract description
    desc = _extract_description(body)
    if is_metaskill:
        desc = "🔗 [MetaSkill Pipeline] " + desc

    return {
        "type": "function",
        "function": {
            "name": _safe_tool_name(name),
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": (
                            f"The specific task or question for the [{name}] skill. "
                            "Pass the user's request verbatim or refined for clarity."
                        ),
                    }
                },
                "required": ["task"],
            },
        },
    }


def _safe_tool_name(name: str) -> str:
    """Convert a skill name to a safe function name: ASCII-only, lowercase.

    The OpenAI/DeepSeek API requires function names matching ^[a-zA-Z0-9_-]+$.
    Chinese and other non-ASCII characters are transliterated to a short hash.
    """
    import hashlib
    import re

    # First, extract ASCII parts (letters, digits, hyphens, underscores)
    ascii_part = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    ascii_part = re.sub(r"_+", "_", ascii_part).strip("_")

    # If we have meaningful ASCII content, use it
    if ascii_part and len(ascii_part) >= 3:
        return ascii_part.lower()[:64]

    # Otherwise, generate a short hash from the original name
    hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"skill_{hash_suffix}"


def _extract_description(body: str, max_len: int = 300) -> str:
    """Extract a description from the skill body for the tool definition."""
    lines = [l.strip() for l in body.split("\n") if l.strip()]

    # Skip headings to find first real content
    content_lines = []
    for line in lines:
        if line.startswith("#"):
            # Use the heading itself as a fallback, but keep looking
            if not content_lines:
                heading = line.lstrip("#").strip()
                if heading:
                    content_lines.append(heading)
            continue
        content_lines.append(line)

    desc = " ".join(content_lines)
    if len(desc) > max_len:
        desc = desc[: max_len - 3] + "..."
    return desc if desc else "Execute this skill."


def _build_skill_summary(skill: dict[str, Any]) -> str:
    """One-line summary of a skill for the system prompt."""
    name = skill["name"]
    body = skill["body"]
    # Use first heading line as summary
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("#"):
            return f"- **{name}**: {line.lstrip('#').strip()}"
    return f"- **{name}**"


class DispatchResult:
    """Result of a dispatch decision."""

    def __init__(
        self,
        reply: str,
        skill_used: Optional[str] = None,
        tool_called: bool = False,
    ) -> None:
        self.reply = reply
        self.skill_used = skill_used
        self.tool_called = tool_called

    def __repr__(self) -> str:
        return (
            f"DispatchResult(skill={self.skill_used!r}, "
            f"tool_called={self.tool_called!r})"
        )


def dispatch(
    user_message: str,
    conversation_history: Optional[list[dict[str, str]]] = None,
    available_skills: Optional[list[str]] = None,
    *,
    voice_mode: bool = False,
    model: str = "",
    system_extra: str = "",
) -> DispatchResult:
    """Route a user message: call a skill or respond conversationally.

    Args:
        user_message: The user's latest message.
        conversation_history: Previous turns (role: user/assistant).
        available_skills: List of skill names to consider. If None, loads all.
        model: Optional model override. If empty, uses config default.
        voice_mode: Whether to use voice-specific system prompt.

    Returns:
        DispatchResult with the reply and optional skill_used info.
    """
    client = _build_client()
    selected_model = model if model else get_config().model

    # Load skills
    skill_names = available_skills if available_skills is not None else skill_store.list_skills()

    if not skill_names:
        # No skills — just respond conversationally
        system_content = ROUTING_PROMPT_NO_TOOLS
        if voice_mode:
            system_content += "\n\n" + VOICE_SYSTEM_EXTRA
        if system_extra:
            system_content += "\n\n" + system_extra
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
        ]
        if conversation_history:
            for turn in conversation_history[-20:]:
                role = turn.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        # Add web search + fetch tools even when no skills
        from skillos.utils.web_fetch import get_tool_definition as _wf_tool
        from skillos.utils.web_search import get_tool_definition as _ws_tool
        no_skill_tools = [_ws_tool(), _wf_tool()]

        response = client.chat.completions.create(  # type: ignore[call-overload]
            model=selected_model,
            messages=messages,
            tools=no_skill_tools,
            tool_choice="auto",
            temperature=0.7,
            **get_config().to_llm_args()[3],
        )

        choice = response.choices[0]
        # If web search/fetch was called, execute it
        if choice.message.tool_calls:
            return _handle_web_tool(choice.message, messages, client, model)

        return DispatchResult(
            reply=choice.message.content or "",
        )

    # Load skill details and build tools
    all_skills = skill_store.load_all_skills_raw()
    skills_map: dict[str, dict[str, Any]] = {}
    filtered: list[dict[str, Any]] = []
    for s in all_skills:
        if s["name"] in skill_names:
            filtered.append(s)
    try:
        from skillos.knowledge.skill_routing import filter_skills_for_message
        routed = filter_skills_for_message(filtered, user_message)
        if len(routed) < len(filtered):
            logger.info(
                "Skill routing: %d/%d skills kept for message category match",
                len(routed), len(filtered),
            )
        filtered = routed
    except Exception:
        pass
    for s in filtered:
        skills_map[_safe_tool_name(s["name"])] = s

    tools = [_skill_to_tool(s) for s in skills_map.values()]
    # Context budget: proportional token allocation (LLM Wiki inspired)
    # Caps tools to fit within skills_library budget instead of a hard count
    try:
        from skillos.skills.context_budget import get_context_budget
        budget = get_context_budget()
        allocation = budget.allocate()
        tools = budget.fit_skills(tools, budget=allocation)
    except Exception:
        if len(tools) > MAX_TOOLS_PER_REQUEST:
            tools = tools[:MAX_TOOLS_PER_REQUEST]

    # Always include web search + fetch tools
    from skillos.utils.web_fetch import get_tool_definition as _wf_tool
    from skillos.utils.web_search import get_tool_definition as _ws_tool
    tools.append(_ws_tool())
    tools.append(_wf_tool())

    # Build skill summaries for system prompt
    summaries = "\n".join(
        _build_skill_summary(s) for s in skills_map.values()
    )

    # Build messages
    system_content = DISPATCHER_SYSTEM
    if voice_mode:
        system_content += "\n\n" + VOICE_SYSTEM_EXTRA
    if system_extra:
        system_content += "\n\n" + system_extra
    system_content += "\n\n" + ROUTING_PROMPT_WITH_TOOLS.format(
        skill_summaries=summaries
    )

    messages = [{"role": "system", "content": system_content}]
    if conversation_history:
        for turn in conversation_history[-20:]:
            role = turn.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": turn.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    # First LLM call: routing decision
    response = client.chat.completions.create(  # type: ignore[call-overload]
        model=selected_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.3,  # lower temp for routing accuracy
        **get_config().to_llm_args()[3],
    )

    choice = response.choices[0]
    msg = choice.message

    # If no tool call, return the conversational response
    if not msg.tool_calls:
        return DispatchResult(
            reply=msg.content or "",
        )

    # Tool was called — execute the skill
    tool_call = msg.tool_calls[0]
    func_name = tool_call.function.name
    try:
        func_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        func_args = {}
    task = func_args.get("task", user_message)

    skill = skills_map.get(func_name)

    # Handle web_search tool
    if func_name == "web_search":
        from skillos.utils.web_search import search
        query = func_args.get("query", task)
        logger.info("Web search: %s", query[:100])
        try:
            search_result = search(query)
        except Exception as exc:
            search_result = f"Search failed: {exc}"
        skill_result = search_result
        skill = None  # Don't try to load skill for web_search
    elif func_name == "web_fetch":
        from skillos.utils.web_fetch import fetch
        url = func_args.get("url", task)
        logger.info("Web fetch: %s", url[:120])
        try:
            skill_result = fetch(url)
        except Exception as exc:
            skill_result = f"Fetch failed: {exc}"
        skill = None
    elif not skill:
        return DispatchResult(
            reply=f"Sorry, I couldn't find the skill [{func_name}].",
            skill_used=func_name,
            tool_called=True,
        )

    # Execute the skill (if it's a skill, not web_search)
    if skill is not None:
        # Polymorphic dispatch: check for better variant match
        try:
            from skillos.skills.variants import dispatch_variant
            context = {"params": func_args}
            best_variant = dispatch_variant(skill["name"], context)
            if best_variant and best_variant.content:
                skill = {"name": best_variant.variant_id, "skill_doc": best_variant.content,
                         "system_prompt": best_variant.content, "model": skill.get("model", "")}
                logger.info("Variant dispatched: %s (creator=%s)", best_variant.variant_id, best_variant.creator)
        except Exception:
            pass  # Fall through to original skill execution

        logger.info("Executing skill: %s | task: %s", skill["name"], task[:100])

        # Runtime tool validation: check if skill's required tools are available
        try:
            from skillos.skills.tool_registry import get_registry
            readiness = get_registry().check_skill_readiness(skill["name"])
            if not readiness["ready"]:
                missing_tools = ", ".join(readiness["missing"])
                skill_result = (
                    f"⚠️ 技能「{skill['name']}」无法执行：缺少工具 {missing_tools}。\n"
                    f"可用工具: {', '.join(t.name for t in get_registry().list_tools())}\n"
                    f"请先注册并验证所需工具。"
                )
                # Compose final reply with the error
                messages.append({
                    "role": "assistant", "content": None,
                    "tool_calls": [{
                        "id": tool_call.id, "type": "function",
                        "function": {"name": func_name, "arguments": tool_call.function.arguments},
                    }],
                })
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": skill_result})
                final_response = client.chat.completions.create(
                    model=selected_model, messages=messages, temperature=0.7, **get_config().to_llm_args()[3],
                )
                return DispatchResult(
                    reply=final_response.choices[0].message.content or skill_result,
                    skill_used=skill["name"], tool_called=True,
                )
        except Exception as e:
            logger.warning("Non-critical in dispatcher.py: %s", e)
            pass  # Tool registry unavailable — skip validation

        try:
            skill_doc_raw = skill_store.get_skill_body(skill_store.load_skill(skill["name"]))

            # Check if MetaSkill — run as pipeline
            if "type: metaskill" in skill_doc_raw[:200]:
                from skillos.skills.metaskill import parse_metaskill, run_pipeline
                ms = parse_metaskill(skill_doc_raw)
                if ms and ms.steps:
                    cfg2 = get_config()
                    llm_args = (cfg2.api_key, cfg2.base_url, cfg2.model, cfg2.to_llm_args()[3])
                    result = run_pipeline(ms, {"user_input": task}, llm_args=llm_args)
                    if result.success:
                        parts = [f"## Pipeline: {ms.name}\n"]
                        for i, t in enumerate(result.trace):
                            parts.append(f"{i+1}. {t}")
                        parts.append("\n## Results")
                        for k, v in result.outputs.items():
                            parts.append(f"\n### {k}\n{v[:500]}")
                        skill_result = "\n".join(parts)
                    else:
                        skill_result = f"Pipeline failed: {result.errors}"
                else:
                    skill_result = "MetaSkill pipeline is invalid or empty"
            else:
                agent = agent_factory.create_agent(skill_doc_raw)
                skill_result = agent_factory.run_agent(agent, task)
        except Exception as exc:
            skill_result = f"Skill execution error: {exc}"
            logger.error("Skill [%s] execution failed: %s", skill["name"], exc)

    # Second LLM call: compose the final reply incorporating skill output
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": tool_call.function.arguments,
                },
            }
        ],
    })
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": skill_result,
    })

    # Ask the LLM to compose a natural response incorporating the skill output
    compose_system = (
        "You are a helpful AI companion. The user asked you to use a skill, "
        "and the skill's output is provided above. Present the results naturally "
        "and conversationally. If the skill output is long, summarize the key "
        "points. Always respond in Chinese (中文) unless the user explicitly "
        "asks for another language."
    )

    # Replace system message for composition
    compose_messages = [
        {"role": "system", "content": compose_system},
    ] + messages[1:]  # skip original system message

    final_response = client.chat.completions.create(
        model=selected_model,
        messages=compose_messages,
        temperature=0.7,
        **get_config().to_llm_args()[3],
    )

    return DispatchResult(
        reply=final_response.choices[0].message.content or skill_result,
        skill_used=skill["name"] if skill else func_name,
        tool_called=True,
    )


def _handle_web_tool(
    msg, messages: list[dict[str, Any]], client, model: str
) -> DispatchResult:
    """Execute web_search or web_fetch tool and compose final response."""
    import json

    tool_call = msg.tool_calls[0]
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        args = {}
    func_name = tool_call.function.name

    if func_name == "web_fetch":
        from skillos.utils.web_fetch import fetch
        url = args.get("url", "")
        logger.info("Web fetch (no-skill): %s", url[:120])
        tool_result = fetch(url)
    else:
        from skillos.utils.web_search import search
        query = args.get("query", "")
        logger.info("Web search (no-skill): %s", query[:100])
        tool_result = search(query)

    messages.append({
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": tool_call.id, "type": "function",
            "function": {"name": func_name, "arguments": tool_call.function.arguments},
        }],
    })
    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})

    compose_system = (
        "You are a helpful AI companion. Use the results above to answer "
        "the user's question naturally. Always respond in Chinese (中文)."
    )

    final_response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": compose_system}] + messages[1:],
        temperature=0.7,
        **get_config().to_llm_args()[3],
    )
    return DispatchResult(
        reply=final_response.choices[0].message.content or tool_result,
        tool_called=True,
    )


def quick_dispatch(user_message: str) -> DispatchResult:
    """Convenience wrapper — dispatches with all available skills, no history."""
    return dispatch(user_message)
