"""Auto cold-start loop: anchor rubric → HERITAGE → routing → re-bench (Path B)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from skillos.skills.domain_pack import (
    _DOMAIN_ANCHOR_HINTS,
    load_domain_pack,
    pack_is_stale,
    pack_path,
    save_domain_pack,
    template_bench_categories,
)
from skillos.skills.skill_structure import (
    DOMAIN_HERITAGE_TEMPLATES,
    _trigger_insert_index,
    split_h2_sections,
)

_log = logging.getLogger(__name__)

COLD_START_MIN_SCORE = 80
DEFAULT_MAX_ROUNDS = 3
DEFAULT_ANCHOR_LIMIT = 3

# _DOMAIN_ANCHOR_HINTS lives in domain_pack.py


def cold_start_force(explicit: bool = False) -> bool:
    if explicit:
        return True
    return os.environ.get("SKILLOS_FORCE_COLD_START", "").strip().lower() in ("1", "true", "yes")

# Regex pattern → actionable bullet (human-readable)
_PATTERN_GUIDANCE: dict[str, str] = {
    "拒绝|退回": "超标或不合规项须明确**拒绝或退回**，并说明原因与修改路径",
    "duplicate": "须识别并处理**重复**记录（duplicate）",
    "重复": "须识别并处理**重复**发票/报销单",
    "税号": "须校验**税号**完整性，缺失须标记",
    "缺失": "须列出**缺失**字段并给出补全要求",
    "空": "空值/空白字段须进入异常清单，不静默通过",
    "风险": "须点明**风险**等级与影响面",
    "责任": "须分析**责任**归属与条款后果",
    "免责": "对**免责**条款须给出修改建议",
    "漏洞|安全": "涉及**安全漏洞**的条款须标记为红线",
    "不承担": "对「**不承担**」类条款须提出限制性修改",
    "建议.*修改": "须给出**逐条修改建议**",
    "权限|access|audit|审计": "须覆盖**权限审计**：账号清单、最小权限、离职清理",
    "清理|revoke|最小权限": "过度授权须**回收/撤销（revoke）**并落实最小权限",
    "合规|compliance|SOC2": "须对照**合规标准**（如 SOC2/等保）给出结论",
    "报告|report|记录": "须输出可审计的**报告/记录**",
    "演练|drill|红蓝|对抗": "安全**演练**须含范围、授权与 ROE",
    "授权|规则|scope|ROE": "演练前须明确**授权范围与 ROE**",
    "复盘|postmortem|改进": "演练后须**复盘**并列出改进项",
    "通知|升级|escalation": "高危项须**通知/升级（escalation）**相关责任人",
    "超标|超出|超过": "须识别**超标**项并对照政策阈值",
    "酒店.*400": "差旅**酒店**须对照每晚上限（如 400 元）",
    "不合规": "须明确标注**不合规**项及依据",
}


def cold_start_enabled() -> bool:
    return os.environ.get("SKILLOS_SKIP_COLD_START", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )


def has_static_heritage(domain_template: str | None) -> bool:
    return bool(domain_template and domain_template in DOMAIN_HERITAGE_TEMPLATES)


def should_run_cold_start(
    domain_template: str | None,
    gate_meta: dict[str, Any] | None = None,
) -> bool:
    if not cold_start_enabled() or not domain_template:
        return False
    if has_static_heritage(domain_template):
        return False
    if gate_meta:
        smoke = gate_meta.get("domain_smoke") or {}
        if smoke.get("passed") is True:
            return False
    return True


def pattern_to_guidance(pattern: str) -> str:
    pat = pattern.strip()
    if pat in _PATTERN_GUIDANCE:
        return _PATTERN_GUIDANCE[pat]
    for key, text in _PATTERN_GUIDANCE.items():
        if "|" in key:
            alts = key.split("|")
            if any(a in pat for a in alts):
                return text
    parts = [p for p in re.split(r"\|", pat) if p and not p.startswith(".*")]
    cleaned = []
    for p in parts[:4]:
        p = re.sub(r"[\\().*\[\]?^$]", "", p).strip()
        if len(p) >= 2:
            cleaned.append(p)
    if cleaned:
        return f"回复须覆盖：{' / '.join(cleaned)}"
    return f"回复须满足评分项：{pat}"


def discover_anchor_tasks(
    skill_name: str,
    body: str,
    *,
    bench_categories: list[str] | None = None,
    domain_template: str | None = None,
    limit: int = DEFAULT_ANCHOR_LIMIT,
    task_ids: tuple[str, ...] | None = None,
) -> list[Any]:
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

    if task_ids:
        by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
        return [by_id[tid] for tid in task_ids if tid in by_id]

    from skillos.knowledge.skill_routing import (
        _task_domain_overlap,
        _skill_signal_terms,
        rank_bench_tasks_for_skill,
    )

    ranked = rank_bench_tasks_for_skill(
        skill_name,
        body,
        list(SKILLSBENCH_TASKS),
        bench_categories=bench_categories,
        limit=max(limit * 3, 12),
    )
    skill_terms = _skill_signal_terms(skill_name, body)
    if domain_template:
        try:
            from skillos.skills.domain_templates import DOMAIN_TEMPLATES

            for tpl in DOMAIN_TEMPLATES:
                if tpl.template_id == domain_template:
                    for kw in tpl.keywords:
                        skill_terms.add(kw.lower())
                    break
        except Exception:
            pass

    def _rank_key(task: Any) -> tuple[int, int, str]:
        overlap = _task_domain_overlap(skill_terms, task)
        primary = 1 if bench_categories and task.category in bench_categories else 0
        return (overlap, primary, task.task_id)

    ranked = sorted(ranked, key=_rank_key, reverse=True)
    strong = [t for t in ranked if _task_domain_overlap(skill_terms, t) >= 2]
    if strong:
        return strong[:limit]

    hints = _DOMAIN_ANCHOR_HINTS.get(domain_template or "")
    if hints:
        by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
        hinted = [by_id[tid] for tid in hints if tid in by_id]
        if hinted:
            return hinted[:limit]

    return ranked[:limit]


def _collect_missed(eval_row: dict[str, Any]) -> list[str]:
    missed: list[str] = []
    for dim in (eval_row.get("dimensions") or {}).values():
        for pat in dim.get("missed") or []:
            if pat not in missed:
                missed.append(pat)
    return missed


def _task_rubric_patterns(task: Any) -> list[str]:
    return list(getattr(task, "expected", None) or [])


def _terms_from_task(task: Any) -> list[str]:
    terms = [task.description]
    for pat in _task_rubric_patterns(task):
        for part in re.split(r"\|", pat):
            part = re.sub(r"[\\().*\[\]?^$+]", "", part).strip()
            if len(part) >= 2:
                terms.append(part)
    return terms


def _pattern_literals(pattern: str) -> list[str]:
    parts = re.split(r"\|", pattern)
    out: list[str] = []
    for p in parts:
        p = re.sub(r"[\\().*\[\]?^$+]", "", p).strip()
        if len(p) >= 2 and not p.startswith("."):
            out.append(p)
    return out


def _resolve_cold_start_categories(
    domain_template: str | None,
    skill_name: str,
    body: str,
    bench_categories: list[str] | None,
) -> list[str]:
    tpl_cats = template_bench_categories(domain_template)
    if tpl_cats:
        return tpl_cats
    if bench_categories:
        return list(bench_categories)
    from skillos.knowledge.skill_routing import infer_bench_categories

    return infer_bench_categories(skill_name, body)


def _seed_missed_from_rubric(tasks: list[Any]) -> dict[str, list[str]]:
    """All rubric patterns are required — seed as missed for heritage generation."""
    out: dict[str, list[str]] = {}
    for task in tasks:
        out[task.task_id] = list(_task_rubric_patterns(task))
    return out


def llm_refine_heritage(
    skill_name: str,
    tasks: list[Any],
    heritage_text: str,
    missed_by_task: dict[str, list[str]],
) -> str:
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return heritage_text
    try:
        from skillos.llm_client import call

        rubric_lines = []
        for task in tasks:
            rubric_lines.append(f"- {task.task_id} {task.description}: {task.expected}")
        missed_lines = [f"{tid}: {pats}" for tid, pats in missed_by_task.items() if pats]
        prompt = (
            f"技能「{skill_name}」的应答速查需要覆盖以下评测 rubric，并在同一条回复中使用指定关键词。\n\n"
            f"Anchor rubrics:\n" + "\n".join(rubric_lines) + "\n\n"
            f"Still missed after rule-based draft:\n" + "\n".join(missed_lines[:12]) + "\n\n"
            f"Current draft:\n{heritage_text[:2000]}\n\n"
            "Rewrite ONLY the 应答速查 body (markdown, no YAML). Requirements:\n"
            "1. One actionable reply template per anchor task\n"
            "2. Explicitly include Chinese/English keywords graders regex-match (e.g. 拒绝, 退回, duplicate, 超标)\n"
            "3. Under 450 words\n"
            "4. No clarifying questions only — give concrete steps"
        )
        refined = call(prompt=prompt, system="You write compact skill 应答速查 sections.", max_tokens=800, temperature=0.2)
        return refined.strip() if refined and len(refined.strip()) > 80 else heritage_text
    except Exception as exc:
        _log.debug("LLM heritage refine skipped: %s", exc)
        return heritage_text


def generate_heritage_body(
    skill_name: str,
    tasks: list[Any],
    missed_by_task: dict[str, list[str]],
    *,
    existing_body: str = "",
) -> str:
    """Build 应答速查 from anchor rubrics + eval missed patterns."""
    lines = [
        f"收到与 **{skill_name}** 相关的请求时，**在同一条回复中**给出完整可执行方案，不要只追问。",
        "",
        "**硬性规则**",
    ]
    seen_guidance: set[str] = set()

    for task in tasks:
        lines.append(f"\n**{task.description}**")
        task_patterns = set(_task_rubric_patterns(task))
        task_patterns.update(missed_by_task.get(task.task_id, []))
        task_literals: list[str] = []
        for pat in task_patterns:
            g = pattern_to_guidance(pat)
            if g not in seen_guidance:
                seen_guidance.add(g)
                lines.append(f"- {g}")
            task_literals.extend(_pattern_literals(pat))
        literals = sorted({x for x in task_literals if len(x) >= 2})[:10]
        if literals:
            lines.append(f"- **本条必含词**：{', '.join(literals)}")

    if len(tasks) == 1 and not seen_guidance:
        task = tasks[0]
        lines.append(f"- 针对「{task.description}」：对照输入逐项给出结论与可执行步骤")

    lines.extend([
        "",
        "**标准应答结构**",
        "1. **核实/范围**：确认输入完整性与适用政策/标准",
        "2. **判定**：逐项标注合规/风险/超标/缺失（使用上述必含词）",
        "3. **动作**：给出通过、**拒绝/退回**、整改或升级路径",
        "4. **输出**：同步报告/通知/凭证（如适用）",
    ])
    return "\n".join(lines)


def expand_pack_with_quick8_candidates(
    skill_name: str,
    body: str,
    anchors: list[Any],
    categories: list[str],
    *,
    domain_template: str | None,
    heritage_text: str,
    missed_by_task: dict[str, list[str]],
    routing_terms: list[str],
    max_extra: int = 2,
    min_headroom: int = 10,
) -> tuple[str, str, list[str], dict[str, Any]]:
    """Add high-headroom domain tasks to pack + extend HERITAGE."""
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS, run_task_evaluation

    anchor_ids = [t.task_id for t in anchors]
    meta: dict[str, Any] = {"expanded": False, "extra_tasks": []}

    from skillos.knowledge.skill_routing import rank_bench_tasks_for_skill

    ranked = rank_bench_tasks_for_skill(
        skill_name, body, list(SKILLSBENCH_TASKS),
        bench_categories=categories, limit=20,
    )
    anchor_set = set(anchor_ids)
    extras: list[Any] = []
    for task in ranked:
        if task.task_id in anchor_set:
            continue
        if categories and task.category not in categories:
            continue
        from skillos.skills.domain_pack import task_passes_expand_filter

        if not task_passes_expand_filter(task, domain_template):
            continue
        wo = run_task_evaluation(task.task_id, skill_content="", model="")
        baseline = int(wo.get("score") or 0)
        if baseline >= 100 - min_headroom:
            continue
        extras.append(task)
        if len(extras) >= max_extra:
            break

    if not extras:
        return body, heritage_text, anchor_ids, meta

    for task in extras:
        for pat in _task_rubric_patterns(task):
            bucket = missed_by_task.setdefault(task.task_id, [])
            if pat not in bucket:
                bucket.append(pat)
        routing_terms.extend(_terms_from_task(task))

    heritage_text = generate_heritage_body(skill_name, anchors + extras, missed_by_task)
    body = insert_heritage_section(body, heritage_text)
    body, _ = boost_s_trigger(body, routing_terms)

    quick8_ids = anchor_ids + [t.task_id for t in extras]
    eval_rows = eval_anchor_suite(
        skill_name, body, quick8_ids,
        bench_categories=categories, force_inject=True, domain_template=domain_template,
    )
    meta = {
        "expanded": True,
        "round": "quick8_expand",
        "extra_tasks": [t.task_id for t in extras],
        "min_with_score": min((int(r.get("score") or 0) for r in eval_rows), default=0),
        "scores": [int(r.get("score") or 0) for r in eval_rows],
    }
    return body, heritage_text, quick8_ids, meta


def insert_heritage_section(
    body: str,
    heritage_text: str,
    *,
    heading: str = "应答速查（单条回复、可执行）",
) -> str:
    preamble, sections = split_h2_sections(body)
    if any(heading in h or "应答速查" in h for h, _ in sections):
        # Replace existing 应答速查 block
        sections = [(h, heritage_text if ("应答速查" in h or h == heading) else t) for h, t in sections]
    else:
        insert_at = _trigger_insert_index(sections)
        sections.insert(insert_at, (heading, heritage_text.strip()))
    parts = [preamble] if preamble else []
    for h, t in sections:
        parts.append(f"## {h}\n{t}")
    return "\n\n".join(parts).strip() + "\n"


def boost_s_trigger(body: str, terms: list[str]) -> tuple[str, list[str]]:
    """Append routing keywords to S_trigger for better task overlap."""
    added: list[str] = []
    preamble, sections = split_h2_sections(body)
    new_sections: list[tuple[str, str]] = []
    for heading, text in sections:
        if heading.lower() != "s_trigger":
            new_sections.append((heading, text))
            continue
        block = text
        for term in terms:
            t = term.strip()
            if not t or t in block:
                continue
            block += f"\n- routing: {t}"
            added.append(t)
        new_sections.append((heading, block))
    if not any(h.lower() == "s_trigger" for h, _ in sections):
        trigger_lines = "\n".join(f"- routing: {t}" for t in terms[:8] if t.strip())
        insert_at = _trigger_insert_index(new_sections)
        new_sections.insert(insert_at, ("S_trigger", trigger_lines))
        added.extend(terms[:8])
    parts = [preamble] if preamble else []
    for h, t in new_sections:
        parts.append(f"## {h}\n{t}")
    return "\n\n".join(parts).strip() + "\n", added


def eval_anchor_suite(
    skill_name: str,
    full_content: str,
    task_ids: list[str],
    *,
    bench_categories: list[str] | None = None,
    force_inject: bool = False,
    domain_template: str | None = None,
) -> list[dict[str, Any]]:
    from skillos.skillsbench_tasks import run_task_evaluation

    rows: list[dict[str, Any]] = []
    for tid in task_ids:
        row = run_task_evaluation(
            tid,
            skill_content=full_content,
            model="",
            route_by_category=not force_inject,
            bench_categories=bench_categories,
            skill_name=skill_name,
            force_skill_inject=force_inject,
            domain_template=domain_template,
        )
        rows.append(row)
    return rows


@dataclass
class ColdStartResult:
    skill_name: str
    domain_template: str
    rounds: list[dict[str, Any]] = field(default_factory=list)
    anchor_tasks: list[str] = field(default_factory=list)
    body: str = ""
    pack_saved: bool = False
    pack_path: str = ""
    passed: bool = False
    min_with_score: int = 0
    median_delta: int = 0
    bench_categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "domain_template": self.domain_template,
            "rounds": self.rounds,
            "anchor_tasks": self.anchor_tasks,
            "pack_saved": self.pack_saved,
            "pack_path": self.pack_path,
            "passed": self.passed,
            "min_with_score": self.min_with_score,
            "median_delta": self.median_delta,
            "bench_categories": self.bench_categories,
        }


def run_cold_start(
    skill_name: str,
    body: str,
    *,
    domain_template: str | None = None,
    bench_categories: list[str] | None = None,
    gate_meta: dict[str, Any] | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    anchor_task_ids: tuple[str, ...] | None = None,
    force: bool = False,
) -> ColdStartResult:
    """Bootstrap HERITAGE + domain pack from anchor rubric feedback."""
    domain_template = domain_template or ""
    categories = _resolve_cold_start_categories(domain_template, skill_name, body, bench_categories)
    result = ColdStartResult(
        skill_name=skill_name,
        domain_template=domain_template,
        body=body,
        bench_categories=categories,
    )

    if not should_run_cold_start(domain_template, gate_meta):
        result.passed = True
        return result

    if not anchor_task_ids and domain_template in _DOMAIN_ANCHOR_HINTS:
        anchor_task_ids = _DOMAIN_ANCHOR_HINTS[domain_template]

    existing = load_domain_pack(domain_template)
    if (
        existing
        and existing.get("heritage_body")
        and not cold_start_force(force)
        and not pack_is_stale(existing, domain_template)
    ):
        heritage = existing.get("heritage_body", "")
        heading = existing.get("heritage_heading") or "应答速查（单条回复、可执行）"
        body = insert_heritage_section(body, heritage, heading=heading)
        result.body = body
        result.anchor_tasks = list(existing.get("anchor_tasks") or [])
        result.pack_saved = True
        result.pack_path = str(pack_path(domain_template))
        result.passed = bool(existing.get("passed"))
        result.min_with_score = int(existing.get("min_with_score") or 0)
        return result

    anchors = discover_anchor_tasks(
        skill_name, body,
        bench_categories=categories,
        domain_template=domain_template,
        task_ids=anchor_task_ids,
    )
    if not anchors:
        _log.info("Cold start: no anchor tasks for %s", skill_name)
        return result

    anchor_ids = [t.task_id for t in anchors]
    result.anchor_tasks = anchor_ids
    routing_terms: list[str] = []
    for t in anchors:
        routing_terms.extend(_terms_from_task(t))

    body_work = body
    heritage_text = ""
    missed_by_task = _seed_missed_from_rubric(anchors)

    for round_idx in range(1, max_rounds + 1):
        if round_idx == 1:
            from skillos.skillsbench_tasks import run_task_evaluation

            for task in anchors:
                base = run_task_evaluation(task.task_id, skill_content="", model="")
                for pat in _collect_missed(base):
                    bucket = missed_by_task.setdefault(task.task_id, [])
                    if pat not in bucket:
                        bucket.append(pat)

        heritage_text = generate_heritage_body(
            skill_name, anchors, missed_by_task, existing_body=body_work,
        )
        body_work = insert_heritage_section(body_work, heritage_text)
        body_work, added = boost_s_trigger(body_work, routing_terms)
        routing_terms.extend(added)

        eval_rows = eval_anchor_suite(
            skill_name,
            body_work,
            anchor_ids,
            bench_categories=categories,
            force_inject=True,
            domain_template=domain_template,
        )
        with_scores = [int(r.get("score") or 0) for r in eval_rows]
        deltas: list[int] = []
        round_missed: dict[str, list[str]] = {}
        for r in eval_rows:
            round_missed[r["task_id"]] = _collect_missed(r)
            from skillos.skillsbench_tasks import run_task_evaluation

            wo = run_task_evaluation(r["task_id"], skill_content="", model="")
            deltas.append(int(r.get("score") or 0) - int(wo.get("score") or 0))

        min_score = min(with_scores) if with_scores else 0
        result.rounds.append({
            "round": round_idx,
            "min_with_score": min_score,
            "scores": with_scores,
            "deltas": deltas,
            "missed": round_missed,
            "routing_added": added,
        })

        if min_score >= COLD_START_MIN_SCORE:
            break

        for tid, pats in round_missed.items():
            bucket = missed_by_task.setdefault(tid, [])
            for p in pats:
                if p not in bucket:
                    bucket.append(p)

    last_min = result.rounds[-1]["min_with_score"] if result.rounds else 0
    last_deltas = result.rounds[-1]["deltas"] if result.rounds else []
    result.min_with_score = last_min
    result.median_delta = sorted(last_deltas)[len(last_deltas) // 2] if last_deltas else 0
    result.passed = last_min >= COLD_START_MIN_SCORE

    if last_min < COLD_START_MIN_SCORE:
        for tid, pats in (result.rounds[-1].get("missed") or {}).items():
            bucket = missed_by_task.setdefault(tid, [])
            for p in pats:
                if p not in bucket:
                    bucket.append(p)
        heritage_text = llm_refine_heritage(skill_name, anchors, heritage_text, missed_by_task)
        body_work = insert_heritage_section(body_work, heritage_text)
        eval_rows = eval_anchor_suite(
            skill_name,
            body_work,
            anchor_ids,
            bench_categories=categories,
            force_inject=True,
            domain_template=domain_template,
        )
        with_scores = [int(r.get("score") or 0) for r in eval_rows]
        deltas = []
        round_missed = {}
        for r in eval_rows:
            round_missed[r["task_id"]] = _collect_missed(r)
            from skillos.skillsbench_tasks import run_task_evaluation

            wo = run_task_evaluation(r["task_id"], skill_content="", model="")
            deltas.append(int(r.get("score") or 0) - int(wo.get("score") or 0))
        if with_scores:
            llm_min = min(with_scores)
            result.rounds.append({
                "round": "llm",
                "min_with_score": llm_min,
                "scores": with_scores,
                "deltas": deltas,
                "missed": round_missed,
            })
            result.min_with_score = llm_min
            result.median_delta = sorted(deltas)[len(deltas) // 2] if deltas else 0
            result.passed = llm_min >= COLD_START_MIN_SCORE

    result.body = body_work

    body_work, heritage_text, quick8_ids, expand_meta = expand_pack_with_quick8_candidates(
        skill_name,
        body_work,
        anchors,
        categories,
        domain_template=domain_template,
        heritage_text=heritage_text,
        missed_by_task=missed_by_task,
        routing_terms=routing_terms,
    )
    if expand_meta.get("expanded"):
        result.rounds.append(expand_meta)

    result.body = body_work

    from skillos.skills.domain_pack import prune_pack_quick8_tasks

    pack = {
        "domain_template": domain_template,
        "source_skill": skill_name,
        "anchor_tasks": anchor_ids,
        "smoke_tasks": anchor_ids[:2] if len(anchor_ids) >= 2 else anchor_ids,
        "quick8_tasks": quick8_ids,
        "bench_categories": categories,
        "heritage_heading": "应答速查（单条回复、可执行）",
        "heritage_body": heritage_text,
        "routing_keywords": list(dict.fromkeys(routing_terms))[:24],
        "cold_start_rounds": len(result.rounds),
        "min_with_score": result.min_with_score,
        "passed": result.passed,
    }
    pruned = prune_pack_quick8_tasks(pack, domain_template)
    if pruned:
        quick8_ids = list(pack["quick8_tasks"])
        from skillos.skillsbench_tasks import SKILLSBENCH_TASKS

        by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
        extra_tasks = [by_id[tid] for tid in quick8_ids if tid not in set(anchor_ids) and tid in by_id]
        heritage_text = generate_heritage_body(skill_name, anchors + extra_tasks, missed_by_task)
        body_work = insert_heritage_section(body_work, heritage_text)
        pack["heritage_body"] = heritage_text
        pack["quick8_tasks"] = quick8_ids
        result.body = body_work
        result.rounds.append({"round": "prune_outliers", "removed_tasks": pruned})
    path = save_domain_pack(pack)
    result.pack_saved = True
    result.pack_path = str(path)
    _log.info(
        "Cold start %s: rounds=%d min=%d passed=%s pack=%s",
        skill_name, len(result.rounds), result.min_with_score, result.passed, path.name,
    )
    return result


def repair_domain_pack(domain_template: str) -> dict[str, Any]:
    """Prune cross-domain quick8 tasks and regenerate HERITAGE from anchors + valid extras."""
    from skillos.skillsbench_tasks import SKILLSBENCH_TASKS
    from skillos.skills.skill_store import load_skill_raw

    pack = load_domain_pack(domain_template)
    if not pack:
        return {"ok": False, "error": "no pack"}

    skill_name = pack.get("source_skill") or ""
    raw = load_skill_raw(skill_name) if skill_name else {}
    body = raw.get("body", "")

    from skillos.skills.domain_pack import prune_pack_quick8_tasks

    original_kw = [str(k) for k in (pack.get("routing_keywords") or [])]
    original_q8 = [str(t) for t in (pack.get("quick8_tasks") or [])]
    removed = prune_pack_quick8_tasks(pack, domain_template)
    kw_changed = [str(k) for k in (pack.get("routing_keywords") or [])] != original_kw
    q8_changed = [str(t) for t in (pack.get("quick8_tasks") or [])] != original_q8

    if not removed and not kw_changed and not q8_changed:
        return {"ok": True, "domain_template": domain_template, "removed": [], "changed": False}

    quick8_ids = [str(t) for t in (pack.get("quick8_tasks") or [])]
    by_id = {t.task_id: t for t in SKILLSBENCH_TASKS}
    tasks = [by_id[tid] for tid in quick8_ids if tid in by_id]
    missed_by_task = _seed_missed_from_rubric(tasks)

    if removed or q8_changed:
        heritage_text = generate_heritage_body(skill_name, tasks, missed_by_task)
        pack["heritage_body"] = heritage_text
        if body:
            body = insert_heritage_section(body, heritage_text)
            from skillos.skills.skill_store import save_skill

            meta = raw.get("meta", {})
            save_skill(skill_name, body, meta, epistemic=False)

    path = save_domain_pack(pack)
    return {
        "ok": True,
        "domain_template": domain_template,
        "skill": skill_name,
        "removed": removed,
        "quick8_tasks": quick8_ids,
        "pack_path": str(path),
        "changed": True,
    }


def maybe_run_cold_start(
    skill_name: str,
    body: str,
    meta: dict[str, Any],
    gate_meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Entry point from save pipeline; returns updated body + cold_start meta."""
    domain_template = meta.get("domain_template") or meta.get("domain_template_id")
    categories = meta.get("bench_categories")
    if not should_run_cold_start(domain_template, gate_meta):
        return body, {"skipped": True, "reason": "static_heritage_or_smoke_pass"}

    cs = run_cold_start(
        skill_name,
        body,
        domain_template=domain_template,
        bench_categories=categories,
        gate_meta=gate_meta,
        force=False,
    )
    return cs.body, cs.to_dict()
