"""SkillOpt data types — all dataclass definitions for the optimization pipeline."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto


@dataclass
class OptConfig:
    """SkillOpt optimization configuration."""

    # Edit budget: starts at 4, decays by 1 per round, min 1
    initial_edit_budget: int = 4
    min_edit_budget: int = 1

    # Validation
    validation_split_ratio: float = 0.3  # oldest 30% traces as held-out
    min_traces_for_split: int = 3         # need at least this many traces to split
    strict_gate: bool = True              # require strict score improvement

    # Cross-model validation
    cross_model_enabled: bool = True
    fast_model: str = "deepseek-v4-flash"  # cheaper model for quick validation

    # Meta-learning
    meta_enabled: bool = True
    meta_skill_max_len: int = 600  # keep meta-skill compact

    # Rollout
    max_rollout_tasks: int = 5  # max tasks to run per optimization round
    rollout_timeout: int = 120  # seconds per rollout task


@dataclass
class EditProposal:
    """A single proposed edit to a skill document."""

    edit_type: str   # "add", "delete", "replace"
    target: str      # what section/line to edit
    old_text: str = ""
    new_text: str = ""
    reason: str = ""  # why this edit (traceable to a failure)

    def to_markdown(self) -> str:
        markers = {"add": "+", "delete": "-", "replace": "~"}
        m = markers.get(self.edit_type, "?")
        if self.edit_type == "add":
            return f"{m} add [{self.target}]: {self.new_text[:120]}\n  原因: {self.reason[:100]}"
        elif self.edit_type == "delete":
            return f"{m} delete [{self.target}]: {self.old_text[:120]}\n  原因: {self.reason[:100]}"
        else:
            return f"{m} replace [{self.target}]: {self.old_text[:60]} → {self.new_text[:60]}\n  原因: {self.reason[:100]}"


@dataclass
class OptimizationRound:
    """One round of optimization."""

    round_num: int
    edit_budget: int
    proposals: list[EditProposal] = field(default_factory=list)
    accepted: list[EditProposal] = field(default_factory=list)
    rejected: list[EditProposal] = field(default_factory=list)
    old_score: float = 0.0
    new_score: float = 0.0
    gate_result: str = ""  # "accepted", "rejected", "skipped"
    cross_model_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class OptimizationSession:
    """Tracks multi-round optimization state across a conversation."""

    skill_name: str
    original_content: str
    current_content: str
    rounds: list[OptimizationRound] = field(default_factory=list)
    rejection_buffer: list[str] = field(default_factory=list)  # failed edit patterns
    meta_skill: str = ""  # cross-round stable patterns
    config: OptConfig = field(default_factory=OptConfig)

    @property
    def round_num(self) -> int:
        return len(self.rounds)

    def edit_budget_for_round(self) -> int:
        """Decaying edit budget: starts at 4, decays per round."""
        next_round = len(self.rounds) + 1
        budget = self.config.initial_edit_budget - (next_round - 1)
        return max(self.config.min_edit_budget, budget)


@dataclass
class ElitePool:
    """Fixed-capacity pool of top-K competing skill versions.

    Each candidate must beat the weakest member to enter.
    Eliminated candidates are archived with failure reasons for proposer feedback.
    """

    skill_name: str
    max_size: int = 3
    members: list[dict] = field(default_factory=list)  # [{content, score, version, entered_at}]
    eliminated: list[dict] = field(default_factory=list)  # [{content_preview, score, eliminated_reason}]

    @property
    def champion(self) -> dict | None:
        return self.members[0] if self.members else None

    @property
    def weakest(self) -> dict | None:
        return self.members[-1] if self.members else None

    @property
    def median_score(self) -> float:
        if not self.members:
            return 0.0
        scores = sorted([m["score"] for m in self.members])
        mid = len(scores) // 2
        return scores[mid]

    def nominate(self, candidate_content: str, candidate_score: float, version: int) -> tuple[bool, str]:
        """Nominate a candidate for the elite pool.

        Pool fills freely until max_size. After that, tournament mode:
        candidate must beat the weakest member to enter.

        Returns (accepted, reason).
        """
        # Pool not full yet — auto-admit
        if len(self.members) < self.max_size:
            self.members.append({
                "content": candidate_content, "score": candidate_score,
                "version": version, "entered_at": time.time(),
            })
            self.members.sort(key=lambda m: m["score"], reverse=True)
            return True, f"入池（{len(self.members)}/{self.max_size}，未满免赛）"

        # Tournament: pool full, must beat the weakest
        weakest = self.weakest
        if weakest is None:
            return True, "入池（池空，自动通过）"
        if candidate_score > weakest["score"]:
            eliminated = self.members.pop()  # Remove weakest
            self.eliminated.append({
                "content_preview": eliminated["content"][:200],
                "score": eliminated["score"],
                "eliminated_by_score": candidate_score,
                "eliminated_at": time.time(),
            })
            self.members.append({
                "content": candidate_content, "score": candidate_score,
                "version": version, "entered_at": time.time(),
            })
            self.members.sort(key=lambda m: m["score"], reverse=True)
            return True, f"胜出：{candidate_score:.1f} > {weakest['score']:.1f}（淘汰池底版本 v{eliminated['version']}）"

        # Lost the tournament
        self.eliminated.append({
            "content_preview": candidate_content[:200],
            "score": candidate_score,
            "eliminated_reason": f"得分 {candidate_score:.1f} ≤ 池底 {weakest['score']:.1f}",
            "eliminated_at": time.time(),
        })
        return False, f"未入池：{candidate_score:.1f} ≤ {weakest['score']:.1f}（未击败池底版本 v{weakest['version']}）"

    def get_elimination_feedback(self) -> str:
        """Build proposer feedback from eliminated candidates."""
        if not self.eliminated:
            return ""
        lines = ["\n## 🏆 精英池淘汰记录（给提案者的反面教材）\n"]
        for e in self.eliminated[-5:]:
            lines.append(f"- ❌ 得分 {e['score']:.1f}: {e.get('eliminated_reason', e.get('eliminated_by_score', '淘汰'))}")
            lines.append(f"  内容预览: {e['content_preview'][:100]}...")
        return "\n".join(lines)


@dataclass
class AuditReport:
    """Independent audit of a skill document."""

    passed: bool = False
    score: int = 0            # 0-100
    checks: list[dict] = field(default_factory=list)
    # Each check: {check_name, passed, severity, detail, suggestion}
    summary: str = ""


class EvolutionExpert(Enum):
    TRACE2SKILL = auto()   # Batch collective discovery
    EVOSKILL = auto()      # Tournament selection
    SKILLOPT = auto()      # Bounded fine-tuning


@dataclass
class SkillState:
    """Features that the gating network uses to route."""
    skill_name: str
    trace_count: int = 0
    score_mean: float = 0.0
    score_variance: float = 0.0
    failure_count: int = 0
    failure_diversity: int = 0       # number of distinct root cause categories
    total_runs: int = 0
    days_since_creation: float = 0.0
    has_protected_regions: bool = False
    elite_pool_size: int = 0


@dataclass
class RoutingDecision:
    """Which expert(s) to use and why."""
    primary: EvolutionExpert
    secondary: EvolutionExpert | None = None
    mode: str = "auto"           # auto | top2_vote | all3_ensemble | force_<expert>
    confidence: float = 0.5      # how confident the router is in this decision
    reasoning: str = ""
