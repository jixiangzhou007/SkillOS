"""Skill CRUD, extraction, and execution endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from skillos.api._skills_shared import (
    _reset_tenant,
    _tenant_context_from_auth,
)
from skillos.identity.middleware import AuthContext, get_optional_auth, require_auth

router = APIRouter()
_log = logging.getLogger(__name__)

# ── Include extraction sub-router ────────────────────────────
from skillos.api.skills_extract import router as extract_router  # noqa: E402

router.include_router(extract_router)

# Re-export extraction helpers for backward compatibility with tests
from skillos.api.skills_extract import (  # noqa: E402, F401
    _create_mode_skills_list,
    _finalize_extraction_response,
    _persist_created_skill,
    _run_extraction_dispatch,
)

# ── Request/Response models ─────────────────────────────────

class ConfirmClaimsRequest(BaseModel):
    claim_ids: list[str] = []
    confirm_all: bool = False

class CopyToOrgRequest(BaseModel):
    org_id: str
    dept_id: str = ""
    new_name: str = ""


class MetaSkillRunRequest(BaseModel):
    user_input: str = ""
    dry_run: bool = True

class SkillResponse(BaseModel):
    name: str
    version: int = 1
    runs: int = 0
    avg_score: float = 0.0
    failure_rate: float = 0.0
    kb_items: int = 0

# ── Shared impl ─────────────────────────────────────────────

def _kb_items_count(name: str) -> int:
    try:
        from skillos.knowledge.skill_kb import load_kb
        return load_kb(name).total_items
    except Exception:
        return 0

def _list_skills_impl(*, tenant=None, q: str = "", dept_id: str = "") -> list[SkillResponse]:
    """List all skills with trace stats from the evolver."""
    from skillos.skills import skill_store

    result: list[SkillResponse] = []
    meta_by_slug: dict[str, dict] = {}
    if tenant and tenant.tenant_id.startswith("org:"):
        from skillos.identity.models import list_skill_metadata
        for row in list_skill_metadata(tenant.tenant_id):
            meta_by_slug[row["skill_slug"]] = row

    for name in skill_store.list_skills(tenant=tenant):
        if q and q.lower() not in name.lower():
            continue
        if dept_id and tenant and tenant.tenant_id.startswith("org:"):
            from skillos.skills.skill_store import _slugify
            slug = _slugify(name)
            row = meta_by_slug.get(slug)
            skill_dept = (row or {}).get("dept_id", "")
            if skill_dept != dept_id:
                continue
        stats = {"version": 1, "runs": 0, "avg_score": 0.0, "failure_rate": 0.0}
        try:
            from skillos.evolution.evolver import get_skill_stats
            raw = get_skill_stats(name)
            stats = {
                "version": raw.get("version", 1),
                "runs": raw.get("total", 0),
                "avg_score": raw.get("avg_score", 0.0),
                "failure_rate": raw.get("failure_rate", 0.0),
            }
        except Exception:
            pass
        result.append(SkillResponse(name=name, kb_items=_kb_items_count(name), **stats))
    return result

# ── Endpoints ───────────────────────────────────────────────

@router.get("/domain-templates")
async def list_domain_skill_templates():
    """List domain skeleton templates for fast skill extraction."""
    from skillos.knowledge.dna_store import get_template_record, list_domain_template_versions
    from skillos.skills.domain_templates import list_domain_templates

    versions = list_domain_template_versions()
    templates = []
    for t in list_domain_templates():
        tid = t["template_id"]
        rec = get_template_record(tid)
        templates.append({
            **t,
            "version": versions.get(tid, "1.0.0"),
            "derived_from_skills": rec.get("derived_from_skills", 0),
        })
    return {"templates": templates}


@router.get("/dna/stale-queue")
async def get_dna_stale_queue(refresh: bool = False):
    """Skills whose dna_lineage domain versions lag evolved template semver."""
    from skillos.knowledge.dna_evolution import load_stale_queue, refresh_stale_queue

    if refresh:
        payload = refresh_stale_queue()
    else:
        payload = load_stale_queue()
        if not payload.get("items"):
            payload = refresh_stale_queue()
    return {
        "count": len(payload.get("items", [])),
        "updated_at": payload.get("updated_at", ""),
        "items": payload.get("items", []),
    }


@router.post("/dna/stale-queue/process")
async def process_dna_stale_queue(dry_run: bool = False, limit: int = 50):
    """Re-backfill stale dna_lineage entries to current template versions."""
    from skillos.knowledge.dna_evolution import process_stale_queue

    return process_stale_queue(dry_run=dry_run, limit=limit)


@router.post("/{name}/refresh-dna-lineage")
async def refresh_skill_dna_lineage(name: str, auth: AuthContext | None = Depends(get_optional_auth)):
    """Refresh one skill's dna_lineage to current template semver."""
    from skillos.knowledge.dna_evolution import relink_skill_lineage
    from skillos.skills.skill_store import _skill_path, resolve_skills_root

    tenant = auth.tenant_context() if auth else None
    path = _skill_path(name, root=resolve_skills_root(tenant=tenant))
    if not path.exists():
        raise HTTPException(404, f"Skill not found: {name}")
    result = relink_skill_lineage(path)
    return {
        "skill": name,
        "changed": result.get("changed"),
        "was_stale": result.get("was_stale"),
        "still_stale": result.get("still_stale"),
        "lineage": result.get("lineage"),
    }


@router.get("/{name}/dna-lineage")
async def get_skill_dna_lineage(name: str, auth: AuthContext | None = Depends(get_optional_auth)):
    """Return DNA lineage (philosophical + domain inheritance) for a skill."""
    tenant = auth.tenant_context() if auth else None
    try:
        from skillos.knowledge.dna_context import build_dna_lineage
        from skillos.knowledge.dna_store import load_philosophical_stats, parse_lineage_from_meta
        from skillos.skills.skill_store import load_skill_raw

        raw = load_skill_raw(name, tenant=tenant)
        meta = raw.get("meta", {})
        lineage = parse_lineage_from_meta(meta)
        if not lineage:
            lineage = build_dna_lineage(name, raw.get("body", ""))

        from skillos.knowledge.dna_semver import is_stale_version
        from skillos.knowledge.dna_store import get_template_version
        from skillos.skills.domain_templates import get_template

        domain_rows = []
        for entry in lineage.get("domain") or []:
            tid = entry.get("id") or ""
            current_ver = get_template_version(tid) if tid else ""
            tmpl = get_template(tid) if tid else None
            row = dict(entry)
            row["current_version"] = current_ver
            row["title"] = tmpl.title if tmpl else tid
            row["is_stale"] = (
                bool(tid)
                and is_stale_version(str(entry.get("version") or "1.0.0"), current_ver)
            )
            domain_rows.append(row)

        lineage_out = {**lineage, "domain": domain_rows}

        return {
            "skill": name,
            "dna_lineage": lineage_out,
            "meta": {
                k: meta[k]
                for k in (
                    "domain", "domain_label", "philosophical_dna",
                    "philosophical_dna_label", "methodology", "bench_categories",
                    "bench_quality", "domain_template",
                )
                if k in meta
            },
            "philosophical_stats": load_philosophical_stats().get("methods", {}),
        }
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")


@router.get("/", response_model=list[SkillResponse])
async def list_skills(
    q: str = "",
    dept_id: str = "",
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """List all skills; scoped to JWT workspace when authenticated."""
    tenant = auth.tenant_context() if auth else None
    return _list_skills_impl(tenant=tenant, q=q, dept_id=dept_id)


@router.get("/{name}")
async def get_skill(name: str, auth: AuthContext | None = Depends(get_optional_auth)):
    """Get a skill by name (tenant-scoped when authenticated)."""
    tenant = auth.tenant_context() if auth else None
    try:
        from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload
        from skillos.skills.skill_store import get_skill_body, load_skill, load_skill_raw
        doc = load_skill(name, tenant=tenant)
        body = get_skill_body(doc)
        raw = load_skill_raw(name, tenant=tenant)
        meta = raw.get("meta", {})
        skill_type = meta.get("type", "skill")
        is_metaskill = skill_type == "metaskill" or "type: metaskill" in (doc or "")[:200]
        stats = {"version": meta.get("version", 1), "runs": 0, "avg_score": 0.0}
        try:
            from skillos.evolution.evolver import get_skill_stats
            raw_stats = get_skill_stats(name)
            stats = {
                "version": raw_stats.get("version", meta.get("version", 1)),
                "runs": raw_stats.get("total", 0),
                "avg_score": raw_stats.get("avg_score", 0.0),
            }
        except Exception:
            pass
        from skillos.skills.skill_store import get_skill_versions
        versions = get_skill_versions(name, tenant=tenant)
        return {
            "name": name,
            "content": doc,
            "body": body,
            "type": skill_type,
            "is_metaskill": is_metaskill,
            "version": stats["version"],
            "runs": stats["runs"],
            "avg_score": stats["avg_score"],
            "kb_items": _kb_items_count(name),
            "versions": versions,
            "epistemic_summary": format_epistemic_api_payload(meta),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")


@router.delete("/{name}")
async def delete_skill_api(name: str, auth: AuthContext = Depends(require_auth)):
    """Delete a skill from the current tenant workspace."""
    from skillos.skills.skill_store import delete_skill

    tenant = auth.tenant_context()
    if not delete_skill(name, tenant=tenant):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"deleted": True, "name": name}


@router.get("/{name}/kb")
async def get_skill_kb(name: str, auth: AuthContext | None = Depends(get_optional_auth)):
    """Skill knowledge base summary (facts, templates, heuristics counts)."""
    tenant = auth.tenant_context() if auth else None
    from skillos.skills.skill_store import skill_exists
    if not skill_exists(name, tenant=tenant):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    try:
        from skillos.knowledge.skill_kb import load_kb
        kb = load_kb(name)
    except Exception:
        return {"facts": 0, "cases": 0, "heuristics": 0, "constraints": 0, "templates": 0, "total": 0}
    return {
        "facts": len(kb.facts),
        "cases": len(kb.cases),
        "heuristics": len(kb.heuristics),
        "constraints": len(kb.constraints),
        "templates": len(kb.templates),
        "total": kb.total_items,
    }


class CompareTemplateRequest(BaseModel):
    input: str = ""


@router.post("/{name}/compare-template")
async def compare_template_api(
    name: str,
    req: CompareTemplateRequest,
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Compare input document against skill KB templates."""
    from skillos.config import get_config
    from skillos.knowledge.skill_kb import compare_against_templates
    from skillos.skills.skill_store import skill_exists

    tenant = auth.tenant_context() if auth else None
    if not skill_exists(name, tenant=tenant):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="input required")
    cfg = get_config()
    return compare_against_templates(name, req.input.strip(), cfg.to_llm_args())


class ImportAdaptRequest(BaseModel):
    zip: str = ""
    model: str = ""


@router.post("/import-and-adapt")
async def import_and_adapt(req: ImportAdaptRequest, auth: AuthContext = Depends(require_auth)):
    """Import skills from a base64-encoded zip (SKILL.md files)."""
    import base64
    import io
    import zipfile

    if not req.zip:
        raise HTTPException(status_code=400, detail="zip payload required")
    tenant = auth.tenant_context()
    try:
        raw = base64.b64decode(req.zip)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid base64 zip")

    imported: list[str] = []
    from skillos.skills.skill_store import save_skill

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            fname = info.filename.replace("\\", "/")
            if not (fname.endswith("SKILL.md") or fname.endswith(".md")):
                continue
            try:
                content = zf.read(info).decode("utf-8", errors="replace")
            except Exception:
                continue
            if len(content.strip()) < 20:
                continue
            base = fname.split("/")[-1].replace(".md", "")
            skill_name = base if base != "SKILL" else fname.split("/")[-2] if "/" in fname else base
            save_skill(skill_name, content, epistemic=False, tenant=tenant)
            imported.append(skill_name)

    if not imported:
        return {"reply": "未在 zip 中找到有效的 SKILL.md", "imported": 0, "skills": []}
    return {
        "reply": f"已导入 {len(imported)} 个技能：" + "、".join(imported[:5]),
        "imported": len(imported),
        "skills": imported,
    }


@router.get("/{name}/epistemic/pending")
async def list_epistemic_pending(name: str, auth: AuthContext | None = Depends(get_optional_auth)):
    """List pending Experience/Evidence claims for a skill (Sprint 4 UI)."""
    from skillos.knowledge.epistemic_bridge import format_epistemic_api_payload, list_pending_claims_detail
    from skillos.skills.skill_store import load_skill_raw

    tenant = auth.tenant_context() if auth else None
    try:
        raw = load_skill_raw(name, tenant=tenant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    pending = list_pending_claims_detail(name)
    return {
        "skill": name,
        "epistemic_summary": format_epistemic_api_payload(raw.get("meta", {})),
        "pending_claims": pending,
    }


@router.post("/{name}/epistemic/confirm")
async def confirm_epistemic_pending(
    name: str,
    req: ConfirmClaimsRequest,
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Promote selected pending claims to Knowledge."""
    from skillos.config import get_config
    from skillos.knowledge.epistemic_bridge import confirm_claims_detailed, list_pending_claims_detail
    from skillos.skills.intent_router import list_pending_for_confirm

    claim_ids = req.claim_ids
    if req.confirm_all:
        claim_ids = list_pending_for_confirm(name)
    if not claim_ids:
        raise HTTPException(status_code=400, detail="No claims selected")

    cfg = get_config()
    result = confirm_claims_detailed(claim_ids, cfg.to_llm_args())
    remaining = list_pending_claims_detail(name)
    return {
        "skill": name,
        "promoted": result.promoted,
        "claim_ids": result.claim_ids,
        "synced_skills": result.synced_skills,
        "remaining_pending": len(remaining),
    }


@router.get("/{name}/similar")
async def similar_skills(name: str, auth: AuthContext | None = Depends(get_optional_auth)):
    """Dedup hints — similar skills in current tenant."""
    from skillos.skills.dedup import find_similar_skills
    from skillos.skills.skill_store import get_skill_body, load_skill_raw

    tenant = auth.tenant_context() if auth else None
    try:
        raw = load_skill_raw(name, tenant=tenant)
        body = raw.get("body") or get_skill_body(raw.get("content", ""))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    similar = find_similar_skills(name, body, tenant=tenant)
    return {"skill": name, "similar": similar}


@router.get("/{name}/metaskill")
async def get_metaskill_pipeline(name: str, auth: AuthContext = Depends(require_auth)):
    """Parse MetaSkill pipeline structure for portal visualization."""
    from skillos.skills.metaskill import META_MARKER, parse_metaskill
    from skillos.skills.skill_store import load_skill_raw

    tenant = auth.tenant_context()
    try:
        raw = load_skill_raw(name, tenant=tenant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    content = raw.get("body") or ""
    meta = raw.get("meta") or {}
    if meta.get("type") != "metaskill" and META_MARKER not in content[:200]:
        raise HTTPException(status_code=400, detail="Not a MetaSkill")

    ms = parse_metaskill(content)
    if not ms:
        raise HTTPException(status_code=400, detail="Failed to parse MetaSkill pipeline")

    valid, msg = ms.validate()
    from skillos.skills.metaskill import pipeline_to_mermaid

    return {
        "skill": name,
        "name": ms.name,
        "goal": ms.goal,
        "risk_level": ms.risk_level,
        "valid": valid,
        "validation_message": msg,
        "mermaid": pipeline_to_mermaid(ms.steps),
        "steps": [
            {
                "name": s.name,
                "skill_name": s.skill_name,
                "depends_on": s.depends_on,
                "output_key": s.output_key,
            }
            for s in ms.steps
        ],
    }


@router.post("/{name}/metaskill/run")
async def run_metaskill_pipeline(
    name: str,
    req: MetaSkillRunRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Execute a MetaSkill pipeline (dry_run loads skills without LLM)."""
    from skillos.skills.metaskill import META_MARKER, parse_metaskill, run_pipeline
    from skillos.skills.skill_store import load_skill_raw

    token = _tenant_context_from_auth(auth)
    try:
        raw = load_skill_raw(name, tenant=auth.tenant_context())
    except FileNotFoundError:
        _reset_tenant(token)
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")

    content = raw.get("body") or ""
    meta = raw.get("meta") or {}
    if meta.get("type") != "metaskill" and META_MARKER not in content[:200]:
        _reset_tenant(token)
        raise HTTPException(status_code=400, detail="Not a MetaSkill")

    ms = parse_metaskill(content)
    if not ms:
        _reset_tenant(token)
        raise HTTPException(status_code=400, detail="Failed to parse MetaSkill pipeline")

    llm_args = None
    if not req.dry_run:
        from skillos.config import get_config
        llm_args = get_config().to_llm_args()

    try:
        result = run_pipeline(
            ms,
            context={"user_input": req.user_input},
            llm_args=llm_args,
        )
    finally:
        _reset_tenant(token)

    return {
        "skill": name,
        "success": result.success,
        "dry_run": req.dry_run,
        "outputs": result.outputs,
        "errors": result.errors,
        "trace": result.trace,
    }


@router.post("/{name}/copy-to-org")
async def copy_skill_to_org_api(
    name: str,
    req: CopyToOrgRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Copy a personal skill into an organization workspace (draft)."""
    from skillos.identity.context import TenantContext
    from skillos.identity.models import get_member_role
    from skillos.skills.copy import SkillCopyError, copy_skill_to_org

    oid = req.org_id if req.org_id.startswith("org_") else f"org_{req.org_id}"
    if not get_member_role(auth.platform_user_id, oid):
        raise HTTPException(status_code=403, detail="Not an organization member")

    personal = TenantContext.personal(auth.platform_user_id)
    try:
        saved = copy_skill_to_org(
            name,
            personal_tenant=personal,
            org_id=oid,
            dept_id=req.dept_id,
            creator_user_id=auth.platform_user_id,
            new_name=req.new_name or None,
        )
    except SkillCopyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        from skillos.analytics.funnel import track_funnel
        track_funnel("copy_to_org", tenant_id=f"org:{oid}", user_id=auth.platform_user_id, detail=saved)
    except Exception:
        pass
    return {"ok": True, "skill_saved": saved, "org_id": oid, "approval_status": "draft"}


@router.post("/{name}/run")
async def run_skill(name: str, task: dict):
    """Execute a skill with a given task and record the trace for evolution."""
    from skillos.evolution.evolver import judge_execution, record_trace
    from skillos.skills.agent_factory import create_agent, run_agent
    from skillos.skills.skill_store import load_skill_raw

    task_text = task.get("task", "")
    if not task_text:
        raise HTTPException(400, "Missing 'task' field")

    # Load skill
    try:
        skill_raw = load_skill_raw(name)
        skill_doc = skill_raw["body"]
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")

    # Execute
    agent = create_agent(skill_doc, task_text)
    result = run_agent(agent, task_text)

    # Record trace for evolution
    score = 0
    feedback = ""
    try:
        score_result = judge_execution(task_text, result, skill_doc)
        if isinstance(score_result, dict):
            score = score_result.get("score", 3)
            feedback = score_result.get("feedback", "")
        else:
            score = int(score_result) if score_result else 3
    except Exception:
        score = 3
        feedback = ""

    try:
        record_trace(name, task_text, result, score, feedback)
    except Exception:
        _log.debug("Non-critical operation skipped", exc_info=True)

    return {
        "skill": name,
        "task": task_text[:200],
        "result": result[:2000],
        "score": score,
        "feedback": feedback[:500],
    }


@router.get("/{name}/export")
async def export_skill(
    name: str,
    format: str = "markdown",
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """Export a skill in various formats.

    - markdown: Raw SKILL.md (AgentSkills.io compatible)
    - universal: JSON with full metadata (for import into other systems)
    """
    from skillos.skills.skill_store import get_skill_versions, load_skill_raw

    tenant = auth.tenant_context() if auth else None
    try:
        skill = load_skill_raw(name, tenant=tenant)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")

    meta = skill["meta"]
    body = skill["body"]

    if format == "universal":
        versions = get_skill_versions(name)
        return {
            "format": "universal",
            "skill": {
                "name": name,
                "version": meta.get("version", 1),
                "created_at": meta.get("created_at", ""),
                "updated_at": meta.get("updated_at", ""),
                "type": meta.get("type", "skill"),
                "source_url": meta.get("source_url", ""),
                "content": body,
                "available_versions": versions,
            }
        }
    else:
        # Raw markdown — portable install bundle (AgentSkills.io / Cursor / Claude Code)
        from skillos.skills.portable_skill import build_description, tool_slug
        from skillos.skills.skill_store import _compose

        slug = meta.get("portable_slug") or tool_slug(name, body)
        description = meta.get("description") or build_description(name, body)
        portable_meta = {
            "name": slug,
            "description": description,
        }
        portable_content = _compose(portable_meta, body)
        return {
            "format": "markdown",
            "name": name,
            "portable_slug": slug,
            "description": description,
            "content": body,
            "portable_content": portable_content,
            "meta": meta,
        }


@router.get("/{name}/export/zip")
async def export_skill_zip(
    name: str,
    auth: AuthContext | None = Depends(get_optional_auth),
):
    """One-click install zip: {slug}/SKILL.md + README for Cursor / Claude / Trae."""
    from skillos.skills.portable_export import build_install_zip

    tenant = auth.tenant_context() if auth else None
    try:
        data, filename = build_install_zip(name, tenant=tenant)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}") from None
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{name}/security")
async def scan_skill(name: str):
    """Scan a skill for security issues."""
    try:
        from skillos.api.middleware import scan_skill_file
        findings = scan_skill_file(name)
        return {"skill": name, "findings": findings, "safe": len(findings) == 0}
    except Exception:
        return {"skill": name, "error": "Scan failed", "safe": True}


@router.get("/{name}/traces")
async def get_traces(name: str):
    """Get execution traces for a skill."""
    try:
        from skillos.evolution.evolver import get_recent_traces
        return get_recent_traces(name, 20)
    except Exception:
        return []


@router.get("/{name}/decisions")
async def get_decisions(name: str):
    """Get decision history (WHY chain) for a skill."""
    try:
        from skillos.evolution.skillhone import load_decisions
        records = load_decisions(name, 30)
        return {"skill": name, "decisions": records, "count": len(records)}
    except Exception:
        return {"skill": name, "decisions": [], "count": 0}


# ── Skill DNA ───────────────────────────────────────────────

@router.get("/dna/view")
async def view_skill_dna():
    """View the current Skill DNA — principles distilled from all skills."""
    try:
        from skillos.skills.pattern_miner import get_skill_dna
        dna = get_skill_dna()
        if not dna or not dna.get("dna"):
            return {"dna": None, "message": "尚未生成 Skill DNA。创建更多技能后会自动提炼。"}
        return {
            "dna": {
                "principles": dna.get("dna", []),
                "archetypes": dna.get("archetypes", []),
                "anti_patterns": dna.get("anti_patterns", []),
                "templates": dna.get("templates", []),
                "generated_at": dna.get("generated_at", 0),
            }
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/dna/remine")
async def remine_dna():
    """Re-run cross-skill pattern mining to update the DNA."""
    try:
        from skillos.config import get_config
        from skillos.skills.pattern_miner import run_cross_skill_optimization
        cfg = get_config()
        result = run_cross_skill_optimization(cfg.to_llm_args())
        return {"success": True, "dna": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/dna/stability")
async def view_dna_stability():
    """View philosophical DNA stability stats — how many skills contributed to each methodology."""
    try:
        from skillos.knowledge.dna_context import get_dna_stability_report
        report = get_dna_stability_report()
        return {"dna_stability": report}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{name}/dna-check")
async def check_skill_dna(name: str):
    """Check a skill against DNA compliance principles."""
    try:
        from skillos.skills.pattern_miner import check_dna_compliance
        from skillos.skills.skill_store import get_skill_body, load_skill
        doc = load_skill(name)
        body = get_skill_body(doc)
        result = check_dna_compliance(body)
        return {"skill": name, "dna_compliance": result}
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")
    except Exception as e:
        return {"error": str(e)}


# ── MoE Evaluation ───────────────────────────────────────────

@router.get("/{name}/evaluate")
async def evaluate_skill_moe(
    name: str,
    cross_model: str = "",
    fast_model: str = "",
):
    """Run MoE multi-expert evaluation with optional cross-model validation.

    - 6 independent expert judges score different dimensions
    - Optional cross_model: re-run on a different model for validation
    - Returns structured report with per-dimension breakdown and confidence

    Example: GET /api/skills/MySkill/evaluate?cross_model=deepseek-v4-flash
    """
    try:
        from skillos.config import get_config
        from skillos.evaluation import evaluate_skill
        from skillos.skills.skill_store import get_skill_body, load_skill

        doc = load_skill(name)
        body = get_skill_body(doc)
        cfg = get_config()
        llm_args = cfg.to_llm_args()

        report = evaluate_skill(
            body, name, llm_args,
            cross_model=cross_model or fast_model,
        )
        report_dict = report.to_dict()
        moe_summary = {
            "overall_score": report.overall_score,
            "passed": report.passed,
            "confidence": round(report.confidence, 2),
            "dimensions": report.dimensions,
        }
        from skillos.evaluation.quality import build_quality_payload, evaluate_heuristic
        report_dict["quality"] = build_quality_payload(
            skill_name=name,
            body=body,
            heuristic=evaluate_heuristic(body, name),
            moe=moe_summary,
        )
        return report_dict
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")
    except Exception as e:
        return {"error": str(e)}


@router.get("/{name}/evaluate/markdown")
async def evaluate_skill_moe_markdown(name: str, cross_model: str = ""):
    """MoE evaluation report in markdown format."""
    try:
        from skillos.config import get_config
        from skillos.evaluation import evaluate_skill
        from skillos.skills.skill_store import get_skill_body, load_skill

        doc = load_skill(name)
        body = get_skill_body(doc)
        cfg = get_config()
        llm_args = cfg.to_llm_args()

        report = evaluate_skill(body, name, llm_args, cross_model=cross_model)
        return {"skill": name, "markdown": report.to_markdown(), "report": report.to_dict()}
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")
    except Exception as e:
        return {"error": str(e)}


# ── Skill Variants (多态) ────────────────────────────────────

@router.get("/{name}/variants")
async def list_variants(name: str):
    """List all variants of a skill archetype."""
    try:
        from skillos.skills.variants import compare_variants, format_variant_comparison
        comparison = compare_variants(name)
        formatted = format_variant_comparison(name)
        return {"skill": name, "comparison": comparison, "formatted": formatted}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{name}/variants")
async def register_variant(name: str, req: dict | None = None):
    if req is None: req = {}
    """Register a new variant of a skill archetype."""
    try:
        from skillos.skills.variants import VariantRegistry
        reg = VariantRegistry()
        variant = reg.register_variant(
            archetype=name,
            creator=req.get("creator", ""),
            content=req.get("content", ""),
            creator_role=req.get("creator_role", ""),
            source=req.get("source", ""),
            confidence=req.get("confidence", 0.5),
            epistemic_level=req.get("epistemic_level", "experience"),
        )
        return {"registered": variant.variant_id, "archetype": name}
    except Exception as e:
        return {"error": str(e)}


@router.get("/variants/detect")
async def detect_variants():
    """Auto-detect potential variant families across all skills."""
    try:
        from skillos.skills.variants import auto_detect_variants
        groups = auto_detect_variants()
        return {"groups": groups, "count": len(groups)}
    except Exception as e:
        return {"error": str(e)}
