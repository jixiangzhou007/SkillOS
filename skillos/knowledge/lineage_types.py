"""Knowledge Lineage — data class definitions for provenance tracking."""

import time
from dataclasses import dataclass, field
from pathlib import Path

LINEAGE_DIR = Path(__file__).parent / "data" / "lineage"
LINEAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SourceChunk:
    """A specific chunk of source material."""
    chunk_id: str = ""              # src_<hash>
    source_url: str = ""
    source_type: str = ""           # url | file | conversation | paper
    paragraph_index: int = 0
    raw_text: str = ""
    char_offset_start: int = 0
    char_offset_end: int = 0


@dataclass
class ExtractStep:
    """One step in the knowledge extraction pipeline."""
    step_name: str = ""             # 初识 | 理解 | 拆解 | 重构 | 验证 | 内化 | 沉淀 | 扩散
    input_text: str = ""
    output_text: str = ""
    method: str = ""                # LLM call | regex | heuristic
    model_used: str = ""
    confidence_delta: float = 0.0   # how much confidence changed in this step
    elapsed_s: float = 0.0
    timestamp: float = 0.0


@dataclass
class KnowledgeItem:
    """A single knowledge item with full lineage."""
    item_id: str = ""               # ki_<hash>
    content: str = ""               # the knowledge itself
    category: str = "fact"          # fact | concept | heuristic | pattern | contradiction

    # Lineage
    source_chunk: SourceChunk | None = None
    extraction_pipeline: list[ExtractStep] = field(default_factory=list)

    # Current state
    confidence: float = 0.5
    epistemic_level: str = "experience"  # evidence | experience | knowledge | wisdom | superseded
    verified_by: list[str] = field(default_factory=list)     # other item IDs
    contradicted_by: list[str] = field(default_factory=list)  # other item IDs
    superseded_by: str = ""         # item ID of the newer fact that replaced this one

    # Graph connections
    graph_node_id: str = ""         # linked knowledge graph node
    related_items: list[dict] = field(default_factory=list)
    # [{item_id, relation_type, weight}]

    # Impact tracking
    affected_skills: list[dict] = field(default_factory=list)
    # [{skill_name, optimization_round, score_delta, timestamp}]

    # Temporal (Graphiti-inspired: bi-temporal validity)
    created_at: float = 0.0
    valid_at: float = 0.0           # when this fact became true
    invalid_at: float = 0.0         # when this fact stopped being true (0 = still valid)
    last_accessed: float = 0.0
    access_count: int = 0
    decay_rate: float = 0.05        # Ebbinghaus decay per day

    @property
    def is_valid(self) -> bool:
        """Is this fact currently valid? (Graphiti: auto-filter expired facts)"""
        return self.invalid_at == 0 or time.time() < self.invalid_at

    @property
    def current_strength(self) -> float:
        """Ebbinghaus: strength decays without reinforcement."""
        if self.last_accessed <= 0:
            self.last_accessed = self.created_at if self.created_at > 0 else time.time()
        days_since_access = (time.time() - self.last_accessed) / 86400
        decay = self.decay_rate * max(0, days_since_access)
        reinforcement = min(1.0, self.access_count * 0.1)
        return max(0.1, self.confidence - decay + reinforcement)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "content": self.content,
            "category": self.category,
            "confidence": self.confidence,
            "epistemic_level": self.epistemic_level,
            "is_valid": self.is_valid,
            "strength": round(self.current_strength, 2),
            "source": {
                "url": self.source_chunk.source_url if self.source_chunk else "",
                "paragraph": self.source_chunk.paragraph_index if self.source_chunk else 0,
            } if self.source_chunk else None,
            "pipeline_steps": len(self.extraction_pipeline),
            "graph_node": self.graph_node_id,
            "related_items": self.related_items,
            "related_count": len(self.related_items),
            "affected_skills": self.affected_skills,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "superseded_by": self.superseded_by,
        }
