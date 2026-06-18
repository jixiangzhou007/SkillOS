"""Official SkillsBench agent compare presets (no-skill vs with-skill)."""


# CI / local quick compare presets
AGENT_COMPARE_PRESETS: list[dict[str, str]] = [
    {
        "id": "citation-curated",
        "task": "citation-check",
        "skill": "",
        "skills_source": "bundled",
        "description": "Official curated skills on citation-check (baseline SkillsBench paper style)",
    },
    {
        "id": "csv-sales-pivot",
        "task": "sales-pivot-analysis",
        "skill": "CSV数据清洗助手",
        "skills_source": "export",
        "description": "SkillOS CSV skill exported on sales-pivot-analysis",
    },
    {
        "id": "pr-dependency-audit",
        "task": "software-dependency-audit",
        "skill": "GitHub Pull",
        "skills_source": "export",
        "description": "SkillOS PR review skill on software-dependency-audit",
    },
    {
        "id": "refund-invoice-fraud",
        "task": "invoice-fraud-detection",
        "skill": "电商客服退款处理",
        "skills_source": "export",
        "description": "SkillOS refund skill on invoice-fraud-detection",
    },
]

DEFAULT_AGENT = "deepagents"
DEFAULT_MODEL = "deepseek/deepseek-chat"
