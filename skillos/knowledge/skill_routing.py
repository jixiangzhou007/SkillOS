"""Skill ↔ SkillsBench task routing by domain and category."""


import re
from pathlib import Path
from typing import Any

from skillos.knowledge.taxonomy import detect_domain

# SkillsBench task categories (skillsbench_tasks.py)
BENCH_CATEGORIES = (
    "code-review",
    "data-processing",
    "api-design",
    "documentation",
    "workflow",
)

# Domain → default bench categories for that field
DOMAIN_BENCH_CATEGORIES: dict[str, list[str]] = {
    "computer-science": ["code-review", "api-design", "documentation"],
    "medicine-health": ["workflow", "documentation"],
    "management-science": ["workflow", "documentation"],
    "law": ["workflow", "documentation"],
    "economics-finance": ["workflow", "documentation"],
    "education": ["documentation", "workflow"],
    "design": ["documentation", "workflow"],
    "engineering": ["workflow", "data-processing"],
    "natural-science": ["data-processing", "documentation"],
    "social-science": ["data-processing", "documentation"],
    "journalism-communication": ["documentation", "workflow"],
    "agriculture": ["workflow", "documentation"],
}

# Keyword hints per bench category (Chinese + English)
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "code-review": (
        "代码审查", "code review", "pull request", "pr ", "pr审查", "sql注入",
        "null", "漏洞", "review", "diff", "merge", "github",
    ),
    "data-processing": (
        "csv", "数据清洗", "去重", "空值", "表格", "excel", "etl", "清洗",
        "duplicate", "pandas", "数据导出",
    ),
    "api-design": (
        "rest", "api", "endpoint", "接口设计", "restful", "crud", "http",
    ),
    "documentation": (
        "runbook", "文档", "手册", "sop", "应急", "incident", "复盘", "目录结构",
    ),
    "workflow": (
        "退款", "入职", "审批", "流程", "工单", "客服", "退货", "onboard",
        "workflow", "sla", "处理步骤", "诊断", "分诊", "治疗", "护理",
        "采购", "面试", "绩效", "课程", "审计", "合同", "质量", "巡检",
    ),
}


def _score_category(text: str, category: str) -> int:
    return sum(1 for kw in CATEGORY_KEYWORDS.get(category, ()) if kw.lower() in text)


def infer_bench_categories(name: str, content: str = "") -> list[str]:
    """Infer SkillsBench categories from skill name + body."""
    text = f"{name} {content[:4000]}".lower()
    matched: set[str] = set()

    domain = detect_domain(name, content)
    if domain:
        matched.update(DOMAIN_BENCH_CATEGORIES.get(domain.key, []))

    for cat in BENCH_CATEGORIES:
        if _score_category(text, cat) >= 2:
            matched.add(cat)

    if not matched and domain:
        matched.add("workflow" if domain.key == "business-management" else "documentation")

    return sorted(matched)


def build_skill_taxonomy_meta(name: str, content: str = "") -> dict[str, Any]:
    """YAML frontmatter: domain, methodology, bench_categories, dna_lineage."""
    from skillos.knowledge.dna_context import build_skill_dna_meta

    meta = build_skill_dna_meta(name, content)
    meta["bench_categories"] = infer_bench_categories(name, content)
    return meta


def parse_bench_categories_from_skill(skill_content: str) -> list[str]:
    """Read bench_categories from YAML frontmatter if present."""
    if not skill_content.startswith("---"):
        return []
    m = re.match(r"^---\s*\n(.*?)\n---", skill_content, re.DOTALL)
    if not m:
        return []
    try:
        import yaml
        front = yaml.safe_load(m.group(1)) or {}
    except Exception:
        return []
    raw = front.get("bench_categories") or []
    if isinstance(raw, str):
        return [c.strip() for c in raw.split(",") if c.strip()]
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    return []


def skill_body_from_file(content: str) -> str:
    """Strip YAML frontmatter from SKILL.md content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip()
    return content


def skill_injection_payload(content: str, *, max_chars: int = 4000) -> str:
    """Compact skill text for LLM injection (skip YAML, prioritize S_body + 应答速查)."""
    from skillos.skills.skill_structure import split_h2_sections

    body = skill_body_from_file(content)
    preamble, sections = split_h2_sections(body)
    priority_markers = ("应答速查", "审查应答", "清洗应答", "S_body", "S_trigger", "S_route", "核心问题")
    priority: list[str] = []
    rest: list[str] = []
    for heading, text in sections:
        block = f"## {heading}\n{text}"
        if any(m in heading for m in priority_markers):
            priority.append(block)
        elif heading not in ("认识论状态", "质量审核", "知识关联"):
            rest.append(block)
    parts: list[str] = []
    if preamble:
        parts.append(preamble)
    parts.extend(priority)
    parts.extend(rest)
    compact = "\n\n".join(parts).strip()
    return compact[:max_chars] if len(compact) > max_chars else compact


def resolve_bench_categories(
    skill_name: str,
    skill_content: str,
    meta_categories: list[str] | None = None,
) -> list[str]:
    """Categories for routing: YAML meta > infer from body."""
    if meta_categories:
        return list(meta_categories)
    from_file = parse_bench_categories_from_skill(skill_content)
    if from_file:
        return from_file
    body = skill_body_from_file(skill_content)
    return infer_bench_categories(skill_name, body)


def should_inject_skill(bench_categories: list[str], task_category: str) -> bool:
    """True when skill should be injected for this task category."""
    if not bench_categories:
        return False
    return task_category in bench_categories


def infer_task_category(text: str) -> str | None:
    """Infer SkillsBench category from task description or user message."""
    lowered = text.lower()
    scores = {cat: _score_category(lowered, cat) for cat in BENCH_CATEGORIES}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None


def skill_matches_message(
    name: str,
    body: str,
    message: str,
    *,
    meta_categories: list[str] | None = None,
) -> bool:
    """True when skill should be offered for this user message."""
    categories = resolve_bench_categories(name, body, meta_categories)
    if not categories:
        return True
    task_cat = infer_task_category(message)
    if not task_cat:
        return True
    return task_cat in categories


def filter_skills_for_message(
    skills: list[dict[str, Any]],
    message: str,
) -> list[dict[str, Any]]:
    """Drop skills whose bench_categories mismatch the inferred task category."""
    task_cat = infer_task_category(message)
    if not task_cat:
        return skills
    kept: list[dict[str, Any]] = []
    for skill in skills:
        meta = skill.get("meta") or {}
        body = skill.get("body") or ""
        name = skill.get("name") or meta.get("name") or ""
        if skill_matches_message(name, body, message, meta_categories=meta.get("bench_categories")):
            kept.append(skill)
    return kept if kept else skills


def _domain_template_from_content(skill_content: str) -> str | None:
    if not skill_content.startswith("---"):
        return None
    m = re.match(r"^---\s*\n(.*?)\n---", skill_content, re.DOTALL)
    if not m:
        return None
    try:
        import yaml
        front = yaml.safe_load(m.group(1)) or {}
    except Exception:
        return None
    return front.get("domain_template") or front.get("domain_template_id")


def _domain_pack_task_inject(
    task: Any,
    skill_content: str,
    *,
    domain_template: str | None = None,
) -> bool:
    """Force inject when task is registered in auto-generated domain pack."""
    if task is None:
        return False
    domain_tpl = domain_template or _domain_template_from_content(skill_content)
    if not domain_tpl:
        return False
    try:
        from skillos.skills.domain_pack import load_domain_pack

        pack = load_domain_pack(domain_tpl)
        if not pack:
            return False
        registered = set(pack.get("smoke_tasks") or []) | set(pack.get("anchor_tasks") or [])
        return task.task_id in registered
    except Exception:
        return False


def resolve_skill_injection(
    task_category: str,
    skill_content: str,
    bench_categories: list[str] | None = None,
    skill_name: str = "",
    *,
    task: Any | None = None,
    domain_template: str | None = None,
    pack_scoped_inject: bool = True,
) -> tuple[bool, str]:
    """Return (inject, content_to_use) for a task with known category."""
    if pack_scoped_inject and _domain_pack_task_inject(task, skill_content, domain_template=domain_template):
        return True, skill_content
    if pack_scoped_inject and task is not None and domain_template:
        try:
            from skillos.skills.domain_pack import get_pack_task_ids

            registered = set(get_pack_task_ids(domain_template))
            if registered and task.task_id not in registered:
                return False, ""
        except Exception:
            pass
    categories = bench_categories
    if not categories and skill_content:
        categories = resolve_bench_categories(skill_name, skill_content)
    if not categories:
        return True, skill_content
    if not should_inject_skill(categories, task_category):
        return False, ""
    if task is not None and skill_name:
        overlap = _task_domain_overlap(_skill_signal_terms(skill_name, skill_content), task)
        if overlap < task_skill_overlap_threshold():
            return False, ""
    return True, skill_content


def primary_bench_category(skill_name: str, skill_content: str = "") -> str | None:
    """Best-matching SkillsBench category for this skill (≥2 keyword hits)."""
    body = skill_body_from_file(skill_content) if skill_content else ""
    text = f"{skill_name} {body[:4000]}".lower()
    scores = {cat: _score_category(text, cat) for cat in BENCH_CATEGORIES}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None


# Generic workflow terms — low weight in task overlap scoring
_GENERIC_SKILL_TERMS = frozenset({
    "流程", "工单", "审批", "规则", "通知", "处理", "workflow", "sla", "审核", "步骤",
})


def _term_weight(term: str) -> int:
    if term in _GENERIC_SKILL_TERMS:
        return 1
    return max(2, min(6, len(term)))


def _compact_text(text: str) -> str:
    """Lowercase and strip spaces for zh/en keyword overlap."""
    return re.sub(r"\s+", "", text.lower())


# High-signal phrases mined from skill body (beyond category keyword list).
_BODY_TERM_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"n\+1", "n+1"),
    (r"select_related|prefetch_related", "select_related"),
    (r"\bcve\b", "cve"),
    (r"lockfile|package-lock|yarn\.lock|poetry\.lock", "lockfile"),
    (r"semver", "semver"),
    (r"sql\s*注入", "sql注入"),
    (r"时间复杂度|o\(n", "复杂度"),
    (r"传递依赖|transitive", "传递依赖"),
    (r"dependency\s*audit|依赖.*审计|供应链", "dependency audit"),
    (r"去重|duplicate|dedup", "去重"),
    (r"pivot|透视|crosstab", "pivot"),
    (r"空邮箱|fillna|异常表", "空值"),
    (r"pickle\.loads|unsafe.*deserial", "pickle"),
    (r"反序列化|deserializ", "反序列化"),
    (r"无限循环|infinite loop|死循环", "无限循环"),
    (r"timeout|max_iter", "timeout"),
)


def _skill_signal_terms(skill_name: str, skill_content: str) -> set[str]:
    """Domain terms present in the skill (category keywords + name tokens)."""
    body = skill_body_from_file(skill_content)
    text = f"{skill_name} {body[:4000]}".lower()
    compact = _compact_text(f"{skill_name} {body[:4000]}")
    terms: set[str] = set()
    for cat in BENCH_CATEGORIES:
        for kw in CATEGORY_KEYWORDS.get(cat, ()):
            k = kw.lower()
            if k in text or _compact_text(kw) in compact:
                terms.add(k)
    for pattern, term in _BODY_TERM_PATTERNS:
        if re.search(pattern, text, re.I) or re.search(pattern, body[:4000], re.I):
            terms.add(term.lower())
    for token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z]{3,}", skill_name.lower()):
        terms.add(token)
    return terms


def _term_in_description(term: str, description: str) -> bool:
    t = term.lower()
    d = description.lower()
    dc = _compact_text(description)
    if t in d or _compact_text(term) in dc:
        return True
    # e.g. term "dependency audit" ↔ description "dependency audit CVE"
    if " " in t and all(part in d for part in t.split()):
        return True
    return False


def _task_term_overlap(skill_terms: set[str], task: Any) -> int:
    """Weighted overlap between skill terms and task description (not task_id)."""
    desc = task.description.lower()
    return sum(_term_weight(t) for t in skill_terms if _term_in_description(t, desc))


def _task_domain_overlap(skill_terms: set[str], task: Any) -> int:
    """Overlap using non-generic skill terms against task description only."""
    domain = skill_terms - _GENERIC_SKILL_TERMS
    if not domain:
        return _task_term_overlap(skill_terms, task)
    desc = task.description.lower()
    return sum(_term_weight(t) for t in domain if _term_in_description(t, desc))


def task_skill_overlap_threshold() -> int:
    """Minimum domain overlap required to inject skill for a specific task."""
    return 2


def rank_bench_tasks_for_skill(
    skill_name: str,
    skill_content: str,
    tasks: list[Any],
    *,
    bench_categories: list[str] | None = None,
    limit: int = 8,
) -> list[Any]:
    """Pick up to *limit* in-scope tasks ranked by skill↔task term overlap."""
    categories = bench_categories or resolve_bench_categories(skill_name, skill_content)
    primary = primary_bench_category(skill_name, skill_content)
    skill_terms = _skill_signal_terms(skill_name, skill_content)

    def task_rank(task: Any) -> tuple[int, int, int, int, str]:
        overlap = _task_term_overlap(skill_terms, task)
        in_scope = 1 if should_inject_skill(categories, task.category) else 0
        primary_match = 1 if primary and task.category == primary else 0
        cat_score = _score_category(task.description.lower(), task.category)
        return (overlap, primary_match, in_scope, cat_score, task.task_id)

    in_scope = [t for t in tasks if should_inject_skill(categories, t.category)]
    if primary:
        primary_pool = [t for t in in_scope if t.category == primary]
        pool = primary_pool if primary_pool else in_scope
    else:
        pool = in_scope or list(tasks)
    ranked = sorted(pool, key=task_rank, reverse=True)

    if skill_terms:
        with_overlap = [t for t in ranked if _task_term_overlap(skill_terms, t) > 0]
        if with_overlap:
            ranked = with_overlap + [t for t in ranked if t not in with_overlap]

    return ranked[:limit]


def backfill_skill_routing_meta(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Merge domain/methodology/bench_categories into an existing SKILL.md."""
    from skillos.skills.skill_store import _compose, _split_front_matter

    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    name = meta.get("name") or path.parent.name
    taxonomy = build_skill_taxonomy_meta(name, body)
    changed = False
    for key, value in taxonomy.items():
        if meta.get(key) != value:
            meta[key] = value
            changed = True
    result = {"path": str(path), "name": name, "changed": changed, **taxonomy}
    if changed and not dry_run:
        path.write_text(_compose(meta, body), encoding="utf-8")
    return result


def load_skill_routing_info(skill_path: str) -> dict[str, Any]:
    """Load name, body, and routing metadata from a SKILL.md path."""
    path = Path(skill_path)
    raw = path.read_text(encoding="utf-8")
    name = path.parent.name
    categories: list[str] = []
    meta: dict[str, Any] = {}
    if raw.startswith("---"):
        try:
            import yaml
            fm = re.match(r"^---\s*\n(.*?)\n---", raw, re.DOTALL)
            if fm:
                front = yaml.safe_load(fm.group(1)) or {}
                meta = front
                name = front.get("name") or name
                categories = resolve_bench_categories(
                    name, raw, front.get("bench_categories"),
                )
        except Exception:
            categories = infer_bench_categories(name, raw)
    else:
        categories = infer_bench_categories(name, raw)
    return {
        "name": name,
        "path": str(path),
        "content": raw,
        "bench_categories": categories,
        "meta": meta,
    }
