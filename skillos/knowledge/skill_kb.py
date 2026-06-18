"""Skill-specific Knowledge Base — WHAT a skill needs to know in order to DO.

Philosophy:
  Skill = HOW (steps, branches, decisions)     ← skill.md
  Knowledge = WHAT (facts, cases, heuristics)  ← this module

A skill document describes the path. The knowledge base is the terrain it walks on.
Multiple skills can share the same knowledge items — "VIP customer definition"
is one fact, used by complaint handling, email response, and order processing.
"""


import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


# ═══════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════

@dataclass
class KBItem:
    """A single knowledge item in a skill's knowledge base."""

    id: str = ""
    content: str = ""
    type: str = "fact"              # fact | case | heuristic | reference | constraint | template
    source: str = ""                # where this came from (URL, document, conversation)
    confidence: float = 0.5
    used_by_steps: list[str] = field(default_factory=list)  # which S_body steps reference this
    shared_with: list[str] = field(default_factory=list)    # other skills that also use this
    tags: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class SkillKB:
    """A skill's complete knowledge base."""

    skill_name: str
    facts: list[KBItem] = field(default_factory=list)
    cases: list[KBItem] = field(default_factory=list)
    heuristics: list[KBItem] = field(default_factory=list)
    references: list[KBItem] = field(default_factory=list)
    constraints: list[KBItem] = field(default_factory=list)
    templates: list[KBItem] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        return (len(self.facts) + len(self.cases) + len(self.heuristics) +
                len(self.references) + len(self.constraints) + len(self.templates))

    @property
    def path(self) -> Path:
        safe = re.sub(r'[<>:"/\\|?*]', '_', self.skill_name)[:64]
        return SKILLS_DIR / safe / "knowledge"


# ═══════════════════════════════════════════════════════════════
# Storage
# ═══════════════════════════════════════════════════════════════

def _kb_path(skill_name: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', '_', skill_name)[:64]
    return SKILLS_DIR / safe / "knowledge"


def _item_file(kb_path: Path, item_id: str) -> Path:
    return kb_path / f"{item_id}.json"


def save_item(skill_name: str, item: KBItem) -> str:
    """Save a knowledge item to a skill's KB. Returns the item ID."""
    kb_path = _kb_path(skill_name)
    kb_path.mkdir(parents=True, exist_ok=True)

    if not item.id:
        item.id = f"{item.type}_{int(time.time())}_{hash(item.content) % 10000:04d}"
    if not item.created_at:
        item.created_at = time.time()
    item.updated_at = time.time()

    data = {
        "id": item.id, "content": item.content, "type": item.type,
        "source": item.source, "confidence": item.confidence,
        "used_by_steps": item.used_by_steps, "shared_with": item.shared_with,
        "tags": item.tags, "created_at": item.created_at, "updated_at": item.updated_at,
    }
    _item_file(kb_path, item.id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return item.id


def load_kb(skill_name: str) -> SkillKB:
    """Load the complete knowledge base for a skill."""
    kb_path = _kb_path(skill_name)
    kb = SkillKB(skill_name=skill_name)

    if not kb_path.exists():
        return kb

    type_map = {
        "fact": kb.facts, "case": kb.cases, "heuristic": kb.heuristics,
        "reference": kb.references, "constraint": kb.constraints,
        "template": kb.templates,
    }

    for fp in sorted(kb_path.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            item = KBItem(
                id=data.get("id", fp.stem),
                content=data.get("content", ""),
                type=data.get("type", "fact"),
                source=data.get("source", ""),
                confidence=data.get("confidence", 0.5),
                used_by_steps=data.get("used_by_steps", []),
                shared_with=data.get("shared_with", []),
                tags=data.get("tags", []),
                created_at=data.get("created_at", 0),
                updated_at=data.get("updated_at", 0),
            )
            bucket = type_map.get(item.type, kb.facts)
            bucket.append(item)
        except Exception as e:
            _log.warning("Failed to load KB item %s: %s", fp, e)

    return kb


def load_kb_as_context(skill_name: str, max_items: int = 15) -> str:
    """Load a skill's knowledge base as a formatted context string for LLM prompts."""
    kb = load_kb(skill_name)
    if kb.total_items == 0:
        return ""

    parts = [f"## 技能「{skill_name}」专属知识库\n"]

    if kb.facts:
        parts.append("### 📋 事实与定义")
        for f in kb.facts[:5]:
            parts.append(f"- {f.content}")
            if f.tags:
                parts.append(f"  标签: {', '.join(f.tags[:5])}")

    if kb.heuristics:
        parts.append("\n### 💡 启发式规则")
        for h in kb.heuristics[:5]:
            parts.append(f"- {h.content}")

    if kb.cases:
        parts.append("\n### 📖 案例与经验")
        for c in kb.cases[:3]:
            parts.append(f"- {c.content[:150]}")

    if kb.constraints:
        parts.append("\n### ⚠️ 约束条件")
        for c in kb.constraints[:3]:
            parts.append(f"- {c.content}")

    if kb.references:
        parts.append("\n### 🔗 参考来源")
        for r in kb.references[:3]:
            parts.append(f"- {r.content[:120]}")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# Extraction: separate knowledge from process
# ═══════════════════════════════════════════════════════════════

def extract_kb_from_skill(
    skill_name: str,
    skill_content: str,
    llm_args: tuple,
) -> tuple[str, SkillKB]:
    """Analyze a skill document and extract knowledge items from it.

    Returns (cleaned_skill_content, extracted_kb).
    The cleaned skill focuses on process; facts move to the KB.
    """
    from skillos.llm_client import call

    prompt = f"""分析以下技能文档。你的任务是区分"流程"和"知识"。

## 技能文档
```
{skill_content[:3000]}
```

## 区分标准
- **流程**（留在技能里）：步骤、顺序、决策点、if-then 分支。描述了"怎么做"。
- **知识**（提取到知识库）：事实定义、经验规则、案例、约束条件、参考来源。描述了"做的时候需要知道什么"。

## 提取要求
对每条知识，标注类型和它服务于哪个步骤。

## 输出格式
```json
{{
  "items": [
    {{"type": "fact|heuristic|case|constraint|reference", "content": "...", "used_by_step": "步骤名", "confidence": 0.8}}
  ]
}}
```

只输出 JSON。如果没有可提取的知识，items 为空数组。"""

    try:
        raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "",
                   max_tokens=1500, temperature=0.2)
    except Exception as e:
        _log.warning("KB extraction failed: %s", e)
        return skill_content, SkillKB(skill_name=skill_name)

    # Parse
    items = []
    try:
        m = re.search(r'```json\s*\n(.*?)```', raw, re.DOTALL)
        data = json.loads(m.group(1) if m else raw)
        for d in data.get("items", []):
            items.append(KBItem(
                content=d["content"],
                type=d.get("type", "fact"),
                confidence=d.get("confidence", 0.7),
                used_by_steps=[d.get("used_by_step", "")] if d.get("used_by_step") else [],
                created_at=time.time(),
            ))
    except Exception:
        pass

    # Save items
    kb = SkillKB(skill_name=skill_name)
    for item in items:
        type_map = {"fact": kb.facts, "case": kb.cases, "heuristic": kb.heuristics,
                    "reference": kb.references, "constraint": kb.constraints}
        bucket = type_map.get(item.type, kb.facts)
        bucket.append(item)
        save_item(skill_name, item)

    return skill_content, kb


# ═══════════════════════════════════════════════════════════════
# Cross-skill knowledge sharing
# ═══════════════════════════════════════════════════════════════

def find_shared_knowledge(
    source_skill: str,
    target_skills: list[str],
) -> list[dict]:
    """Find knowledge items in source_skill's KB that could benefit target_skills.

    Returns list of {source_item, target_skill, reason} dicts.
    """
    source_kb = load_kb(source_skill)
    if source_kb.total_items == 0:
        return []

    all_items = (source_kb.facts + source_kb.heuristics + source_kb.constraints)
    results = []

    for target in target_skills[:10]:
        if target == source_skill:
            continue
        target_kb = load_kb(target)

        for item in all_items[:20]:
            # Check if target already has similar knowledge
            target_items = (target_kb.facts + target_kb.heuristics)
            has_similar = any(
                _text_overlap(item.content, t.content) > 0.4
                for t in target_items
            )
            if not has_similar:
                # Check if this knowledge is relevant to target's steps
                target_steps = [s.strip() for s in re.findall(r'##\s*S_body\s*\n(.*?)(?=\n##|\Z)',
                                    _load_skill_body(target), re.DOTALL)]
                relevance = _check_relevance(item.content, "\n".join(target_steps))
                if relevance:
                    results.append({
                        "source_skill": source_skill,
                        "target_skill": target,
                        "item_content": item.content[:150],
                        "item_type": item.type,
                        "reason": "可能填补目标技能的知识缺口",
                    })

    return results


def _load_skill_body(skill_name: str) -> str:
    try:
        from skillos.skills import skill_store
        return skill_store.get_skill_body(skill_store.load_skill(skill_name))
    except Exception:
        return ""


def _text_overlap(a: str, b: str) -> float:
    words_a = set(re.findall(r'[\w一-鿿]{2,}', a))
    words_b = set(re.findall(r'[\w一-鿿]{2,}', b))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a | words_b), 1)


def _check_relevance(item: str, context: str) -> bool:
    return _text_overlap(item, context) > 0.15


# ═══════════════════════════════════════════════════════════════
# Full pipeline integration
# ═══════════════════════════════════════════════════════════════

def enrich_skill_with_kb(
    skill_name: str,
    skill_content: str,
    llm_args: tuple,
) -> dict:
    """Full pipeline: extract KB from skill, find cross-skill sharing opportunities.

    Called after skill creation/optimization to build its knowledge base.
    """
    result = {"skill": skill_name, "kb_items": 0, "shared": []}

    # Step 1: Extract knowledge from the skill document
    _, kb = extract_kb_from_skill(skill_name, skill_content, llm_args)
    result["kb_items"] = kb.total_items
    result["breakdown"] = {
        "facts": len(kb.facts),
        "cases": len(kb.cases),
        "heuristics": len(kb.heuristics),
        "references": len(kb.references),
        "constraints": len(kb.constraints),
    }

    # Step 2: Find cross-skill sharing
    from skillos.skills import skill_store
    all_skills = [s for s in skill_store.list_skills() if s != skill_name]
    shared = find_shared_knowledge(skill_name, all_skills)
    result["shared"] = shared



# ═══════════════════════════════════════════════════════════════
# Template Comparison
# ═══════════════════════════════════════════════════════════════

def add_template(skill_name: str, content: str, source: str = "", label: str = "") -> str:
    item = KBItem(content=content, type="template", source=source,
                   confidence=1.0, created_at=time.time(), tags=[label] if label else [])
    return save_item(skill_name, item)


def compare_against_templates(skill_name: str, input_doc: str, llm_args: tuple) -> dict:
    kb = load_kb(skill_name)
    if not kb.templates:
        return {"has_templates": False, "message": "no templates stored"}
    from skillos.llm_client import call
    results = []
    for tpl in kb.templates[:3]:
        prompt = f"""你是文档对比专家。逐条比对输入文档和参考模板，找出差异。

## 参考模板 ({tpl.tags[0] if tpl.tags else "template"})
```
{tpl.content[:2000]}
```

## 输入文档
```
{input_doc[:2000]}
```

## 逐条比对
1. 新增条款: 输入有，模板无
2. 删除条款: 模板有，输入无
3. 修改条款: 两者都有但不同
4. 风险项: 标注 [高/中/低]

输出格式: [类型] [风险] 条款X: 差异描述"""
        try:
            raw = call(prompt, model=llm_args[2] if len(llm_args) > 2 else "", max_tokens=600)
            results.append({"template_label": tpl.tags[0] if tpl.tags else "unnamed",
                            "diff": raw.strip()})
        except Exception as e:
            results.append({"error": str(e)})
    return {"has_templates": True, "compared": len(results), "results": results}
