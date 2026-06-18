"""Dynamic domain packs — auto-generated HERITAGE, smoke tasks, routing (Path B cold start)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# Re-export hints for stale check (avoid circular import at module load)
_DOMAIN_ANCHOR_HINTS: dict[str, tuple[str, ...]] = {
    "finance-expense-audit": ("workflow-082", "workflow-083"),
    "law-contract-review": ("workflow-084",),
    "security-audit": ("workflow-076", "workflow-079"),
}

# Hard blocklist for quick8 expand (known cross-domain task ids)
_DOMAIN_EXPAND_EXCLUDE: dict[str, tuple[str, ...]] = {
    "finance-expense-audit": ("workflow-064", "workflow-076", "workflow-079"),
    "law-contract-review": ("workflow-064", "workflow-082", "workflow-083"),
    "security-audit": ("workflow-082", "workflow-083", "workflow-070"),
}

_PACKS_DIR = Path(__file__).resolve().parents[2] / "data" / "domain_packs"


def packs_dir() -> Path:
    _PACKS_DIR.mkdir(parents=True, exist_ok=True)
    return _PACKS_DIR


def pack_path(domain_template: str) -> Path:
    safe = domain_template.replace("/", "_").strip() or "unknown"
    return packs_dir() / f"{safe}.json"


def load_domain_pack(domain_template: str | None) -> dict[str, Any] | None:
    if not domain_template:
        return None
    path = pack_path(domain_template)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_domain_pack(pack: dict[str, Any]) -> Path:
    domain_template = pack.get("domain_template") or "unknown"
    pack.setdefault("updated_at", int(time.time()))
    path = pack_path(domain_template)
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_smoke_task_ids(
    domain_template: str | None,
    skill_name: str = "",
) -> tuple[str, ...]:
    pack = load_domain_pack(domain_template)
    if not pack:
        return ()
    tasks = pack.get("smoke_tasks") or pack.get("anchor_tasks") or []
    return tuple(str(t) for t in tasks if t)


def get_heritage_entry(domain_template: str | None) -> tuple[str, str] | None:
    pack = load_domain_pack(domain_template)
    if not pack:
        return None
    heading = pack.get("heritage_heading") or "应答速查（单条回复、可执行）"
    body = (pack.get("heritage_body") or "").strip()
    if not body:
        return None
    return heading, body


def get_routing_keywords(domain_template: str | None) -> tuple[str, ...]:
    pack = load_domain_pack(domain_template)
    if not pack:
        return ()
    raw = pack.get("routing_keywords") or []
    return tuple(str(k) for k in raw if k)


def template_bench_categories(domain_template: str | None) -> list[str]:
    """Bench categories from domain template definition (authoritative for cold start)."""
    if not domain_template:
        return []
    try:
        from skillos.skills.domain_templates import get_template

        tpl = get_template(domain_template)
        if tpl and tpl.bench_categories:
            return list(tpl.bench_categories)
    except Exception:
        pass
    return []


def get_pack_task_ids(domain_template: str | None) -> tuple[str, ...]:
    pack = load_domain_pack(domain_template)
    if not pack:
        return ()
    ids: set[str] = set()
    for key in ("anchor_tasks", "smoke_tasks", "quick8_tasks"):
        for tid in pack.get(key) or []:
            if tid:
                ids.add(str(tid))
    return tuple(sorted(ids))


def get_expand_filters(
    domain_template: str | None,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return (negative_keywords, excluded_task_ids, positive_keywords) for quick8 expand."""
    negatives: list[str] = []
    positives: list[str] = []
    excluded: list[str] = list(_DOMAIN_EXPAND_EXCLUDE.get(domain_template or "", ()))

    if domain_template:
        try:
            from skillos.skills.domain_templates import get_template

            dt = get_template(domain_template)
            if dt:
                negatives.extend(dt.negative_keywords)
                positives.extend(dt.keywords)
        except Exception:
            pass

    return tuple(negatives), tuple(excluded), tuple(positives)


def task_passes_expand_filter(task: Any, domain_template: str | None) -> bool:
    """True when a bench task is eligible for domain-pack quick8 expansion."""
    negatives, excluded, positives = get_expand_filters(domain_template)
    tid = getattr(task, "task_id", "") or ""
    if tid in excluded:
        return False

    desc = (getattr(task, "description", "") or "").lower()
    blob = f"{desc} {tid}".lower()
    for neg in negatives:
        if neg.lower() in blob:
            return False

    if positives:
        if not any(kw.lower() in blob for kw in positives if len(kw) >= 2):
            return False
    return True


def filter_routing_keywords(keywords: list[str], domain_template: str | None) -> list[str]:
    """Drop routing terms that match domain negative keywords."""
    negatives, _, _ = get_expand_filters(domain_template)
    if not negatives:
        return keywords
    kept: list[str] = []
    for kw in keywords:
        blob = kw.lower()
        if any(neg.lower() in blob for neg in negatives):
            continue
        kept.append(kw)
    return kept


def prune_pack_quick8_tasks(pack: dict[str, Any], domain_template: str | None) -> list[str]:
    """Remove cross-domain tasks from quick8_tasks; return removed ids."""
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    anchor_ids = {str(t) for t in (pack.get("anchor_tasks") or [])}
    by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
    quick8 = [str(t) for t in (pack.get("quick8_tasks") or [])]
    kept: list[str] = []
    removed: list[str] = []
    seen: set[str] = set()

    for tid in quick8:
        if tid in seen:
            continue
        seen.add(tid)
        if tid in anchor_ids:
            kept.append(tid)
            continue
        task = by_id.get(tid)
        if task and task_passes_expand_filter(task, domain_template):
            kept.append(tid)
        else:
            removed.append(tid)

    pack["quick8_tasks"] = kept
    raw_kw = [str(k) for k in (pack.get("routing_keywords") or [])]
    if raw_kw:
        pack["routing_keywords"] = filter_routing_keywords(raw_kw, domain_template)
    return removed


def pack_is_stale(pack: dict[str, Any], domain_template: str | None) -> bool:
    """True when auto-generated pack anchors don't match domain hints."""
    if not pack or not domain_template:
        return False
    hints = _DOMAIN_ANCHOR_HINTS.get(domain_template)
    if not hints:
        return False
    registered = set(pack.get("anchor_tasks") or [])
    return not registered.intersection(hints)
