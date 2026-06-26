"""LLM Client — unified call interface across providers.

Hermes-compatible: uses the OpenAI-compatible interface that Hermes also uses.
Supports DeepSeek, OpenAI, Anthropic, and any OpenAI-compatible endpoint.
"""

import logging
from typing import Optional

from openai import OpenAI

from skillos.config import get_config

_log = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create OpenAI-compatible client from config."""
    global _client
    if _client is None:
        cfg = get_config()
        _client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
    return _client


def call(
    prompt: str = "",
    *,
    model: str = "",
    max_tokens: int = 600,
    temperature: float = 0.2,
    system: str = "",
    messages: list[dict[str, str]] | None = None,
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    max_retries: int = 3,
) -> str:
    """Call LLM and return text response with exponential backoff retry.

    Args:
        prompt: User message content (ignored if messages is provided)
        model: Model override (uses config default if empty)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0.0-2.0)
        system: Optional system prompt
        messages: Full message list (overrides prompt if provided)
        tools: OpenAI tool definitions for function calling
        tool_choice: Tool choice mode ("auto", "none", "required")
        max_retries: Max retry attempts on transient errors (429/503)

    Returns:
        Response text, or empty string on failure
    """
    import time

    cfg = get_config()
    client = get_client()
    model_name = model or cfg.model

    try:
        from skillos.billing.usage import QuotaExceededError, check_llm_quota
        from skillos.identity.context import get_tenant_context
        ctx = get_tenant_context()
        if ctx:
            check_llm_quota(ctx.tenant_id, ctx.user_id, ctx.dept_id)
    except QuotaExceededError:
        raise
    except Exception:
        pass

    if messages is None:
        msgs: list[dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
    else:
        msgs = list(messages)
        if system and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": system})

    import os
    if os.getenv("SKILLOS_SKIP_DESENSITIZE", "").lower() not in ("1", "true", "yes"):
        from skillos.security.desensitize import desensitize_messages
        msgs = desensitize_messages(msgs)

    create_kwargs = cfg.to_llm_args()[3]
    if tools:
        create_kwargs["tools"] = tools
        create_kwargs["tool_choice"] = tool_choice

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=msgs,
                max_tokens=max_tokens,
                temperature=temperature,
                **create_kwargs,
            )
            text = (response.choices[0].message.content or "").strip()
            try:
                from skillos.billing.usage import record_llm_usage
                from skillos.identity.context import get_tenant_context
                ctx = get_tenant_context()
                if ctx:
                    record_llm_usage(ctx.tenant_id, ctx.user_id, ctx.dept_id)
            except Exception:
                pass
            return text
        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(
                code in error_str
                for code in ("429", "503", "rate", "throttl", "overload", "timeout", "capacity")
            )
            if is_retryable and attempt < max_retries:
                wait = 2 ** attempt
                _log.warning("LLM retry %d/%d in %ds: %s", attempt + 1, max_retries, wait, e)
                time.sleep(wait)
                continue
            # Graceful degradation: try Ollama as fallback
            if attempt == max_retries and cfg.api_key != "ollama":
                _log.warning("Primary model failed, trying Ollama fallback...")
                try:
                    fallback = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
                    fb_resp = fallback.chat.completions.create(  # type: ignore[call-overload,arg-type]
                        model="llama3.2", messages=msgs,
                        max_tokens=max_tokens, temperature=temperature,
                    )
                    return (fb_resp.choices[0].message.content or "").strip()
                except Exception as fb_e:
                    _log.error("Ollama fallback also failed: %s", fb_e)
            _log.error("LLM call failed (model=%s, attempt=%d): %s", model_name, attempt, e)
            return "<SkillOS: LLM unavailable. Check your API key or install Ollama for local mode.>"
    return "<SkillOS: LLM unavailable.>"


def call_with_tools(
    prompt: str = "",
    tools: list[dict] | None = None,
    *,
    model: str = "",
    system: str = "",
    messages: list[dict[str, str]] | None = None,
    max_tokens: int = 600,
    temperature: float = 0.7,
) -> tuple[str, list | None]:
    """LLM call that may return tool calls.

    Returns:
        (text_content, tool_calls_or_None)
    """
    cfg = get_config()
    client = get_client()
    model_name = model or cfg.model

    if messages is None:
        msgs: list[dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
    else:
        msgs = list(messages)
        if system and (not msgs or msgs[0].get("role") != "system"):
            msgs.insert(0, {"role": "system", "content": system})

    create_kwargs = cfg.to_llm_args()[3]

    resp = client.chat.completions.create(  # type: ignore[call-overload,arg-type]
        model=model_name,
        messages=msgs,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools or [],
        tool_choice="auto",
        **create_kwargs,
    )
    choice = resp.choices[0]
    msg = choice.message
    return msg.content or "", msg.tool_calls
