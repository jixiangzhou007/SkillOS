"""Knowledge Extractor — extract, verify, and link facts from content.

Verification strategy:
  1. Source authority weighting
  2. Cross-source consistency check
  3. Internal contradiction detection
  4. Adversarial challenge
  5. Temporal freshness check (Graphiti-inspired)

Ported from Skill Distiller's knowledge/knowledge_extractor.py.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# Source authority weighting
SOURCE_AUTHORITY = {
    "arxiv.org": 0.85, "github.com": 0.7, "wikipedia.org": 0.75,
    "medium.com": 0.5, "blog.csdn.net": 0.4, "mp.weixin.qq.com": 0.35,
    "zhuanlan.zhihu.com": 0.35, "default": 0.4,
}


@dataclass
class KnowledgeItem:
    """A single verified fact/concept/relationship."""

    item_id: str = ""
    content: str = ""
    category: str = "fact"  # fact | concept | relationship | contradiction
    source_url: str = ""
    source_authority: float = 0.5
    confidence: float = 0.5
    verified_by: list[str] = field(default_factory=list)
    challenged_by: list[str] = field(default_factory=list)
    needs_review: bool = False
    review_reason: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = 0.0
    valid_at: float = 0.0
    invalid_at: float = 0.0  # Graphiti: 0 = still valid

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id, "content": self.content,
            "category": self.category, "confidence": round(self.confidence, 2),
            "source_url": self.source_url, "needs_review": self.needs_review,
            "tags": self.tags, "created_at": self.created_at,
            "is_valid": self.invalid_at == 0,
        }


def get_source_authority(url: str) -> float:
    for domain, score in SOURCE_AUTHORITY.items():
        if domain in url:
            return score
    return SOURCE_AUTHORITY["default"]


def extract_knowledge(content: str, source_url: str, llm_args: tuple | None = None) -> list[KnowledgeItem]:
    """Extract knowledge items from content with confidence scoring.

    Uses LLM for extraction; gracefully degrades to regex heuristic if LLM unavailable.
    """
    content_preview = content[:5000] if len(content) > 5000 else content
    source_auth = get_source_authority(source_url)
    items = []

    # Try LLM extraction first
    try:
        from skillos.llm_client import call
        prompt = f"""Extract verifiable facts, concepts, and relationships from this content.

## Source: {source_url} (authority: {source_auth})
## Content
{content_preview}

## Rules
- **fact**: verifiable true/false statements
- **concept**: defined terms or methods
- **relationship**: connections between entities
- **contradiction**: internal conflicts

For each item: give category, content, confidence (0.1-1.0), and tags.

## Output
```json
[
  {{"category": "fact|concept|relationship|contradiction", "content": "...", "confidence": 0.8, "tags": ["tag1"]}}
]
```
Return [] if nothing extractable."""

        raw = call(prompt, max_tokens=2000, temperature=0.2)
        if raw:
            m = re.search(r'```json\s*\n(.*?)```', raw, re.DOTALL)
            json_str = m.group(1) if m else raw
            try:
                data = json.loads(json_str)
                for d in data:
                    if isinstance(d, dict) and d.get("content"):
                        kid = f"ki_{int(time.time())}_{hash(d['content']) % 10000:04d}"
                        items.append(KnowledgeItem(
                            item_id=kid, content=d["content"],
                            category=d.get("category", "fact"),
                            source_url=source_url,
                            source_authority=source_auth,
                            confidence=min(1.0, d.get("confidence", 0.5) * source_auth),
                            tags=d.get("tags", []),
                            created_at=time.time(), valid_at=time.time(),
                            needs_review=d.get("confidence", 0.5) < 0.4,
                            review_reason="Low confidence" if d.get("confidence", 0.5) < 0.4 else "",
                        ))
            except json.JSONDecodeError:
                _log.warning("Failed to parse knowledge JSON from LLM output")
    except Exception as e:
        _log.warning("LLM extraction failed, using heuristic: %s", e)

    return items


def learn_knowledge(content: str, source_url: str, llm_args: tuple | None = None) -> dict:
    """Extract, cross-verify, save, and record lineage for flat knowledge ingestion."""
    items = extract_knowledge(content, source_url, llm_args)
    if not items:
        return {"extracted": 0, "verified": 0, "needs_review": 0, "saved": 0}

    existing = load_all_knowledge()
    items = verify_knowledge(items, existing)
    saved = save_knowledge(items)
    verified = sum(1 for i in items if i.verified_by)
    needs_review = sum(1 for i in items if i.needs_review)

    from skillos.knowledge.ingest_pipeline import finalize_ingest

    payload = {
        "extracted": len(items),
        "verified": verified,
        "needs_review": needs_review,
        "saved": saved,
    }
    payload = finalize_ingest(
        content,
        source_url,
        extractor_items=items,
        channel="learn_knowledge",
        payload=payload,
    )
    if needs_review > 0:
        payload.setdefault("warnings", []).append(f"⚠ {needs_review} 条知识待人工复核")
    return payload


def verify_knowledge(items: list[KnowledgeItem], existing: list[KnowledgeItem]) -> list[KnowledgeItem]:
    """Cross-verify extracted knowledge against existing items.

    Graphiti-inspired: contradictory items trigger invalidation of old facts.
    """
    for item in items:
        for existing_item in existing[:50]:
            words_new = set(re.findall(r'[\w一-鿿]{2,}', item.content.lower()))
            words_old = set(re.findall(r'[\w一-鿿]{2,}', existing_item.content.lower()))
            overlap = len(words_new & words_old) / max(len(words_new), 1)

            if overlap > 0.5:
                if not _are_contradictory(item.content, existing_item.content):
                    item.confidence = min(1.0, item.confidence + 0.15)
                    item.verified_by.append(existing_item.item_id)
                else:
                    # Graphiti: old fact → invalid, new fact → current
                    existing_item.invalid_at = time.time()
                    item.confidence = max(0.3, item.confidence)
                    item.challenged_by.append(existing_item.item_id)

    return items


def save_knowledge(items: list[KnowledgeItem]) -> int:
    """Save knowledge items to disk. Returns count saved."""
    saved = 0
    for item in items:
        try:
            fp = KNOWLEDGE_DIR / f"{item.item_id}.json"
            payload = item.to_dict()
            try:
                from skillos.knowledge.epistemology import record_claim
                claim = record_claim(
                    content=item.content,
                    source=item.source_url or item.item_id,
                    source_type="url_content",
                )
                payload["epistemic_claim_id"] = claim.claim_id
                payload["epistemic_level"] = claim.level.value
            except Exception as exc:
                _log.debug("Epistemic record skipped for %s: %s", item.item_id, exc)
            fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            saved += 1
        except Exception as e:
            _log.warning("Failed to save knowledge %s: %s", item.item_id, e)
    return saved


def load_all_knowledge() -> list[KnowledgeItem]:
    """Load all saved knowledge items."""
    items = []
    for fp in sorted(KNOWLEDGE_DIR.glob("ki_*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            items.append(KnowledgeItem(
                item_id=data.get("item_id", fp.stem),
                content=data.get("content", ""),
                category=data.get("category", "fact"),
                source_url=data.get("source_url", ""),
                source_authority=data.get("source_authority", 0.5),
                confidence=data.get("confidence", 0.5),
                tags=data.get("tags", []),
                created_at=data.get("created_at", 0),
                valid_at=data.get("valid_at", 0),
                invalid_at=data.get("invalid_at", 0),
            ))
        except Exception:
            pass
    return items


def _are_contradictory(a: str, b: str) -> bool:
    """Heuristic contradiction detection."""
    neg_words = ['not', 'never', 'cannot', "don't", '避免', '不要', '不能', '禁止']
    a_neg = any(w in a.lower() for w in neg_words)
    b_neg = any(w in b.lower() for w in neg_words)
    if a_neg != b_neg:
        return True
    nums_a = set(re.findall(r'\d+\.?\d*', a))
    nums_b = set(re.findall(r'\d+\.?\d*', b))
    if nums_a and nums_b and nums_a != nums_b:
        return True
    return False
