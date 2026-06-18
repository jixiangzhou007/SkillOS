"""Human Learning Theory — applied to Skill Distiller's learning engine.

Five mechanisms inspired by cognitive science:
1. Metacognitive Uncertainty  — Skills express confidence per step (Flavell)
2. Skill Staleness & Reinforcement — Unused skills degrade (Ebbinghaus)
3. Recursive Feynman — Explain it again, simpler (Feynman Technique)
4. Analogical Transfer — Find structural similarities across domains
5. Learning Journal — Timeline of what was learned, from where, reflections

Philosophy: The system doesn't just store skills — it maintains a learning state
that evolves over time, like a human's understanding.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

JOURNAL_PATH = Path(__file__).parent / "knowledge" / "learning_journal.jsonl"
STALENESS_PATH = Path(__file__).parent / "knowledge" / "skill_state.json"


# ═══════════════════════════════════════════════════════════════
# 1. Metacognitive Uncertainty
# ═══════════════════════════════════════════════════════════════

@dataclass
class StepConfidence:
    """How confident the system is about each part of a skill."""

    step_name: str
    confidence: float  # 0-1
    reason: str = ""   # why uncertain, if applicable

    @property
    def is_certain(self) -> bool:
        return self.confidence >= 0.8

    @property
    def needs_review(self) -> bool:
        return self.confidence < 0.5


def assess_skill_confidence(skill_content: str, llm_args: tuple) -> list[StepConfidence]:
    """Metacognitive assessment: how confident is the system about each step?

    Uses Flavell's metacognition model: the system reflects on its own knowledge.
    """
    from skillos.llm_client import call

    prompt = f"""你是技能文档的元认知审核员。对以下技能文档的每个 S_body 步骤，评估信心。

## 技能文档
```
{skill_content[:2000]}
```

## 输出格式（严格每行一个）
对每个步骤输出一行: 步骤名 | 信心(0-1) | 原因
例如: 读取输入 | 0.3 | 描述太模糊，不知道输入来源

只输出步骤行，不要其他内容。"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=400, temperature=0.1)
        results = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|", 2)]
            if len(parts) >= 2:
                try:
                    conf_val = float(parts[1])
                except ValueError:
                    conf_val = 0.5
                reason = parts[2] if len(parts) > 2 else ""
                results.append(StepConfidence(
                    step_name=parts[0][:60],
                    confidence=conf_val,
                    reason=reason[:120],
                ))
        return results
    except Exception as e:
        _log.warning("Metacognitive assessment failed: %s", e)
        return []


def add_confidence_to_skill(skill_content: str, confidences: list[StepConfidence]) -> str:
    """Annotate a skill document with confidence markers."""
    if not confidences:
        return skill_content

    # Add metacognitive section
    uncertain = [c for c in confidences if c.confidence < 0.7]
    if not uncertain:
        return skill_content

    meta_section = "\n\n## 🧠 元认知评估\n"
    for c in uncertain[:5]:
        icon = "⚠️" if c.confidence < 0.5 else "💡"
        meta_section += f"- {icon} **{c.step}**: 信心 {c.confidence:.0%} — {c.reason}\n"

    return skill_content + meta_section


# ═══════════════════════════════════════════════════════════════
# 2. Skill Staleness & Reinforcement (Ebbinghaus Forgetting Curve)
# ═══════════════════════════════════════════════════════════════

@dataclass
class SkillState:
    """The 'memory state' of a skill — evolves over time like human memory."""

    skill_name: str
    created_at: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    reinforcement_count: int = 0  # times re-learned/refreshed
    base_confidence: float = 0.5   # starts low, grows with use

    @property
    def staleness(self) -> float:
        """0 = fresh, 1 = completely forgotten (Ebbinghaus curve approximation)."""
        if self.last_used == 0:
            return 0.5  # never used → moderately stale
        days_since_use = (time.time() - self.last_used) / 86400
        # Simplified forgetting curve: decays by ~20% per week
        return min(1.0, days_since_use / 35)  # fully stale after ~5 weeks

    @property
    def effective_confidence(self) -> float:
        """Base confidence adjusted for staleness and reinforcement."""
        # More use → higher base
        use_bonus = min(0.3, self.use_count * 0.05)
        # More reinforcement → slower decay
        decay_resistance = min(0.5, self.reinforcement_count * 0.1)
        # Apply staleness
        adjusted = (self.base_confidence + use_bonus) * (1 - self.staleness * (1 - decay_resistance))
        return max(0.1, min(1.0, adjusted))

    def record_use(self) -> None:
        self.last_used = time.time()
        self.use_count += 1

    def record_reinforcement(self) -> None:
        """Called when skill is re-learned (e.g., optimized, re-encountered via URL)."""
        self.last_used = time.time()
        self.reinforcement_count += 1
        self.base_confidence = min(1.0, self.base_confidence + 0.1)


def load_skill_state() -> dict[str, SkillState]:
    """Load all skill states from disk."""
    if not STALENESS_PATH.exists():
        return {}
    try:
        data = json.loads(STALENESS_PATH.read_text(encoding="utf-8"))
        return {
            k: SkillState(
                skill_name=k,
                created_at=v.get("created_at", 0),
                last_used=v.get("last_used", 0),
                use_count=v.get("use_count", 0),
                reinforcement_count=v.get("reinforcement_count", 0),
                base_confidence=v.get("base_confidence", 0.5),
            )
            for k, v in data.items()
        }
    except Exception:
        return {}


def save_skill_states(states: dict[str, SkillState]) -> None:
    STALENESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        k: {
            "created_at": s.created_at, "last_used": s.last_used,
            "use_count": s.use_count, "reinforcement_count": s.reinforcement_count,
            "base_confidence": s.base_confidence,
        }
        for k, s in states.items()
    }
    STALENESS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def check_template_staleness(skill_name: str) -> Optional[str]:
    """Check if a skill's templates might need updating.
    Returns a suggestion message, or None if everything is fresh.
    """
    try:
        from knowledge import skill_kb
        kb = skill_kb.load_kb(skill_name)
        if not kb.templates:
            return None
        oldest = min((t.created_at for t in kb.templates), default=0)
        if oldest == 0:
            return None
        days = (time.time() - oldest) / 86400
        if days > 30:
            return (f"📄 「{skill_name}」的参考模板已 {days:.0f} 天未更新。"
                    f"模板是否有变化？如有新版本可以发给我更新。")
    except Exception:
        pass
    return None


def refresh_skill(skill_name: str) -> Optional[SkillState]:
    """Record that a skill was used/encountered. Returns updated state."""
    states = load_skill_state()
    if skill_name not in states:
        states[skill_name] = SkillState(skill_name=skill_name, created_at=time.time())
    states[skill_name].record_use()
    save_skill_states(states)
    return states[skill_name]


def get_stale_skills(days: int = 14) -> list[str]:
    """List skills that haven't been used in N days (need refreshing)."""
    states = load_skill_state()
    return [name for name, s in states.items()
            if s.staleness > 0.5 and s.effective_confidence < 0.6]


# ═══════════════════════════════════════════════════════════════
# 3. Recursive Feynman — Explain it again, simpler
# ═══════════════════════════════════════════════════════════════

def recursive_feynman(skill_content: str, llm_args: tuple) -> tuple[str, bool]:
    """After generating a skill, try explaining it in simpler terms.

    If the simpler explanation is significantly different → understanding deepened.
    If it's almost the same → the original was already clear enough.

    Returns (simpler_version, deepened).
    """
    from skillos.llm_client import call

    prompt = f"""你现在要像一个老师在教一个完全不懂这个领域的学生。

## 原始技能文档
```
{skill_content[:2000]}
```

## 任务
用更简单的语言重写这个技能的核心步骤。规则：
1. 每个步骤用一句话说清楚
2. 用日常类比（比如"这就像..."）
3. 假设读者没有任何专业背景
4. 如果你在某个步骤发现自己说不清楚 → 标注 [这里我需要再想想]

## 输出
用 ```skill_doc ... ``` 围栏输出简化版。"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=1500, temperature=0.3)
        m = re.search(r"```skill_doc\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        simpler = m.group(1).strip() if m else raw.strip()

        # Check if understanding deepened (simpler version is significantly different)
        deepened = "[这里我需要再想想]" in simpler or len(simpler) < len(skill_content) * 0.7

        return simpler, deepened
    except Exception:
        return skill_content, False


# ═══════════════════════════════════════════════════════════════
# 4. Analogical Transfer — Find structural similarities
# ═══════════════════════════════════════════════════════════════

def find_analogies(
    new_skill_name: str,
    new_content: str,
    existing_skills: list[str],
    llm_args: tuple,
) -> list[dict]:
    """Find structural analogies between a new skill and existing ones.

    Not just keyword matching — looks for deeper structural patterns:
    "This A→B→C pipeline is structurally the same as that X→Y→Z pipeline"
    """
    from skillos.llm_client import call
    from skillos.skills import skill_store

    results = []
    for existing_name in existing_skills[:8]:
        if existing_name == new_skill_name:
            continue
        try:
            existing_body = skill_store.get_skill_body(skill_store.load_skill(existing_name))
        except Exception:
            continue

        prompt = f"""找找这两个技能之间的**结构性相似之处**。不是表面关键词，而是底层逻辑。

## 技能A: {new_skill_name}
```
{new_content[:600]}
```

## 技能B: {existing_name}
```
{existing_body[:600]}
```

## 找类比
1. 它们的流程结构相似吗？（都是"收集→处理→输出"？都是"判断→分支→执行"？）
2. 有没有技能A的某个步骤可以从技能B的方法中受益？
3. 有没有一个通用模式可以同时描述这两个技能？

输出: "相似: <是/否>。模式: <通用模式描述>。借鉴: <A可以从B学什么>" """

        try:
            raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                       max_tokens=200, temperature=0.2)
            if "相似: 是" in raw:
                results.append({
                    "target_skill": existing_name,
                    "pattern": raw.split("模式:")[-1].split("借鉴:")[0].strip() if "模式:" in raw else "",
                    "takeaway": raw.split("借鉴:")[-1].strip() if "借鉴:" in raw else "",
                })
        except Exception:
            pass

    return results


# ═══════════════════════════════════════════════════════════════
# 5. Learning Journal
# ═══════════════════════════════════════════════════════════════

def journal_event(
    event_type: str,
    description: str,
    source: str = "",
    skill_name: str = "",
    metadata: dict | None = None,
) -> None:
    """Record a learning event in the journal.

    event_type: "skill_created", "skill_optimized", "url_learned",
                "knowledge_extracted", "analogy_found", "feynman_deepened"
    """
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.time(),
        "event_type": event_type,
        "description": description[:300],
    }
    if source:
        entry["source"] = source[:200]
    if skill_name:
        entry["skill_name"] = skill_name
    if metadata:
        entry["metadata"] = metadata

    try:
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        _log.warning("Failed to journal event: %s", exc)


def read_journal(limit: int = 20) -> list[dict]:
    """Read recent learning journal entries."""
    if not JOURNAL_PATH.exists():
        return []
    entries = []
    try:
        for line in JOURNAL_PATH.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                entries.append(json.loads(line))
    except Exception:
        pass
    return sorted(entries, key=lambda e: e.get("timestamp", 0), reverse=True)[:limit]


def journal_summary() -> str:
    """Generate a human-readable summary of recent learning."""
    entries = read_journal(20)
    if not entries:
        return "尚无学习记录。"

    lines = ["## 📖 学习日志\n"]
    by_type: dict[str, int] = {}
    for e in entries:
        t = e.get("event_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    lines.append(f"最近 {len(entries)} 条记录:")
    for t, c in sorted(by_type.items()):
        label = {"skill_created": "创建技能", "skill_optimized": "优化技能",
                 "url_learned": "URL学习", "knowledge_extracted": "知识提取",
                 "analogy_found": "类比发现", "feynman_deepened": "费曼深化"}.get(t, t)
        lines.append(f"- {label}: {c} 次")

    for e in entries[:5]:
        ts = e.get("timestamp", 0)
        from datetime import datetime
        dt = datetime.fromtimestamp(ts).strftime("%m/%d %H:%M")
        lines.append(f"\n{dt} | {e.get('event_type','?')}")
        lines.append(f"  {e.get('description','')[:120]}")

    return "\n".join(lines)