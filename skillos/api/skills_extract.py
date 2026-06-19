"""Skill extraction pipeline endpoints — dispatch, create, finalize, status, resume, ingest.

Extracted from skills.py to keep file sizes manageable.
"""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from skillos.identity.middleware import AuthContext, get_optional_auth, require_auth
from skillos.api._skills_shared import (
    CreateSkillRequest,
    DispatchRequest,
    _reset_tenant,
    _skills_list,
    _tenant_context_from_auth,
    _tenant_from_context,
)

router = APIRouter()
_log = logging.getLogger(__name__)


def _persist_created_skill(
    name: str,
    content: str,
    llm_args: tuple,
    *,
    source: str = "",
    source_type: str = "llm_generated",
    meta: dict | None = None,
    team_context: dict | None = None,
) -> dict:
    """Save skill with epistemology pipeline; return epistemic summary for API."""
    from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload
    from skillos.knowledge.lineage import record_skill_precipitation
    from skillos.skills.portable_skill import finalize_portable_skill
    from skillos.skills.skill_store import _skill_path, load_skill_raw, resolve_skills_root, save_skill
    from skillos.skills.variants import register_precipitation_variant

    ctx = team_context or {}
    tenant = _tenant_from_context(ctx)
    finalized = finalize_portable_skill(name, content)
    agent_meta = dict(meta or {})
    domain_tpl = agent_meta.get("domain_template") or agent_meta.get("domain_template_id")
    domain_tpl_ids = agent_meta.get("domain_template_ids")

    body_out = finalized["body"]
    heritage_meta: dict = {}
    old_body = ""
    try:
        from skillos.skills.skill_store import _skill_path, load_skill_raw, resolve_skills_root, skill_exists
        from skillos.skills.skill_structure import apply_structure_pipeline

        skill_path = _skill_path(finalized["name"], root=resolve_skills_root(tenant))
        if skill_exists(finalized["name"], tenant=tenant):
            old_body = load_skill_raw(finalized["name"], tenant=tenant).get("body", "")
        body_out, heritage_meta = apply_structure_pipeline(
            finalized["name"],
            body_out,
            skill_md_path=skill_path,
            old_body=old_body or None,
            domain_template=domain_tpl,
        )
    except Exception as exc:
        _log.debug("Structure pipeline skipped for '%s': %s", finalized["name"], exc)

    dna_compliance_meta: dict | None = None
    if llm_args and os.environ.get("SKILLOS_SKIP_DNA_FIX", "").strip().lower() not in ("1", "true", "yes"):
        try:
            from skillos.skills.pattern_miner import apply_dna_compliance_fix, check_dna_compliance

            before = check_dna_compliance(body_out)
            if not before.get("all_passed") and before.get("passed", 0) < 5:
                body_out = apply_dna_compliance_fix(body_out, llm_args)
            after = check_dna_compliance(body_out)
            dna_compliance_meta = {
                "before": before.get("score"),
                "after": after.get("score"),
                "passed": after.get("passed"),
                "total": after.get("total"),
                "all_passed": after.get("all_passed"),
            }
        except Exception as exc:
            _log.debug("DNA compliance fix on save skipped for '%s': %s", finalized["name"], exc)

    moe_dict: dict | None = None
    ep_moe: dict | None = None
    boost_rounds: list[dict] = []
    try:
        from skillos.evaluation.moe_boost import evaluate_and_boost
        body_out, moe_report, boost_rounds = evaluate_and_boost(
            body_out, finalized["name"], llm_args,
        )
        moe_dict = moe_report.to_dict()
        ep_moe = {
            "overall_score": moe_report.overall_score,
            "confidence": round(moe_report.confidence, 2),
            "passed": moe_report.passed,
            "dimensions": moe_report.dimensions,
        }
        if boost_rounds:
            ep_moe["boost_rounds"] = boost_rounds
        _log.info(
            "MoE evaluation: %s score=%d confidence=%.2f passed=%s boosts=%d",
            finalized["name"], moe_report.overall_score, moe_report.confidence,
            moe_report.passed, len(boost_rounds),
        )
    except Exception as exc:
        _log.warning("MoE boost skipped for '%s': %s", finalized["name"], exc)
        try:
            from skillos.evaluation import evaluate_skill
            moe_report = evaluate_skill(body_out, finalized["name"], llm_args)
            moe_dict = moe_report.to_dict()
            ep_moe = {
                "overall_score": moe_report.overall_score,
                "confidence": round(moe_report.confidence, 2),
                "passed": moe_report.passed,
                "dimensions": moe_report.dimensions,
            }
        except Exception as exc2:
            _log.warning("MoE evaluation skipped for '%s': %s", finalized["name"], exc2)
            ep_moe = None

    gate_meta: dict = {}
    cold_start_meta: dict = {}
    try:
        from skillos.evaluation.save_gate import apply_save_gate
        from skillos.knowledge.skill_routing import infer_bench_categories

        body_out, gate_meta = apply_save_gate(
            finalized["name"],
            body_out,
            old_body=old_body or None,
            bench_categories=infer_bench_categories(finalized["name"], body_out),
            domain_template=domain_tpl,
        )
    except Exception as exc:
        _log.debug("Save gate skipped for '%s': %s", finalized["name"], exc)

    try:
        from skillos.skills.cold_start import maybe_run_cold_start

        body_out, cold_start_meta = maybe_run_cold_start(
            finalized["name"],
            body_out,
            {"domain_template": domain_tpl, "bench_categories": infer_bench_categories(finalized["name"], body_out)},
            gate_meta=gate_meta or None,
        )
        cs_categories = cold_start_meta.get("bench_categories")
        if cold_start_meta.get("rounds") or cold_start_meta.get("pack_saved"):
            body_out, gate_meta = apply_save_gate(
                finalized["name"],
                body_out,
                old_body=old_body or None,
                bench_categories=cs_categories or infer_bench_categories(finalized["name"], body_out),
                domain_template=domain_tpl,
            )
    except Exception as exc:
        _log.warning("Cold start skipped for '%s': %s", finalized["name"], exc)

    from skillos.knowledge.dna_context import build_skill_dna_meta
    save_meta: dict = {
        "description": finalized["description"],
        "portable_slug": finalized["slug"],
        "draft": False,
        **build_skill_dna_meta(
            finalized["name"],
            body_out,
            domain_template_id=domain_tpl,
            domain_template_ids=domain_tpl_ids,
        ),
    }
    if domain_tpl:
        save_meta["domain_template"] = domain_tpl
    if cold_start_meta.get("bench_categories"):
        save_meta["bench_categories"] = cold_start_meta["bench_categories"]
    elif "bench_categories" not in save_meta:
        from skillos.knowledge.skill_routing import infer_bench_categories
        save_meta["bench_categories"] = infer_bench_categories(finalized["name"], body_out)
    try:
        from skillos.skills.bench_quality import build_bench_quality_meta

        save_meta["bench_quality"] = build_bench_quality_meta(
            finalized["name"],
            body_out,
            meta=save_meta,
            gate_meta=gate_meta or None,
            dna_compliance_meta=dna_compliance_meta,
            moe=ep_moe,
        )
    except Exception as exc:
        _log.debug("bench_quality meta skipped for '%s': %s", finalized["name"], exc)

    # ── Philosophical DNA stability tracking ──
    try:
        moe_score_for_tracking = (ep_moe or {}).get("overall_score", 0)
        from skillos.knowledge.dna_context import track_philosophical_dna_contribution
        dna_tracked = track_philosophical_dna_contribution(
            finalized["name"], body_out, moe_score=moe_score_for_tracking,
        )
        if dna_tracked.get("tracked"):
            _log.info("Philosophical DNA updated: %s", dna_tracked.get("updated"))
    except Exception:
        pass

    for key, val in agent_meta.items():
        if key in save_meta and key in ("dna_lineage", "philosophical_dna", "methodology", "domain"):
            continue
        if val is not None and val != "":
            save_meta[key] = val

    save_skill(
        finalized["name"], body_out, meta=save_meta,
        source=source or name,
        source_type=source_type,
        llm_args=llm_args,
        tenant=tenant,
    )
    raw = load_skill_raw(finalized["name"], tenant=tenant)
    ep = format_epistemic_api_payload(raw.get("meta", {}))
    if save_meta.get("dna_lineage"):
        ep["dna_lineage"] = save_meta["dna_lineage"]
    if heritage_meta.get("heritage_merged"):
        ep["heritage_merged"] = heritage_meta["heritage_merged"]
    if gate_meta:
        ep["save_gate"] = gate_meta
    if cold_start_meta and not cold_start_meta.get("skipped"):
        ep["cold_start"] = cold_start_meta
    if dna_compliance_meta:
        ep["dna_compliance"] = dna_compliance_meta
    ep["portable_slug"] = finalized["slug"]
    ep["install_paths"] = finalized["install_paths"]
    try:
        ep["skill_path"] = str(_skill_path(finalized["name"], root=resolve_skills_root(tenant)))
    except Exception:
        pass

    ctx = team_context or {}
    record_skill_precipitation(
        finalized["name"],
        session_id=ctx.get("session_id", ""),
        channel=ctx.get("channel", ""),
        chat_id=ctx.get("chat_id", ""),
        user_id=ctx.get("user_id", ""),
        source=source or name,
    )
    try:
        from skillos.knowledge.ingest_pipeline import finalize_ingest
        ep = finalize_ingest(
            finalized["body"],
            source or f"skill://{finalized['name']}",
            source_title=finalized["name"],
            skill_name=finalized["name"],
            skill_body=finalized["body"],
            sync_graph=False,
            channel="skill_precipitation",
            payload=ep,
        )
    except Exception as exc:
        _log.warning("Lineage finalize_ingest failed for skill %s: %s", finalized["name"], exc)
        from skillos.knowledge.ingest_pipeline import enrich_with_lineage
        enrich_with_lineage(ep, {"lineage_applied": False, "reason": str(exc)})
    variant_hint = register_precipitation_variant(
        finalized["name"],
        finalized["body"],
        creator=ctx.get("user_id") or ctx.get("chat_id") or "",
        source=source or "",
    )
    if variant_hint:
        ep["variant_hint"] = variant_hint

    try:
        from skillos.skills.dedup import find_similar_skills
        from skillos.skills.skill_store import get_skill_body
        tenant = _tenant_from_context(ctx)
        similar = find_similar_skills(finalized["name"], get_skill_body(body_out), tenant=tenant)
        if similar:
            ep["similar_skills"] = similar
    except Exception:
        pass

    # MoE evaluation payload (evaluate_and_boost runs before save)
    if ep_moe is not None:
        ep["moe_evaluation"] = ep_moe

    # Domain DNA evolution + persistent philosophical stats
    try:
        moe_score = (ep_moe or {}).get("overall_score", 0)
        lineage = save_meta.get("dna_lineage") or {}
        if moe_score >= 70 and lineage:
            from skillos.knowledge.dna_store import record_dna_contribution
            from skillos.skills.domain_templates import evolve_domain_template

            record_dna_contribution(finalized["name"], lineage, moe_score=moe_score)
            primary_domain = next(
                (d.get("id") for d in lineage.get("domain", []) if d.get("primary")),
                None,
            ) or (lineage.get("domain") or [{}])[0].get("id") if lineage.get("domain") else None
            if primary_domain:
                evolved = evolve_domain_template(
                    primary_domain, body_out, moe_score, skill_name=finalized["name"],
                )
                if evolved:
                    try:
                        from skillos.knowledge.dna_store import backfill_skill_lineage
                        skill_path = _skill_path(finalized["name"], tenant=tenant)
                        row = backfill_skill_lineage(skill_path)
                        if row.get("changed"):
                            ep["dna_lineage"] = row["lineage"]
                    except Exception:
                        pass
    except Exception:
        pass

    try:
        from skillos.evaluation.quality import build_quality_payload, evaluate_heuristic
        heuristic = evaluate_heuristic(body_out, finalized["name"])
        ep["quality"] = build_quality_payload(
            skill_name=finalized["name"],
            body=body_out,
            heuristic=heuristic,
            moe=moe_dict,
        )
    except Exception as exc:
        _log.debug("Quality payload skipped: %s", exc)

    try:
        from skillos.skills.pattern_miner import auto_mine_if_needed, ensure_bootstrap_skill_dna
        ensure_bootstrap_skill_dna()
        auto_mine_if_needed(llm_args)
    except Exception as exc:
        _log.debug("Cross-skill DNA mining skipped: %s", exc)

    if save_meta.get("bench_quality"):
        ep["bench_quality"] = save_meta["bench_quality"]

    try:
        from skillos.skills.post_extraction_bench import after_skill_persist

        ep["post_bench"] = after_skill_persist(finalized["name"], llm_args=llm_args)
    except Exception as exc:
        _log.debug("Post-extract bench skipped for '%s': %s", finalized["name"], exc)

    if ctx is not None:
        try:
            from skillos.identity.audit import log_skill_action
            log_skill_action(
                user_id=ctx.get("user_id", ""),
                action="create",
                skill_name=finalized["name"],
                tenant_id=ctx.get("tenant_id", "") or (tenant.tenant_id if tenant else ""),
            )
        except Exception:
            pass

    return ep


def _persist_meta_from_agent(agent) -> dict | None:
    tid = getattr(agent, "_domain_template_id", "") or ""
    tids = getattr(agent, "_domain_template_ids", None) or []
    meta: dict = {}
    if tid:
        meta["domain_template_id"] = tid
    if tids:
        meta["domain_template_ids"] = list(tids)
    return meta or None


def _team_context_from_session(session) -> dict:
    return {
        "session_id": session.id,
        "channel": getattr(session, "channel", ""),
        "chat_id": getattr(session, "chat_id", ""),
        "user_id": getattr(session, "user_id", ""),
        "tenant_id": getattr(session, "tenant_id", ""),
        "org_id": getattr(session, "org_id", ""),
        "dept_id": getattr(session, "dept_id", ""),
    }


def _team_context_from_auth(
    auth: AuthContext | None,
    *,
    tenant_id: str = "",
    org_id: str = "",
    dept_id: str = "",
    user_id: str = "",
    session_id: str = "",
    channel: str = "",
    chat_id: str = "",
) -> dict:
    """Merge JWT auth into team context; auth wins for tenant/user when present."""
    if auth:
        return {
            "session_id": session_id,
            "channel": channel,
            "chat_id": chat_id,
            "user_id": auth.platform_user_id,
            "tenant_id": auth.tenant_id,
            "org_id": auth.org_id or org_id,
            "dept_id": dept_id,
        }
    return {
        "session_id": session_id,
        "channel": channel,
        "chat_id": chat_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "org_id": org_id,
        "dept_id": dept_id,
    }


def _tenant_context_from_auth(auth: AuthContext | None):
    """Set thread-local tenant for quota / path resolution within request."""
    if not auth:
        return None
    from skillos.identity.context import set_tenant_context
    return set_tenant_context(auth.tenant_context())


def _reset_tenant(token) -> None:
    if token is None:
        return
    from skillos.identity.context import reset_tenant_context
    reset_tenant_context(token)


def _dispatch_identity(req: DispatchRequest, auth: AuthContext | None) -> tuple[str, str, str, str]:
    """Resolve tenant/org/user/dept for dispatch; JWT overrides body when authenticated."""
    ctx = _team_context_from_auth(
        auth,
        tenant_id=req.tenant_id,
        org_id=req.org_id,
        dept_id=req.dept_id,
        user_id=req.user_id,
        channel=req.channel,
        chat_id=req.chat_id,
    )
    return ctx["tenant_id"], ctx["org_id"], ctx["user_id"], ctx["dept_id"]


def _skills_list(auth: AuthContext | None = None):
    from skillos.skills.skill_store import list_skills
    tenant = auth.tenant_context() if auth else None
    return list_skills(tenant=tenant)


def _create_mode_skills_list(auth: AuthContext | None = None) -> list[str]:
    """Create mode context: user skills + skill-creator reference (SD-compatible)."""
    from skillos.skills.system_skills import create_mode_skills

    return create_mode_skills(_skills_list(auth))


def _tenant_from_context(ctx: dict):
    from skillos.identity.resolver import tenant_from_context
    return tenant_from_context(ctx)

def _epistemic_reply_suffix(epistemic: dict) -> str:
    if not epistemic or epistemic.get("total_claims", 0) == 0:
        suffix = ""
    else:
        suffix = (
            f"\n\n📊 **认识论状态**：已验证 **{epistemic.get('verified', 0)}** 条 · "
            f"待确认 **{epistemic.get('pending', 0)}** 条"
        )
    hint = epistemic.get("variant_hint") if epistemic else ""
    if hint:
        suffix += f"\n\n{hint}"
    lineage_notice = epistemic.get("lineage_notice") if epistemic else ""
    if lineage_notice:
        suffix += f"\n\n🔗 {lineage_notice}"
    for warning in (epistemic or {}).get("warnings") or []:
        if warning and warning != lineage_notice:
            suffix += f"\n\n{warning}"
    return suffix


def _lineage_reply_suffix(lineage: dict | None) -> str:
    from skillos.knowledge.ingest_pipeline import format_lineage_notice
    notice = format_lineage_notice(lineage)
    if not notice:
        return ""
    return f"\n\n🔗 {notice}"
def _finalize_extraction_response(
    session,
    reply: str,
    agent,
    *,
    doc: dict | None = None,
    ep=None,
    extra: dict | None = None,
) -> dict:
    """Build dispatch JSON and attach clickable [选项] buttons when present."""
    from skillos.skills.extraction_helpers import attach_extraction_actions

    result: dict = {"reply": reply, "session_id": session.id, **(extra or {})}
    if doc:
        result["skill_saved"] = doc["name"]
        result["draft_saved"] = doc["name"]
        if doc.get("slug"):
            result["portable_slug"] = doc["slug"]
        if doc.get("install_paths"):
            result["install_paths"] = doc["install_paths"]
        if ep is not None:
            result["epistemic_summary"] = ep
            result["reply"] = reply + _epistemic_reply_suffix(ep)
            if ep.get("quality"):
                result["quality"] = ep["quality"]
            if ep.get("bench_quality"):
                result["bench_quality"] = ep["bench_quality"]
            if ep.get("moe_evaluation"):
                result["moe_evaluation"] = ep["moe_evaluation"]
            if ep.get("post_bench"):
                result["post_bench"] = ep["post_bench"]
            from skillos.skills.portable_skill import format_install_guide
            slug = doc.get("slug") or ep.get("portable_slug", "")
            path = ep.get("skill_path", "")
            if slug:
                result["reply"] += format_install_guide(doc["name"], slug, path)
        result["export_zip_url"] = f"/api/skills/{doc['name']}/export/zip"
    else:
        result["skill_active"] = agent.is_active
        if agent.draft_name:
            result["draft_preview"] = agent.draft_name
            result["draft_in_session"] = True
            result["draft_saved"] = agent.draft_name
    return attach_extraction_actions(result, result["reply"])


def _run_extraction_dispatch(session, msg: str, auth, llm_args, req: DispatchRequest) -> dict:
    """SD create-mode pipeline: handle() first turn, Socratic dual-output, option buttons."""
    from skillos.skills.intent_router import is_meta_extraction_question

    agent = session.agent
    skills = _create_mode_skills_list(auth)

    if agent.is_active and is_meta_extraction_question(msg):
        reply = agent.reply_to_meta_question()
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        return _finalize_extraction_response(session, reply, agent, extra={"skill_active": True})

    from skillos.skills.agent import Phase

    if (
        agent.is_active
        and agent._phase != Phase.CONFIRMING
        and agent.should_start(msg)
        and not is_meta_extraction_question(msg)
    ):
        session.reset_extraction_agent()
        agent = session.agent
        agent.set_team_context(
            channel=session.channel,
            chat_id=session.chat_id,
            user_id=session.user_id,
            session_id=session.id,
        )

    if not agent.is_active and is_meta_extraction_question(msg):
        reply = (
            "我们还没开始具体的技能沉淀。"
            "你可以直接说想沉淀什么流程，比如「合同审核」或「退款处理」。"
        )
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        return {"reply": reply, "session_id": session.id}

    if not agent.is_active and req.quick_mode and len(msg.strip()) >= 500:
        agent.start(msg, quick_mode=True)

    reply, doc = agent.handle(msg, skills, llm_args)
    session.add_turn("user", msg)
    session.add_turn("assistant", reply)

    if doc:
        try:
            ep = _persist_created_skill(
                doc["name"], doc["content"], llm_args,
                source=f"session:{session.id}", source_type="conversation",
                meta=_persist_meta_from_agent(agent),
                team_context=_team_context_from_session(session),
            )
        except Exception as exc:
            from skillos.billing.usage import QuotaExceededError
            if isinstance(exc, QuotaExceededError):
                raise HTTPException(status_code=402, detail=str(exc)) from exc
            raise
        return _finalize_extraction_response(session, reply, agent, doc=doc, ep=ep)

    return _finalize_extraction_response(session, reply, agent)


@router.post("/dispatch")
async def dispatch_message(
    req: DispatchRequest,
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Handle a chat message — route to skill extraction, URL learning, or conversation."""
    import re

    from skillos.config import get_config
    from skillos.skills.session_manager import get_session_manager

    msg = req.message.strip()
    if not msg:
        return {"reply": "Please enter a message.", "session_id": req.session_id}

    tenant_id, org_id, user_id, dept_id = _dispatch_identity(req, auth)
    _tenant_context_from_auth(auth)

    cfg = get_config()
    llm_args = cfg.to_llm_args()
    from skillos.channels.session_ids import resolve_session_id

    resolved_session = resolve_session_id(
        req.session_id,
        channel=req.channel,
        chat_id=req.chat_id,
        user_id=user_id or req.user_id,
    )
    mgr = get_session_manager()
    session = mgr.get_or_create(
        resolved_session,
        req.mode,
        req.model or cfg.model,
        channel=req.channel,
        chat_id=req.chat_id,
        user_id=user_id or req.user_id,
        tenant_id=tenant_id,
        org_id=org_id,
        dept_id=dept_id,
    )

    agent = session.agent
    from skillos.skills.agent import Phase
    if not agent.is_active and session.history and agent._phase != Phase.DONE:
        agent.restore_from_history(session.history)

    if msg == "__reset__":
        if resolved_session:
            mgr.delete(resolved_session)
        new_session = mgr.get_or_create("", req.mode, req.model or cfg.model)
        return {"reply": "Session reset", "reset": True, "session_id": new_session.id}

    if msg.startswith("__metaskill__") or req.mode == "meta":
        from skillos.skills.agent import Phase
        existing = _skills_list(auth)
        if not agent.is_active or agent._phase != Phase.METASKILL:
            reply = agent.start_metaskill(existing)
            session.add_turn("user", msg)
            session.add_turn("assistant", reply)
            return _finalize_extraction_response(
                session, reply, agent, extra={"skill_active": True, "metaskill_active": True},
            )
        reply, doc = agent.handle(msg, existing, llm_args)
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        if doc:
            from skillos.skills.skill_store import save_skill
            save_skill(doc["name"], doc["content"])
            return _finalize_extraction_response(
                session, reply, agent, doc=doc, extra={"metaskill_active": True},
            )
        return _finalize_extraction_response(
            session, reply, agent, extra={"skill_active": True, "metaskill_active": True},
        )

    # ── Helper: classify content as actionable vs conceptual ──
    def _classify_content(text: str) -> str:
        """Quick LLM classification: actionable (methodology/how-to) or conceptual (reference)."""
        from skillos.knowledge.content_classify import classify_content
        return classify_content(text)

    # ── Helper: fetch URL content ──
    def _fetch_url(url: str) -> str | None:
        from skillos.utils.wechat_fetch import needs_cdp
        if needs_cdp(url):
            from skillos.utils.wechat_fetch import fetch
        else:
            from skillos.utils.web_fetch import fetch
        content = fetch(url)
        return content if content and len(content) > 100 else None

    # ── 1. URL detection ──
    urls = re.findall(r'https?://[^\s]+', msg)
    if urls:
        agent = session.agent
        from skillos.skills.skill_store import save_skill

        for url in urls[:2]:
            content = _fetch_url(url)
            if not content:
                session.add_turn("user", msg)
                session.add_turn("assistant", f"❌ {url[:60]}: 无法获取内容")
                return {"reply": f"❌ {url[:60]}: 无法获取内容", "session_id": session.id}

            # If in extraction conversation → inject as research material
            if agent.is_active:
                reply = agent.inject_external_knowledge(content, url)
                session.add_turn("user", msg)
                session.add_turn("assistant", reply)
                return {"reply": reply, "session_id": session.id, "skill_active": True}

            # Not in extraction → classify and route
            content_type = _classify_content(content)
            if content_type == "actionable":
                from skillos.skills.agent import SkillExtractionAgent
                agent2 = SkillExtractionAgent()
                reply, doc = agent2.learn_from_url(url, content, _skills_list(auth), llm_args)
                session.add_turn("user", msg)
                session.add_turn("assistant", reply)
                result = {"reply": reply, "session_id": session.id}
                if doc:
                    try:
                        ep = _persist_created_skill(
                            doc["name"], doc["content"], llm_args,
                            source=url, source_type="url_content",
                            team_context=_team_context_from_session(session),
                        )
                    except Exception as exc:
                        from skillos.billing.usage import QuotaExceededError
                        if isinstance(exc, QuotaExceededError):
                            raise HTTPException(status_code=402, detail=str(exc)) from exc
                        raise
                    result["skill_saved"] = doc["name"]
                    result["epistemic_summary"] = ep
                    result["reply"] = reply + _epistemic_reply_suffix(ep)
                return result
            else:
                from skillos.knowledge.deep_digest import deep_digest, save_digest
                dd = deep_digest(content, url, llm_args=llm_args)
                if dd.glossary or dd.patterns:
                    save_digest(dd)
                from skillos.knowledge.ingest_pipeline import finalize_ingest
                out_lineage = finalize_ingest(
                    content,
                    url,
                    source_title=dd.title,
                    digest_result=dd if (dd.glossary or dd.patterns or dd.sections) else None,
                    channel="url_conceptual",
                )
                lineage_info = out_lineage.get("lineage")
                reply = f"📦 {url[:60]} → 知识包「{dd.title}」({len(dd.glossary)}术语, {len(dd.patterns)}模式)"
                if out_lineage.get("lineage_notice"):
                    reply += f"\n\n🔗 {out_lineage['lineage_notice']}"
                for warning in out_lineage.get("warnings") or []:
                    if warning != out_lineage.get("lineage_notice"):
                        reply += f"\n\n{warning}"
                session.add_turn("user", msg)
                session.add_turn("assistant", reply)
                out = {"reply": reply, "session_id": session.id}
                if lineage_info:
                    out["lineage"] = lineage_info
                if out_lineage.get("lineage_notice"):
                    out["lineage_notice"] = out_lineage["lineage_notice"]
                if out_lineage.get("warnings"):
                    out["warnings"] = out_lineage["warnings"]
                return out

    # ── Intent routing (Phase 3 — see docs/USER_GUIDE.md) ──
    from skillos.skills.intent_router import (
        DispatchIntent,
        classify_message_intent,
        extract_skill_hint,
        list_pending_for_confirm,
        parse_confirm_claim_selection,
    )

    intent = classify_message_intent(msg, extraction_active=agent.is_active)

    if intent == DispatchIntent.CONFIRM_CLAIMS:
        skill_hint = extract_skill_hint(msg)
        pending = list_pending_for_confirm(skill_hint)
        selected = parse_confirm_claim_selection(msg, pending)
        if not selected:
            reply = (
                "当前没有可晋升的待审声明。"
                if not pending
                else "未能解析要确认的条目。可以说「确认待审」或「确认 1,2」（按待审列表序号）。"
            )
            session.add_turn("user", msg)
            session.add_turn("assistant", reply)
            return {
                "reply": reply,
                "session_id": session.id,
                "intent": "confirm_claims",
                "promoted": 0,
            }

        from skillos.knowledge.epistemic_bridge import confirm_claims_detailed

        result = confirm_claims_detailed(selected, llm_args)
        reply = f"✅ 已晋升 **{result.promoted}** 条声明为已验证知识。"
        if result.synced_skills:
            reply += f"\n已同步技能：{', '.join(result.synced_skills)}"
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        return {
            "reply": reply,
            "session_id": session.id,
            "intent": "confirm_claims",
            "promoted": result.promoted,
            "synced_skills": result.synced_skills,
            "claim_ids": result.claim_ids,
        }

    # ── Cold-start interview: guided playbook creation ──
    if intent == DispatchIntent.PLAYBOOK:
        from skillos.knowledge.playbook import has_playbook, load_playbook

        if "purpose" in msg.lower() or "目标" in msg.lower() or "使命" in msg.lower():
            # Guiding the purpose definition
            try:
                from skillos.llm_client import call
                model = llm_args[2] if len(llm_args) > 2 else ""
                prompt = f"""用户正在定义知识体系的目标(PURPOSE.md)。根据用户输入，生成接下来应该问的引导性问题。

用户输入: {msg}

PURPOSE.md 定义了这个知识体系要解决什么核心问题、为谁服务、关键成功指标是什么。
引导用户说清楚：1) 这个知识体系的读者是谁 2) 它要解决什么核心问题 3) 成功时是什么样子的

自然口语，用中文，问一个开放性问题。"""
                reply = call(prompt, model=model, max_tokens=300, temperature=0.7)
                session.add_turn("user", msg)
                session.add_turn("assistant", reply)
                return {"reply": reply, "session_id": session.id, "mode": "purpose_interview"}
            except Exception:
                _log.debug("Non-critical operation skipped", exc_info=True)

        if has_playbook():
            existing = load_playbook()
            reply = f"📖 当前团队 Playbook:\n\n{existing[:2000]}\n\n---\n你想更新哪些部分？(团队画像 / 文档标准 / 风格偏好 / 术语表 / 工作流)"
            session.add_turn("user", msg)
            session.add_turn("assistant", reply)
            return {"reply": reply, "session_id": session.id}

        # Start cold-start interview
        reply = """## 🏢 冷启动访谈 — 创建团队 Playbook

一个好的 Playbook 让所有技能输出都像同一个团队写的。我会问你几个问题：

**第一步：团队画像**
你们是谁？什么领域？做什么产品？团队规模和构成？

**第二步：文档标准**
你们通常用什么格式写文档？有模板吗？输出要什么格式？

**第三步：风格偏好**
文档风格是怎样的？正式还是轻松？中文还是中英混排？有什么特定的用语习惯？

**第四步：术语表**
团队有没有特定的术语？比如"PR"对你们来说是指 Pull Request 还是 Public Relations？

**第五步：工作流**
你们的工作流是怎样的？从需求到上线经过哪些环节？

先从第一步开始——告诉我你们的团队画像吧。"""
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        return {"reply": reply, "session_id": session.id, "mode": "cold_start_interview"}

    # ── Agent mode — brainstorming dispatcher (not extraction) ──
    if req.mode == "agent" and not agent.is_active:
        from skillos.skills import dispatcher
        from skillos.skills.system_skills import (
            agent_mode_skills,
            methodology_paste_instruction,
        )

        agent_skills = agent_mode_skills(_skills_list(auth))
        system_extra = ""
        if len(msg) > 100 and any(
            kw in msg
            for kw in (
                "步骤", "流程", "方法", "规则", "原则", "指南", "框架", "结构",
                "SKILL", "Skill", "skill", "怎么做", "如何使用",
            )
        ):
            system_extra = methodology_paste_instruction()

        history = session.history if session.history else req.history
        result = dispatcher.dispatch(
            msg,
            history,
            agent_skills,
            model=req.model or cfg.model,
            system_extra=system_extra,
        )
        reply = result.reply or ""
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        out: dict = {
            "reply": reply,
            "mode": "agent",
            "session_id": session.id,
        }
        if result.skill_used:
            out["skill_used"] = result.skill_used
        return out

    # ── Skill extraction — SD create-mode: handle() + Socratic + [选项] buttons ──
    if req.mode == "create" or agent.is_active or intent == DispatchIntent.EXTRACT:
        return _run_extraction_dispatch(session, msg, auth, llm_args, req)

    # ── 3. Default: conversational response ──
    try:
        from skillos.llm_client import call
        history_text = "\n".join(f"{h['role']}: {h['content'][:200]}" for h in req.history[-5:])
        prompt = f"Previous conversation:\n{history_text}\n\nUser: {msg}\n\nRespond helpfully in Chinese (1-3 sentences)."
        reply = call(prompt, max_tokens=200, temperature=0.7)
        session.add_turn("user", msg)
        session.add_turn("assistant", reply)
        return {"reply": reply or "收到，请继续。", "session_id": session.id}
    except Exception as e:
        return {"reply": f"回复生成失败: {e}", "session_id": session.id}


@router.post("/create")
async def create_skill(
    req: CreateSkillRequest,
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Create a new skill from text description."""
    from skillos.config import get_config
    from skillos.skills.agent import SkillExtractionAgent
    from skillos.skills.skill_store import list_skills
    cfg = get_config()
    tenant = auth.tenant_context() if auth else None
    team_ctx = _team_context_from_auth(auth)
    agent = SkillExtractionAgent()
    agent.start(req.text)
    reply, doc = agent.handle(req.text, list_skills(tenant=tenant), cfg.to_llm_args())
    if not doc:
        reply2, doc = agent.handle("请直接生成最终技能文档。", list_skills(tenant=tenant), cfg.to_llm_args())
        reply = reply2
    if doc:
        try:
            ep = _persist_created_skill(
                doc["name"], doc["content"], cfg.to_llm_args(),
                source="api/create", source_type="conversation",
                team_context=team_ctx,
            )
        except Exception as exc:
            from skillos.billing.usage import QuotaExceededError
            if isinstance(exc, QuotaExceededError):
                raise HTTPException(status_code=402, detail=str(exc)) from exc
            raise
        return {
            "reply": reply + _epistemic_reply_suffix(ep),
            "skill_saved": doc["name"],
            "epistemic_summary": ep,
        }
    return {"reply": reply, "active": agent.is_active}


_FINALIZE_MARKER = "生成"


@router.post("/finalize")
async def finalize_extraction(session_id: str = ""):
    """Generate the final SKILL.md from the current extraction conversation.

    Frontend calls this when the user clicks the "生成技能" button.
    Equivalent to the user typing "生成" but as a dedicated API.
    """
    if not session_id:
        return {"reply": "请提供 session_id", "skill_active": False}
    from skillos.config import get_config
    from skillos.skills.session_manager import get_session_manager
    from skillos.skills.skill_store import list_skills, save_skill

    mgr = get_session_manager()
    session = mgr.get(session_id)
    if not session or not session.agent:
        return {"reply": "会话已过期。请重新开始萃取。", "skill_active": False}

    agent = session.agent
    if not agent.is_active:
        return {"reply": "当前没有进行中的萃取。请先描述你的工作流程。", "skill_active": False}
    if len(agent._context) < 2:
        return {"reply": "聊的内容还不够，请再多说一些你的流程细节。", "skill_active": True}

    cfg = get_config()
    llm_args = cfg.to_llm_args()
    reply, doc = agent.handle(_FINALIZE_MARKER, list_skills(), llm_args)
    session.add_turn("user", "[生成技能]")
    session.add_turn("assistant", reply)

    result = {"reply": reply, "session_id": session.id, "skill_active": agent.is_active}
    if doc:
        save_skill(doc["name"], doc["content"])
        result["skill_saved"] = doc["name"]
    return result


@router.get("/status")
async def extraction_status(session_id: str = ""):
    """Check if an extraction is active for a session.

    Returns: {active, skill_name, turn, phase, context_turns, draft_length}
    """
    if not session_id:
        return {"active": False, "reason": "no session_id"}
    from skillos.skills.session_manager import get_session_manager
    mgr = get_session_manager()
    session = mgr.get(session_id)
    if not session or not session.agent:
        return {"active": False, "reason": "session not found"}
    agent = session.agent
    return {
        "active": agent.is_active,
        "skill_name": agent.draft_name or agent.locked_name or "",
        "turn": agent._turn if hasattr(agent, '_turn') else 0,
        "phase": agent._phase.name if hasattr(agent, '_phase') else "unknown",
        "context_turns": len(agent._context) if hasattr(agent, '_context') else 0,
        "draft_length": len(agent._draft_content) if hasattr(agent, '_draft_content') and agent._draft_content else 0,
        "can_resume": bool(agent._context) if hasattr(agent, '_context') else False,
    }


@router.post("/resume")
async def resume_extraction(session_id: str = "", message: str = ""):
    """Resume an incomplete extraction. Re-hydrates state from persisted session.

    If the user closed the window, the draft is still saved. Send a follow-up
    message to continue where they left off.
    """
    if not session_id:
        return {"reply": "请提供 session_id", "resumed": False}
    from skillos.config import get_config
    from skillos.skills.session_manager import get_session_manager
    from skillos.skills.skill_store import list_skills

    mgr = get_session_manager()
    session = mgr.get(session_id)
    if not session:
        return {"reply": "会话已过期（超过30分钟无活动）。请重新开始萃取。", "resumed": False}

    agent = session.agent
    cfg = get_config()
    llm_args = cfg.to_llm_args()

    if not agent.is_active and agent._context:
        # Agent has context but is not active — rehydrate from draft
        agent._phase = type(agent._phase).REFINING if hasattr(agent, '_phase') else agent._phase
        agent._refinement_rounds = max(0, getattr(agent, '_refinement_rounds', 1) - 1)
        agent._turn = len(agent._context)

    name = agent.draft_name or agent.locked_name or "你的技能"
    if not message:
        return {
            "reply": f"欢迎回来！之前我们在聊「**{name}**」，已经积累了 {len(agent._context)} 轮对话。继续说说你的想法吧。",
            "resumed": True,
            "skill_name": name,
            "context_turns": len(agent._context),
        }

    # Process the follow-up message
    reply, doc = agent.handle(message, list_skills(), llm_args)
    session.add_turn("user", message)
    session.add_turn("assistant", reply)
    result = {"reply": reply, "resumed": True, "session_id": session.id, "skill_name": name}
    if doc:
        from skillos.skills.skill_store import save_skill
        save_skill(doc["name"], doc["content"])
        result["skill_saved"] = doc["name"]
    else:
        result["skill_active"] = agent.is_active
    return result


@router.post("/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    session_id: str = Form(""),
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Upload a file (PDF/Word/PPT/Excel/image/txt). Auto-classifies content and routes:
    - actionable (methodology/how-to) → 7-step skill creation pipeline
    - conceptual (reference/theory) → deep_digest knowledge package
    """
    from skillos.config import get_config
    from skillos.skills.session_manager import get_session_manager
    from skillos.utils.file_ingest import convert_to_markdown, get_file_category, is_supported

    cfg = get_config()
    llm_args = cfg.to_llm_args()

    if not file.filename:
        raise HTTPException(400, "No file provided")
    if not is_supported(file.filename):
        ext = Path(file.filename).suffix.lower()
        raise HTTPException(400, f"Unsupported format: {ext}. Supported: PDF, Word, Excel, PPT, images, txt, md, csv, json, html, epub, audio")

    suffix = Path(file.filename).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        md_text, conv_meta = convert_to_markdown(tmp_path, file.filename)

        if md_text.startswith("[不支持的") or md_text.startswith("[文件"):
            return {"error": md_text, "filename": file.filename, "conversion": conv_meta}

        if len(md_text) < 200:
            return {"note": "内容太短，跳过处理", "filename": file.filename,
                    "markdown_length": len(md_text), "conversion": conv_meta}

        # Check if in extraction conversation → inject
        if session_id:
            mgr = get_session_manager()
            session = mgr.get(session_id)
            if session and session.agent.is_active:
                reply = session.agent.inject_external_knowledge(md_text, file.filename)
                return {
                    "filename": file.filename, "file_category": get_file_category(file.filename),
                    "markdown_length": len(md_text), "conversion": conv_meta,
                    "reply": reply, "injected_into_extraction": True,
                }

        # Auto-classify: actionable → skill, conceptual → digest,
        #                template/reference → resource directory
        try:
            from skillos.llm_client import call
            model = llm_args[2] if len(llm_args) > 2 else ""
            classify_prompt = f"""判断以下内容是"actionable"(含可执行步骤/方法论/流程)、"conceptual"(概念/背景/参考)还是"template"(模板/配置/话术/检查清单)?

内容: {md_text[:500]}

只回复一个词: actionable 或 conceptual 或 template"""
            content_type = call(classify_prompt, model=model, max_tokens=10, temperature=0.1).strip().lower()
            is_actionable = "actionable" in content_type
            is_template = "template" in content_type
        except Exception:
            is_actionable = False
            is_template = False

        category = get_file_category(file.filename)

        # Route 0: Template/reference → write directly to skill resource dir
        if is_template and session_id:
            try:
                sm = get_session_manager()
                session = sm.get(session_id)
                if session and session.agent and session.agent._draft_name:
                    from pathlib import Path as _Path
                    from skillos.skills.portable_skill import tool_slug
                    slug = tool_slug(session.agent._draft_name or "skill")
                    skills_root = _Path(__file__).parent.parent.parent / "skills"
                    skill_dir = skills_root / slug
                    from skillos.skills.skill_store import _ensure_standard_dirs
                    _ensure_standard_dirs(skill_dir)
                    from skillos.skills.resource_capture import extract_asset, extract_reference
                    asset_file = extract_asset(md_text, skill_dir, filename=file.filename)
                    if asset_file:
                        reply = f"📎 已保存为资源文件: {asset_file.name}"
                    else:
                        ref_file = extract_reference(md_text, skill_dir, filename=file.filename)
                        reply = f"📎 已保存为参考文档: {ref_file.name}" if ref_file else "📎 文件已接收"
                    import json as _json
                    out = {"reply": reply, "session_id": session_id, "resource_saved": True}
                    session.add_turn("user", f"[上传文件: {file.filename}]")
                    session.add_turn("assistant", reply)
                    return out
            except Exception:
                _log.debug("Template resource routing skipped", exc_info=True)

        if is_actionable:
            from skillos.skills.agent import SkillExtractionAgent
            agent = SkillExtractionAgent()
            reply, doc = agent.learn_from_url(f"file://{file.filename}", md_text, _skills_list(auth), llm_args)
            ep = None
            if doc:
                try:
                    ep = _persist_created_skill(
                        doc["name"], doc["content"], llm_args,
                        source=f"file://{file.filename}", source_type="url_content",
                        team_context=_team_context_from_auth(auth),
                    )
                except Exception as exc:
                    from skillos.billing.usage import QuotaExceededError
                    if isinstance(exc, QuotaExceededError):
                        raise HTTPException(status_code=402, detail=str(exc)) from exc
                    raise
            return {
                "routed_to": "skill", "filename": file.filename, "file_category": category,
                "markdown_length": len(md_text), "conversion": conv_meta,
                "reply": (reply + _epistemic_reply_suffix(ep)) if doc else reply,
                "skill_saved": doc["name"] if doc else None,
                "epistemic_summary": ep if doc else None,
            }
        else:
            from skillos.knowledge.deep_digest import deep_digest, save_digest
            dd = deep_digest(md_text, f"file://{file.filename}", llm_args=llm_args)
            if dd.glossary or dd.patterns:
                save_digest(dd)
            from skillos.knowledge.ingest_pipeline import finalize_ingest
            out = finalize_ingest(
                md_text,
                f"file://{file.filename}",
                source_title=dd.title,
                digest_result=dd if (dd.glossary or dd.patterns or dd.sections) else None,
                channel="file_upload_conceptual",
                payload={
                    "routed_to": "digest", "filename": file.filename, "file_category": category,
                    "markdown_length": len(md_text), "conversion": conv_meta,
                    "title": dd.title, "doc_type": dd.doc_type,
                    "glossary_terms": len(dd.glossary), "patterns": len(dd.patterns),
                    "sections": len(dd.sections),
                },
            )
            return out
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            _log.debug("Non-critical operation skipped", exc_info=True)

