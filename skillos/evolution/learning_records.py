"""Learning Records — track what the user has mastered per skill.

Inspired by Teach's learning-records/ — a file-system state machine
that remembers what you've learned, what you're confused about,
and adjusts the teaching accordingly (ZPD: Zone of Proximal Development).
"""


import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


@dataclass
class StepRecord:
    """What the user knows about one step of a skill."""

    step: str          # e.g., "S_body.步骤1" or "S_trigger"
    status: str = "new"  # new | learning | learned | confused | mastered
    confidence: float = 0.0
    note: str = ""     # user's note or AI's observation
    updated_at: float = 0.0


@dataclass
class LearningRecord:
    """Full learning state for one skill — like Teach's learning-records/."""

    skill_name: str
    steps: list[StepRecord] = field(default_factory=list)
    overall_confidence: float = 0.0
    last_session_at: float = 0.0
    total_sessions: int = 0
    user_goal: str = ""       # why the user wants to learn this (like MISSION.md)
    glossary: dict[str, str] = field(default_factory=dict)  # shared term definitions


def _record_path(skill_name: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', '_', skill_name)[:64]
    return SKILLS_DIR / safe / "learning-records" / "learned.json"


def load(skill_name: str) -> LearningRecord:
    """Load learning records for a skill."""
    path = _record_path(skill_name)
    if not path.exists():
        return LearningRecord(skill_name=skill_name)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        record = LearningRecord(
            skill_name=data.get("skill_name", skill_name),
            overall_confidence=data.get("overall_confidence", 0.0),
            last_session_at=data.get("last_session_at", 0),
            total_sessions=data.get("total_sessions", 0),
            user_goal=data.get("user_goal", ""),
            glossary=data.get("glossary", {}),
        )
        for s in data.get("steps", []):
            record.steps.append(StepRecord(
                step=s["step"], status=s.get("status", "new"),
                confidence=s.get("confidence", 0.0),
                note=s.get("note", ""), updated_at=s.get("updated_at", 0),
            ))
        return record
    except Exception as e:
        _log.warning("Failed to load learning records: %s", e)
        return LearningRecord(skill_name=skill_name)


def save(record: LearningRecord) -> None:
    """Save learning records to disk."""
    path = _record_path(record.skill_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "skill_name": record.skill_name,
        "steps": [
            {"step": s.step, "status": s.status, "confidence": s.confidence,
             "note": s.note, "updated_at": s.updated_at}
            for s in record.steps
        ],
        "overall_confidence": record.overall_confidence,
        "last_session_at": record.last_session_at,
        "total_sessions": record.total_sessions,
        "user_goal": record.user_goal,
        "glossary": record.glossary,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_step(skill_name: str, step: str, status: str, note: str = "") -> None:
    """Mark a single step as learned/confused/mastered."""
    record = load(skill_name)
    now = time.time()

    # Find existing or create new
    for s in record.steps:
        if s.step == step:
            s.status = status
            s.confidence = 1.0 if status in ("learned", "mastered") else s.confidence
            s.note = note
            s.updated_at = now
            break
    else:
        record.steps.append(StepRecord(
            step=step, status=status,
            confidence=1.0 if status in ("learned", "mastered") else 0.3,
            note=note, updated_at=now,
        ))

    _update_overall(record)
    record.last_session_at = now
    save(record)


def start_session(skill_name: str, user_goal: str = "") -> LearningRecord:
    """Called when user begins working with a skill. Records the session."""
    record = load(skill_name)
    record.total_sessions += 1
    record.last_session_at = time.time()
    if user_goal:
        record.user_goal = user_goal
    save(record)
    return record


def add_glossary_term(skill_name: str, term: str, definition: str) -> None:
    """Add a shared term definition — like Teach's GLOSSARY.md."""
    record = load(skill_name)
    record.glossary[term] = definition
    save(record)


def get_zpd_context(skill_name: str) -> str:
    """Generate a ZPD context block for the extraction agent.

    Tells the agent what the user already knows (skip this),
    what they're confused about (focus here), and what's next.
    """
    record = load(skill_name)
    if not record.steps:
        return ""

    learned = [s for s in record.steps if s.status in ("learned", "mastered")]
    confused = [s for s in record.steps if s.status == "confused"]
    new_steps = [s for s in record.steps if s.status == "new"]

    lines = ["\n## 📚 学习记录（ZPD 最近发展区）\n"]
    lines.append(f"总课时: {record.total_sessions} | 整体信心: {record.overall_confidence:.0%}")

    if learned:
        lines.append(f"\n### ✅ 已掌握 ({len(learned)} 项) — 跳过")
        for s in learned[-5:]:
            lines.append(f"- {s.step}")

    if confused:
        lines.append(f"\n### 🤔 有疑问 ({len(confused)} 项) — 聚焦这里")
        for s in confused:
            lines.append(f"- {s.step}: {s.note}")

    if new_steps:
        lines.append(f"\n### 📖 未学 ({len(new_steps)} 项) — 下一步")

    if record.glossary:
        lines.append(f"\n### 📖 术语共识 ({len(record.glossary)} 项)")
        for term, defn in list(record.glossary.items())[:5]:
            lines.append(f"- {term}: {defn}")

    return "\n".join(lines)


def _update_overall(record: LearningRecord) -> None:
    if not record.steps:
        record.overall_confidence = 0.0
        return
    weights = {"mastered": 1.0, "learned": 0.8, "learning": 0.4, "confused": 0.2, "new": 0.0}
    total = sum(weights.get(s.status, 0) for s in record.steps)
    record.overall_confidence = total / len(record.steps) if record.steps else 0.0
