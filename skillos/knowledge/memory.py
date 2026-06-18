"""Conversation Memory — persist AI conversation insights as knowledge assets.

Two layers:
  1. Global memory (ConversationMemory) — HereVault-inspired, cross-session insights
  2. Per-skill memory — user preferences, past decisions, conversation history
     Stored at: skills/{name}/memory.json  (ported from Skill Distiller's skill_memory.py)
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

_log = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".skillos" / "memories"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


# ═══════════════════════════════════════════════════════════════
# 1. Per-skill memory (ported from Skill Distiller)
# ═══════════════════════════════════════════════════════════════

def _skill_mem_path(skill_name: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', '_', skill_name)[:64]
    return SKILLS_DIR / safe / "memory.json"


def _skill_mem_load(skill_name: str) -> dict:
    p = _skill_mem_path(skill_name)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _skill_mem_save(skill_name: str, data: dict) -> None:
    p = _skill_mem_path(skill_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_conversation(skill_name: str, role: str, text: str) -> None:
    """Record a conversation turn for a skill."""
    mem = _skill_mem_load(skill_name)
    mem.setdefault("conversations", []).append({
        "role": role, "text": text[:500],
        "time": datetime.now().isoformat()[:19],
    })
    if len(mem["conversations"]) > 50:
        mem["conversations"] = mem["conversations"][-50:]
    _skill_mem_save(skill_name, mem)


def set_preference(skill_name: str, key: str, value: str) -> None:
    """Set a user preference for a skill (e.g., preferred_style, tone)."""
    mem = _skill_mem_load(skill_name)
    mem.setdefault("preferences", {})[key] = value
    _skill_mem_save(skill_name, mem)


def get_preference(skill_name: str, key: str, default: str = "") -> str:
    """Get a user preference."""
    return _skill_mem_load(skill_name).get("preferences", {}).get(key, default)


def record_decision(skill_name: str, context: str, choice: str) -> None:
    """Record a design decision made by the user during skill creation."""
    mem = _skill_mem_load(skill_name)
    mem.setdefault("decisions", []).append({
        "context": context[:200], "choice": choice[:200],
        "time": datetime.now().isoformat()[:19],
    })
    _skill_mem_save(skill_name, mem)


def get_context(skill_name: str) -> str:
    """Get consolidated memory context for LLM prompt injection."""
    mem = _skill_mem_load(skill_name)
    parts = []

    prefs = mem.get("preferences", {})
    if prefs:
        parts.append("## 用户偏好\n" + "\n".join(f"- {k}: {v}" for k, v in prefs.items()))

    decisions = mem.get("decisions", [])
    if decisions:
        parts.append("## 历史决策\n" + "\n".join(
            f"- {d['context'][:80]}: 选择了「{d['choice'][:80]}」" for d in decisions[-5:]
        ))

    convos = mem.get("conversations", [])
    if convos:
        parts.append("## 近期对话\n" + "\n".join(
            f"[{c['role']}] {c['text'][:120]}" for c in convos[-8:]
        ))

    return "\n\n".join(parts) if parts else ""


def clear_memory(skill_name: str) -> None:
    """Clear all per-skill memory for a skill."""
    p = _skill_mem_path(skill_name)
    if p.exists():
        p.unlink()


# ═══════════════════════════════════════════════════════════════
# 2. Global conversation memory (HereVault-inspired)
# ═══════════════════════════════════════════════════════════════


class ConversationMemory:
    """Persist and search insights from AI conversations."""

    def __init__(self):
        self.memory_file = MEMORY_DIR / "memories.jsonl"

    def save_insight(self, content, category="insight", source_session="", confidence=0.7):
        entry = {
            "id": f"mem_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            "content": content,
            "category": category,
            "source_session": source_session,
            "confidence": confidence,
            "created_at": time.time(),
        }
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def search(self, query, top_k=5):
        if not self.memory_file.exists():
            return []
        qwords = set(re.findall(r"[\w一-鿿]{2,}", query.lower()))
        results = []
        with open(self.memory_file, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    ewords = set(re.findall(r"[\w一-鿿]{2,}", e.get("content", "").lower()))
                    s = len(qwords & ewords) / max(len(qwords), 1)
                    if s > 0:
                        results.append((s, e))
                except json.JSONDecodeError:
                    pass
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]

    def extract(self, messages):
        if not messages:
            return []
        text = "\n".join(
            f"{m.get('role','?')}: {m.get('content','')[:200]}" for m in messages[-10:]
        )
        try:
            from skillos.llm_client import call
            prompt = f"Extract insights (preference|fact|decision|insight) from:\n{text}\nOutput JSON array."
            raw = call(prompt, max_tokens=600, temperature=0.2)
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            items = json.loads(m.group(0)) if m else []
            return [
                self.save_insight(
                    i["content"],
                    i.get("category", "insight"),
                    confidence=i.get("confidence", 0.7),
                )
                for i in items if i.get("content")
            ]
        except Exception as e:
            _log.warning("Extraction failed: %s", e)
            return []
