"""Epistemology Layer — experience ≠ knowledge.

Philosophical foundations:
  Plato:  Knowledge = justified true belief. Experience alone lacks justification.
  Kant:   Phenomena (experience) ≠ Noumena (truth).
  Popper: Knowledge advances through falsification, not verification.
  Polanyi: "We know more than we can tell" — tacit knowledge exists.

Four layers of epistemic confidence:
  Evidence   — raw observation, objective measurement
  Experience — interpreted observation, subjective, may be wrong
  Knowledge  — verified, cross-referenced, survived falsification
  Preference — subjective, no truth value, personal taste
  Error      — proven wrong (preserved to prevent repeating mistakes)
  Superseded — was true, now replaced (Graphiti-inspired temporal model)

Promotion criteria (Experience → Knowledge):
  1. Cross-reference: ≥ 2 independent sources agree
  2. Non-contradiction: not contradicted by any verified knowledge
  3. Falsification resistance: survived adversarial challenge
  4. Temporal stability: still holds after N days

Ported from Skill Distiller's epistemology.py — merged with SkillOS additions.
"""

import json
import logging
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

EPISTEME_PATH = Path(__file__).parent.parent.parent / "data" / "epistemic_state.json"


class EpistemicLevel(Enum):
    EVIDENCE = "evidence"
    EXPERIENCE = "experience"
    KNOWLEDGE = "knowledge"
    PREFERENCE = "preference"
    ERROR = "error"
    SUPERSEDED = "superseded"  # Graphiti-inspired: was true, now replaced


@dataclass
class EpistemicClaim:
    """A claim with full epistemic metadata — how do we know this, and how sure are we?"""

    claim_id: str = ""
    content: str = ""                    # the claim itself
    level: EpistemicLevel = EpistemicLevel.EXPERIENCE
    source: str = ""                     # where it came from (URL, conversation, user)
    source_type: str = ""                # "user_feedback" | "url_content" | "test_result" | "llm_generated"
    confidence: float = 0.5              # 0-1, based on verification
    corroborated_by: list[str] = field(default_factory=list)
    contradicted_by: list[str] = field(default_factory=list)
    falsification_attempts: int = 0
    falsification_survived: int = 0
    created_at: float = 0.0
    last_verified: float = 0.0
    expires_at: float = 0.0             # experience expires faster than knowledge
    valid_at: float = 0.0               # Graphiti: when claim became valid
    invalid_at: float = 0.0             # Graphiti: 0 = still valid
    tags: list[str] = field(default_factory=list)
    skill_name: str = ""

    @property
    def is_knowledge(self) -> bool:
        return self.level == EpistemicLevel.KNOWLEDGE

    @property
    def is_reliable(self) -> bool:
        """Can this claim be trusted for cross-skill recommendations?"""
        return self.level == EpistemicLevel.KNOWLEDGE and self.confidence >= 0.7

    @property
    def is_stale(self) -> bool:
        """Has this claim expired? (time-based TTL)"""
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    @property
    def is_current(self) -> bool:
        """Is this claim currently valid? (Graphiti temporal model)"""
        return self.invalid_at == 0 or time.time() < self.invalid_at

    def promote_to_knowledge(self) -> bool:
        """Check if this experience can be promoted to knowledge.

        Criteria (Plato's justified true belief + Popper's falsification):
        1. ≥ 2 independent corroborating sources
        2. Zero verified contradictions
        3. ≥ 1 successful falsification attempt survived
        """
        if self.level != EpistemicLevel.EXPERIENCE:
            return False
        if len(self.corroborated_by) < 2:
            return False
        if len(self.contradicted_by) > 0:
            return False
        if self.falsification_attempts < 1:
            return False
        if self.falsification_survived < 1:
            return False

        self.level = EpistemicLevel.KNOWLEDGE
        self.confidence = min(1.0, self.confidence + 0.2)
        self.expires_at = time.time() + (90 * 86400)  # 90 days
        return True

    def demote_to_error(self, reason: str = "") -> None:
        """This claim was proven wrong. Demote to error."""
        self.level = EpistemicLevel.ERROR
        self.confidence = 0.1
        self.tags.append(f"error: {reason[:80]}" if reason else "error: disproven")

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id, "content": self.content,
            "level": self.level.value, "source": self.source,
            "source_type": self.source_type, "confidence": round(self.confidence, 2),
            "corroborated_by": self.corroborated_by,
            "contradicted_by": self.contradicted_by,
            "falsification_attempts": self.falsification_attempts,
            "falsification_survived": self.falsification_survived,
            "created_at": self.created_at, "last_verified": self.last_verified,
            "expires_at": self.expires_at,
            "valid_at": self.valid_at, "invalid_at": self.invalid_at,
            "is_current": self.is_current,
            "tags": self.tags, "skill_name": self.skill_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EpistemicClaim":
        level_str = data.get("level", "experience")
        try:
            level = EpistemicLevel(level_str)
        except ValueError:
            level = EpistemicLevel.EXPERIENCE
        return cls(
            claim_id=data.get("claim_id", data.get("id", "")),
            content=data.get("content", ""), level=level,
            source=data.get("source", ""), source_type=data.get("source_type", ""),
            confidence=data.get("confidence", 0.5),
            corroborated_by=data.get("corroborated_by", []),
            contradicted_by=data.get("contradicted_by", []),
            falsification_attempts=data.get("falsification_attempts", 0),
            falsification_survived=data.get("falsification_survived", 0),
            created_at=data.get("created_at", 0),
            last_verified=data.get("last_verified", 0),
            expires_at=data.get("expires_at", 0),
            valid_at=data.get("valid_at", 0), invalid_at=data.get("invalid_at", 0),
            tags=data.get("tags", []), skill_name=data.get("skill_name", ""),
        )


# ═══════════════════════════════════════════════════════════════
# 1. Claim Classification
# ═══════════════════════════════════════════════════════════════

def classify_claim(content: str, source_type: str = "", source_url: str = "",
                   llm_args: tuple | None = None) -> EpistemicLevel:
    """Classify a claim into the correct epistemic level using heuristics + LLM."""
    # Source-based defaults
    if "wikipedia.org" in source_url:
        return EpistemicLevel.EVIDENCE
    if "arxiv.org" in source_url:
        return EpistemicLevel.EVIDENCE

    # Fast heuristic checks
    preference_markers = ["喜欢", "偏好", "习惯", "我觉得", "我个人", "I prefer", "I like"]
    if any(m in content for m in preference_markers):
        return EpistemicLevel.PREFERENCE

    evidence_markers = ["得分", "分数", "score", "scored", "HTTP", "error", "failed",
                        "passed", "通过", "失败", "返回", "returned"]
    if source_type in ("test_result", "validation") or any(m in content for m in evidence_markers):
        return EpistemicLevel.EVIDENCE

    if source_type == "test_result":
        return EpistemicLevel.EVIDENCE

    # LLM-based classification for ambiguous cases
    if llm_args:
        try:
            from skillos.llm_client import call
            model = llm_args[2] if len(llm_args) > 2 else ""
            prompt = f"""分类以下陈述的认识论层级。四个层级:
- evidence: 客观可测量的观察 ("技能得分2/5", "API返回404")
- experience: 主观解释或个人观察 ("触发条件不够清晰")
- knowledge: 已验证、可推广的规律 ("DNA原则2: 参数必须定义类型")
- preference: 个人喜好，没有真假 ("我喜欢简洁的回复")

陈述: {content[:200]}
来源类型: {source_type}

只回复一个词: evidence, experience, knowledge, 或 preference。"""
            result = call(prompt, model=model, max_tokens=10, temperature=0.1).strip().lower()
            for level in EpistemicLevel:
                if level.value in result:
                    return level
        except Exception:
            pass

    return EpistemicLevel.EXPERIENCE


# ═══════════════════════════════════════════════════════════════
# 2. Claim Store — persistent epistemic state
# ═══════════════════════════════════════════════════════════════

class EpistemicStore:
    """Persistent store of claims with epistemic metadata."""

    def __init__(self):
        self.claims: dict[str, EpistemicClaim] = {}
        self._load()

    def _load(self):
        if not EPISTEME_PATH.exists():
            return
        try:
            data = json.loads(EPISTEME_PATH.read_text(encoding="utf-8"))
            claims_data = data.get("claims", [])
            if isinstance(claims_data, list):
                for c in claims_data:
                    claim = EpistemicClaim.from_dict(c)
                    self.claims[claim.claim_id] = claim
            elif isinstance(claims_data, dict):
                for cid, cdata in claims_data.items():
                    claim = EpistemicClaim.from_dict(cdata)
                    self.claims[claim.claim_id] = claim
        except Exception as e:
            _log.warning("Failed to load epistemic store: %s", e)

    def save(self):
        EPISTEME_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"claims": [c.to_dict() for c in self.claims.values()]}
        EPISTEME_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_claim(
        self, content: str, source: str = "", source_type: str = "",
        level: EpistemicLevel | None = None, skill_name: str = "",
        llm_args: tuple | None = None,
    ) -> EpistemicClaim:
        """Add a new claim with automatic classification and TTL."""
        if level is None:
            level = classify_claim(content, source_type, source, llm_args)

        import uuid
        cid = f"ec_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        # Set expiration based on epistemic level
        expires = 0.0
        if level == EpistemicLevel.EXPERIENCE:
            expires = time.time() + (14 * 86400)   # 14 days
        elif level == EpistemicLevel.EVIDENCE:
            expires = time.time() + (30 * 86400)   # 30 days
        elif level == EpistemicLevel.KNOWLEDGE:
            expires = time.time() + (90 * 86400)   # 90 days

        claim = EpistemicClaim(
            claim_id=cid, content=content, level=level, source=source,
            source_type=source_type, confidence=0.5, created_at=time.time(),
            last_verified=time.time(), expires_at=expires, valid_at=time.time(),
            skill_name=skill_name,
        )
        self.claims[cid] = claim
        self.save()
        return claim

    def get_knowledge(self, skill_name: str = "") -> list[EpistemicClaim]:
        """Get verified, current knowledge claims."""
        result = [c for c in self.claims.values() if c.is_knowledge and c.is_current]
        if skill_name:
            result = [c for c in result if c.skill_name == skill_name]
        return result

    def get_experiences(self, skill_name: str = "") -> list[EpistemicClaim]:
        """Get experiences (unverified, for review)."""
        result = [c for c in self.claims.values() if c.level == EpistemicLevel.EXPERIENCE]
        if skill_name:
            result = [c for c in result if c.skill_name == skill_name]
        return result

    def get_preferences(self) -> list[EpistemicClaim]:
        """Get user preferences (subjective, never promoted)."""
        return [c for c in self.claims.values() if c.level == EpistemicLevel.PREFERENCE]

    def invalidate(self, claim_id: str, superseded_by: str = "") -> bool:
        """Graphiti-style: mark claim as no longer valid."""
        if claim_id not in self.claims:
            return False
        self.claims[claim_id].invalid_at = time.time()
        self.claims[claim_id].level = EpistemicLevel.SUPERSEDED
        if superseded_by:
            self.claims[claim_id].tags.append(f"superseded_by: {superseded_by}")
        self.save()
        return True

    def attempt_promotion(self, llm_args: tuple | None = None) -> int:
        """Try to promote experiences to knowledge. Returns count promoted."""
        promoted = 0
        for claim in list(self.claims.values()):
            if claim.level != EpistemicLevel.EXPERIENCE:
                continue
            if claim.is_stale:
                continue
            if llm_args:
                self._falsify_claim(claim, llm_args)
            if claim.promote_to_knowledge():
                promoted += 1
                _log.info("Promoted to knowledge: %s", claim.content[:80])
        if promoted:
            self.save()
        return promoted

    def _falsify_claim(self, claim: EpistemicClaim, llm_args: tuple) -> None:
        """Popper-style: try to disprove this claim."""
        try:
            from skillos.llm_client import call
            model = llm_args[2] if len(llm_args) > 2 else ""
            prompt = f"""试着反驳以下陈述。如果它确实有问题，指出问题。如果它基本正确，说"基本正确"。

陈述: {claim.content}
来源: {claim.source}

输出: "基本正确" 或 "有问题: <具体问题>" """
            result = call(prompt, model=model, max_tokens=100, temperature=0.3)
            claim.falsification_attempts += 1
            if "基本正确" in result:
                claim.falsification_survived += 1
            elif "有问题" in result:
                claim.confidence = max(0.1, claim.confidence - 0.15)
                claim.contradicted_by.append(f"falsification: {result[:80]}")
            claim.last_verified = time.time()
        except Exception:
            pass

    def cross_reference(self) -> int:
        """Cross-reference claims: find corroborating and contradicting pairs."""
        pairs = 0
        claim_list = list(self.claims.values())
        for i in range(len(claim_list)):
            for j in range(i + 1, len(claim_list)):
                a, b = claim_list[i], claim_list[j]
                overlap = _text_overlap(a.content, b.content)
                if overlap > 0.4:
                    pairs += 1
                    if b.claim_id not in a.corroborated_by:
                        a.corroborated_by.append(b.claim_id)
                    if a.claim_id not in b.corroborated_by:
                        b.corroborated_by.append(a.claim_id)
        if pairs:
            self.save()
        return pairs

    def expire_stale_claims(self) -> int:
        """Downgrade confidence of stale experience claims. Returns count expired."""
        expired = 0
        for claim in list(self.claims.values()):
            if claim.is_stale and claim.level == EpistemicLevel.EXPERIENCE:
                claim.confidence = max(0.1, claim.confidence - 0.3)
                expired += 1
        if expired:
            self.save()
        return expired

    def get_knowledge_context(self, skill_name: str = "") -> str:
        """Get verified knowledge as a context block for LLM prompts."""
        knowledge = self.get_knowledge(skill_name)
        if not knowledge:
            return ""
        lines = ["\n## 📚 已验证知识（可跨技能使用）\n"]
        for k in knowledge[:10]:
            lines.append(f"- [{k.confidence:.0%}] {k.content[:150]}")
        return "\n".join(lines)


def _text_overlap(a: str, b: str) -> float:
    """Compute word-level text overlap ratio for cross-referencing."""
    words_a = set(re.findall(r'[\w一-鿿]{2,}', a))
    words_b = set(re.findall(r'[\w一-鿿]{2,}', b))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a | words_b), 1)


# Singleton
_store: Optional[EpistemicStore] = None


def get_store() -> EpistemicStore:
    global _store
    if _store is None:
        _store = EpistemicStore()
    return _store


def reset_store() -> None:
    """Clear singleton (for benchmarks/tests)."""
    global _store
    _store = None


@contextmanager
def isolated_epistemic_store(path: Path | None = None):
    """Use a temporary epistemic JSON file; restore global state after."""
    global _store
    import skillos.knowledge.epistemology as ep_mod

    old_store = _store
    old_path = ep_mod.EPISTEME_PATH
    tmp_path = path
    if tmp_path is None:
        tmp_path = Path(__file__).parent.parent.parent / "data" / "benchmarks" / "epistemic" / "_isolated_state.json"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text('{"claims": []}', encoding="utf-8")
    ep_mod.EPISTEME_PATH = tmp_path
    _store = None
    try:
        yield get_store()
    finally:
        _store = old_store
        ep_mod.EPISTEME_PATH = old_path
        _store = None


# ═══════════════════════════════════════════════════════════════
# 3. Integration functions
# ═══════════════════════════════════════════════════════════════

def record_claim(
    content: str, source: str = "", source_type: str = "",
    skill_name: str = "", llm_args: tuple | None = None,
) -> EpistemicClaim:
    """Record a new claim with proper epistemic classification.

    Called from dispatch after user feedback, URL learning, or test results.
    """
    store = get_store()
    claim = store.add_claim(content, source, source_type, skill_name=skill_name, llm_args=llm_args)

    # Immediately cross-reference with existing knowledge
    existing = store.get_knowledge()
    for ec in existing:
        if _text_overlap(claim.content, ec.content) > 0.3:
            claim.corroborated_by.append(ec.claim_id)
            ec.corroborated_by.append(claim.claim_id)

    if len(claim.corroborated_by) >= 2:
        claim.promote_to_knowledge()

    store.save()
    return claim


def get_knowledge_context(skill_name: str = "") -> str:
    """Get verified knowledge as a context block for skill operations."""
    return get_store().get_knowledge_context(skill_name)


def get_experience_review(skill_name: str = "") -> str:
    """Get unverified experiences for human review."""
    store = get_store()
    experiences = store.get_experiences(skill_name)
    if not experiences:
        return ""

    lines = ["\n## 📝 待审核经验（主观、未验证）\n"]
    for e in experiences[:10]:
        stale = "⏰已过期" if e.is_stale else ""
        lines.append(f"- [{e.confidence:.0%}] {e.content[:150]} {stale}")
    lines.append(f"\n共 {len(experiences)} 条经验等待验证。经验 ≠ 知识 —— 需要交叉验证和证伪测试。")
    return "\n".join(lines)
