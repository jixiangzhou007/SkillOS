"""Official SkillsBench task ↔ SkillOS skill mapping."""


# Curated pairs for Phase 1 eval (official task id → SkillOS skill folder name)
CORE_TASK_MAP: dict[str, str] = {
    "citation-check": "",  # oracle smoke only (uses bundled task skills)
    "sales-pivot-analysis": "CSV数据清洗助手",
    "software-dependency-audit": "GitHub Pull",
}

# Reverse lookup: skill name → preferred official tasks (ordered)
SKILL_TO_TASKS: dict[str, list[str]] = {
    "CSV数据清洗助手": ["sales-pivot-analysis", "xlsx-recover-data"],
    "GitHub Pull": ["software-dependency-audit", "fix-build-agentops", "react-performance-debugging"],
    "电商客服退款处理": ["invoice-fraud-detection", "sec-financial-report"],
}

SMOKE_TASK = "citation-check"


def suggest_tasks_for_skill(skill_name: str) -> list[str]:
    return list(SKILL_TO_TASKS.get(skill_name, []))
