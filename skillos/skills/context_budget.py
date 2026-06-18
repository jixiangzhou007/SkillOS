"""Context Budget Controller — proportional token allocation for dispatcher.

Inspired by LLM Wiki's budget control: 60% wiki / 20% history / 5% index / 15% system.
Prevents context window overflow when the skill library grows large.

Unlike a simple MAX_TOOLS_PER_REQUEST cap, this allocates tokens proportionally
so that every category gets a fair share regardless of window size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BudgetAllocation:
    """Token budget split across context categories."""
    skills_library: int = 0      # skill descriptions and tool definitions
    conversation_history: int = 0  # recent messages
    system_prompt: int = 0        # routing rules and instructions
    skill_index: int = 0          # skill name/summary index
    total: int = 0

    def remaining(self) -> int:
        return self.total - self.skills_library - self.conversation_history - self.system_prompt - self.skill_index


class ContextBudget:
    """Manages proportional token allocation for dispatcher context windows.

    Default split (LLM Wiki inspired, adapted for skill dispatch):
      - Skills library:  50% (tool definitions, descriptions)
      - History:         25% (recent conversation turns)
      - System prompt:   15% (routing rules + instructions)
      - Skill index:     10% (name/summary quick-ref for retrieval)
    """

    DEFAULT_SPLIT = (0.50, 0.25, 0.15, 0.10)

    def __init__(
        self,
        total_tokens: int = 64000,
        split: tuple[float, float, float, float] | None = None,
    ):
        self.total_tokens = total_tokens
        self.split = split or self.DEFAULT_SPLIT

    def allocate(self) -> BudgetAllocation:
        """Compute token budget for each category."""
        skills_pct, history_pct, system_pct, index_pct = self.split
        return BudgetAllocation(
            skills_library=int(self.total_tokens * skills_pct),
            conversation_history=int(self.total_tokens * history_pct),
            system_prompt=int(self.total_tokens * system_pct),
            skill_index=int(self.total_tokens * index_pct),
            total=self.total_tokens,
        )

    def fit_skills(
        self,
        tools: list[dict],
        *,
        tokens_per_tool: int = 500,
        budget: BudgetAllocation | None = None,
    ) -> list[dict]:
        """Return only as many tools as fit in the skills library budget.

        Tools beyond the budget are dropped (with a warning log). The caller
        should sort by relevance before calling this method — the budget is
        a hard cap, not a relevance ranker.
        """
        if budget is None:
            budget = self.allocate()
        max_tools = max(1, budget.skills_library // tokens_per_tool)
        if len(tools) > max_tools:
            import logging
            _log = logging.getLogger(__name__)
            _log.info(
                "Context budget: %d tools exceed budget (%d tokens), capping at %d",
                len(tools), budget.skills_library, max_tools,
            )
        return tools[:max_tools]

    def fit_history(
        self,
        messages: list[dict],
        *,
        chars_per_msg: int = 200,
        budget: BudgetAllocation | None = None,
    ) -> list[dict]:
        """Truncate conversation history to fit the history budget."""
        if budget is None:
            budget = self.allocate()
        tokens_per_msg = chars_per_msg // 3  # rough: ~3 chars per token for CJK
        max_msgs = max(1, budget.conversation_history // max(1, tokens_per_msg))
        return messages[-max_msgs:] if len(messages) > max_msgs else messages


# ── Singleton ──────────────────────────────────────────────────

_budget: Optional[ContextBudget] = None


def get_context_budget(total_tokens: int = 64000) -> ContextBudget:
    """Get or create the context budget singleton."""
    global _budget
    if _budget is None or _budget.total_tokens != total_tokens:
        _budget = ContextBudget(total_tokens=total_tokens)
    return _budget
