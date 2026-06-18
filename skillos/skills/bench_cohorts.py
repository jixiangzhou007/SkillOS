"""Shared benchmark cohort definitions — reference + generalization."""

from __future__ import annotations

from typing import Any

REFERENCE_SKILL_NAMES: frozenset[str] = frozenset({
    "电商客服退款处理",
    "GitHub Pull",
    "CSV数据清洗助手",
})

GENERALIZE_SKILL_NAMES: frozenset[str] = frozenset({
    "财务报销审计助手",
    "合同法务审核助手",
    "安全合规审计助手",
})

# Preset id → skill name (reference Quick8 compare)
REFERENCE_PRESETS: dict[str, str] = {
    "refund-invoice-fraud": "电商客服退款处理",
    "pr-dependency-audit": "GitHub Pull",
    "csv-sales-pivot": "CSV数据清洗助手",
}

REFERENCE_MIN_DELTA_PP: dict[str, float] = {
    "refund-invoice-fraud": 25.0,
    "pr-dependency-audit": 15.0,
    "csv-sales-pivot": 8.0,
}

GENERALIZE_SKILLS: tuple[dict[str, Any], ...] = (
    {
        "name": "财务报销审计助手",
        "domain_template": "finance-expense-audit",
        "anchor_tasks": ("workflow-082", "workflow-083"),
        "bench_categories": ("workflow", "documentation"),
        "min_domain_delta": 20.0,
    },
    {
        "name": "合同法务审核助手",
        "domain_template": "law-contract-review",
        "anchor_tasks": ("workflow-084",),
        "bench_categories": ("workflow", "documentation"),
        "min_domain_delta": 0.0,
    },
    {
        "name": "安全合规审计助手",
        "domain_template": "security-audit",
        "anchor_tasks": ("workflow-076", "workflow-079"),
        "bench_categories": ("workflow", "documentation"),
        "min_domain_delta": 20.0,
    },
)
