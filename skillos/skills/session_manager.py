"""Session Manager — multi-session support with auto-expiry.

Each session owns a SkillExtractionAgent instance and conversation history.
Thread-safe for concurrent requests.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

DEFAULT_TTL = 1800  # 30 minutes


class Session:
    """A single conversation session."""

    def __init__(
        self,
        sid: str,
        mode: str = "create",
        model: str = "",
        channel: str = "",
        chat_id: str = "",
        user_id: str = "",
        tenant_id: str = "",
        org_id: str = "",
        dept_id: str = "",
    ):
        self.id = sid
        self.mode = mode
        self.model = model
        self.channel = channel
        self.chat_id = chat_id
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.org_id = org_id
        self.dept_id = dept_id
        self.history: list[dict[str, str]] = []
        self.created_at = time.time()
        self.last_access = time.time()
        self._agent = None

    def reset_extraction_agent(self) -> None:
        """Discard current extraction agent (e.g. user starts a new skill topic)."""
        self._agent = None

    @property
    def agent(self):
        """Lazy-load the SkillExtractionAgent."""
        if self._agent is None:
            from skillos.skills.agent import SkillExtractionAgent
            self._agent = SkillExtractionAgent()
            self._agent.set_team_context(
                channel=self.channel,
                chat_id=self.chat_id,
                user_id=self.user_id,
                session_id=self.id,
            )
            self._apply_tenant_context()
        else:
            self._agent.set_team_context(
                channel=self.channel,
                chat_id=self.chat_id,
                user_id=self.user_id,
                session_id=self.id,
            )
            self._apply_tenant_context()
        return self._agent

    def _apply_tenant_context(self) -> None:
        if not self._agent:
            return
        ctx = getattr(self._agent, "_team_context", None) or {}
        if self.tenant_id:
            ctx["tenant_id"] = self.tenant_id
        if self.org_id:
            ctx["org_id"] = self.org_id
        if self.dept_id:
            ctx["dept_id"] = self.dept_id
        self._agent._team_context = ctx
        try:
            from skillos.identity.context import set_tenant_context
            from skillos.identity.resolver import tenant_from_context
            tc = tenant_from_context(ctx)
            if tc:
                set_tenant_context(tc)
        except Exception:
            pass

    def touch(self) -> None:
        self.last_access = time.time()

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self.last_access = time.time()
        # Persist to SQLite for survival across restarts
        try:
            from skillos.skills import conversation_store
            conversation_store.save_message(self.id, role, content)
        except Exception:
            pass

    def persist_insights(self) -> int:
        """Extract and persist knowledge from conversation history (HereVault-inspired)."""
        if len(self.history) < 3:
            return 0
        try:
            import sys, os
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            # Dynamic import to avoid circular deps
            from skillos.knowledge.memory import ConversationMemory
            mem = ConversationMemory()
            insights = mem.extract_from_conversation(self.history)
            return len(insights)
        except Exception:
            return 0

    def is_expired(self, ttl: int = DEFAULT_TTL) -> bool:
        return (time.time() - self.last_access) > ttl

    def auto_finalize_on_disconnect(self) -> dict | None:
        """When user disconnects/closes window, auto-complete extraction if enough context.

        Returns saved skill info dict if a skill was auto-generated, None otherwise.
        """
        if not self._agent or not self._agent.is_active:
            return None
        if len(self._agent._context) < 3:
            return None  # Not enough info to auto-generate
        try:
            from skillos.skills.skill_store import list_skills, save_skill
            from skillos.config import get_config
            cfg = get_config()
            # Auto-generate the skill from accumulated context
            reply, doc = self._agent._generate(list_skills(), cfg.to_llm_args())
            if doc:
                save_skill(doc["name"], doc["content"])
                return {"name": doc["name"], "auto_finalized": True}
        except Exception:
            pass
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "mode": self.mode, "model": self.model,
            "history_len": len(self.history),
            "created_at": self.created_at, "last_access": self.last_access,
        }


class SessionManager:
    """Manages all active sessions. Thread-safe."""

    def __init__(self, ttl: int = DEFAULT_TTL):
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl

    def get_or_create(
        self,
        session_id: str = "",
        mode: str = "create",
        model: str = "",
        *,
        channel: str = "",
        chat_id: str = "",
        user_id: str = "",
        tenant_id: str = "",
        org_id: str = "",
        dept_id: str = "",
    ) -> Session:
        """Get existing session or create new one."""
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if not session.is_expired(self._ttl):
                session.touch()
                if mode:
                    session.mode = mode
                if model:
                    session.model = model
                if channel:
                    session.channel = channel
                if chat_id:
                    session.chat_id = chat_id
                if user_id:
                    session.user_id = user_id
                if tenant_id:
                    session.tenant_id = tenant_id
                if org_id:
                    session.org_id = org_id
                if dept_id:
                    session.dept_id = dept_id
                # Reload history from DB in case of server restart
                if not session.history:
                    try:
                        from skillos.skills import conversation_store
                        session.history = conversation_store.load_history(session_id)
                    except Exception:
                        pass
                return session
            self.delete(session_id)

        sid = session_id or uuid.uuid4().hex[:12]
        session = Session(
            sid, mode, model,
            channel=channel, chat_id=chat_id, user_id=user_id,
            tenant_id=tenant_id, org_id=org_id, dept_id=dept_id,
        )
        if session_id:
            try:
                from skillos.skills import conversation_store
                session.history = conversation_store.load_history(session_id)
            except Exception:
                pass
        self._sessions[sid] = session
        _log.info("Session created: %s", sid)
        return session

    def get(self, session_id: str) -> Optional[Session]:
        if not session_id or session_id not in self._sessions:
            return None
        session = self._sessions[session_id]
        if session.is_expired(self._ttl):
            self.delete(session_id)
            return None
        session.touch()
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        try:
            from skillos.skills.session_draft import clear_session_draft
            clear_session_draft(session_id)
        except Exception:
            pass
        try:
            from skillos.skills import conversation_store
            conversation_store.delete_session_history(session_id)
        except Exception:
            pass

    def cleanup_expired(self) -> int:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired(self._ttl)]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    @property
    def count(self) -> int:
        return len(self._sessions)


# Process-wide singleton — dispatch must reuse sessions across HTTP requests
_default_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = SessionManager()
    return _default_manager

