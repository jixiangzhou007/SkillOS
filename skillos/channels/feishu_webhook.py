"""Feishu bot α — message events → SkillOS dispatch (Sprint 3)."""

from __future__ import annotations

import json
import logging

_log = logging.getLogger(__name__)


def parse_feishu_message(body: dict) -> dict | None:
    """Extract text, chat_id, user_id from Feishu event v2 payload."""
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge", "")}

    header = body.get("header") or {}
    event_type = header.get("event_type", "")
    if event_type not in ("im.message.receive_v1", "im.message.message_received_v1"):
        return None

    event = body.get("event") or {}
    message = event.get("message") or {}
    sender = event.get("sender") or {}

    content_raw = message.get("content", "{}")
    try:
        content = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
    except json.JSONDecodeError:
        content = {"text": str(content_raw)}

    text = (content.get("text") or "").strip()
    if not text:
        return None

    user_id = ""
    sid = sender.get("sender_id") or {}
    user_id = sid.get("open_id") or sid.get("user_id") or sender.get("open_id", "")

    return {
        "text": text,
        "chat_id": message.get("chat_id", ""),
        "user_id": user_id,
        "message_id": message.get("message_id", ""),
    }


async def handle_feishu_event(body: dict, *, auth_token: str = "") -> dict:
    """Route Feishu message to dispatch; return reply payload."""
    parsed = parse_feishu_message(body)
    if parsed is None:
        return {"ok": True, "ignored": True}
    if "challenge" in parsed:
        return {"challenge": parsed["challenge"]}

    from skillos.config import get_config
    from skillos.skills.session_manager import get_session_manager
    from skillos.channels.session_ids import resolve_session_id

    cfg = get_config()
    tenant_id = org_id = dept_id = ""
    if auth_token:
        from skillos.identity.middleware import auth_from_token
        ctx = auth_from_token(auth_token)
        if ctx:
            tenant_id = ctx.tenant_id
            org_id = ctx.org_id
            dept_id = ""

    resolved = resolve_session_id(
        "",
        channel="feishu",
        chat_id=parsed["chat_id"],
        user_id=parsed["user_id"],
    )
    mgr = get_session_manager()
    session = mgr.get_or_create(
        resolved,
        "chat",
        cfg.model,
        channel="feishu",
        chat_id=parsed["chat_id"],
        user_id=parsed["user_id"],
        tenant_id=tenant_id,
        org_id=org_id,
        dept_id=dept_id,
    )

    from skillos.skills.intent_router import (
        classify_message_intent,
        DispatchIntent,
        is_meta_extraction_question,
    )

    agent = session.agent
    if not agent.is_active and session.history:
        agent.restore_from_history(session.history)

    intent = classify_message_intent(parsed["text"], extraction_active=agent.is_active)
    if intent == DispatchIntent.EXTRACT or agent.is_active or parsed["text"].strip().startswith("帮我"):
        if agent.is_active and is_meta_extraction_question(parsed["text"]):
            reply = agent.reply_to_meta_question()
        elif agent.is_active and agent.should_start(parsed["text"]) and not is_meta_extraction_question(parsed["text"]):
            session.reset_extraction_agent()
            agent = session.agent
            reply, _doc = agent.handle(parsed["text"], [], cfg.to_llm_args())
        elif agent.is_active:
            reply, _doc = agent.handle(parsed["text"], [], cfg.to_llm_args())
        elif is_meta_extraction_question(parsed["text"]):
            reply = (
                "我们还没开始具体的技能沉淀。"
                "你可以直接说想沉淀什么流程，比如「合同审核」或「退款处理」。"
            )
        else:
            reply, _doc = agent.handle(parsed["text"], [], cfg.to_llm_args())
        session.add_turn("user", parsed["text"])
        session.add_turn("assistant", reply)
        from skillos.skills.extraction_helpers import attach_extraction_actions
        body = {
            "ok": True,
            "reply": reply,
            "session_id": session.id,
            "intent": "extract",
            "skill_active": agent.is_active,
        }
        return attach_extraction_actions(body, reply)

    session.add_turn("user", parsed["text"])
    try:
        from skillos.llm_client import call
        reply = call(
            f"用户说：{parsed['text']}\n请简短回复。",
            model=cfg.model,
            max_tokens=300,
            temperature=0.3,
        )
    except Exception as e:
        reply = f"处理失败: {e}"
    session.add_turn("assistant", reply)
    return {"ok": True, "reply": reply, "session_id": session.id, "intent": "chat"}
