"""Official SkillsBench API — plans and results (eval runs via CLI/CI)."""


from fastapi import APIRouter, Depends, HTTPException

from skillos.identity.middleware import AuthContext, require_auth
from skillos.benchmark_local import (
    latest_bench_regression,
    latest_post_extract_regression,
    local_bench_summary,
    reference_bench_dashboard,
    run_quick8_for_skill,
)
from skillos.official_skillsbench.service import (
    export_skill_to_dir,
    latest_for_skill,
    latest_official_results,
    list_presets,
    plan_for_skill,
    trigger_official_ci,
)

router = APIRouter()


@router.get("/presets")
async def get_presets():
    return {"presets": list_presets()}


@router.get("/latest")
async def get_latest(limit: int = 5):
    return latest_official_results(limit=min(limit, 20))


@router.get("/summary")
async def get_bench_dashboard():
    """Reference skills quick8 + latest official CI snapshot."""
    return reference_bench_dashboard()


@router.get("/regression/latest")
async def get_latest_regression():
    """Latest local Quick8 + domain smoke regression snapshot."""
    data = latest_bench_regression()
    if not data:
        raise HTTPException(404, "No bench regression snapshot found")
    return data


@router.get("/regression/post-extract/latest")
async def get_latest_post_extract_regression():
    """Latest regression triggered after reference-skill extraction save."""
    data = latest_post_extract_regression()
    if not data:
        raise HTTPException(404, "No post-extract regression snapshot found")
    return data


@router.post("/regression/run")
async def trigger_regression(background: bool = True, auth: AuthContext = Depends(require_auth)):
    """Run local Quick8 + smoke regression (reference skills gate)."""
    import threading

    from skillos.skills.post_extraction_bench import _regression_enabled, run_regression_sync

    if not _regression_enabled():
        raise HTTPException(400, "DEEPSEEK_API_KEY required (set SKILLOS_SKIP_BENCH_REGRESSION=1 to disable)")
    if background:
        threading.Thread(
            target=run_regression_sync,
            kwargs={},
            daemon=True,
        ).start()
        return {"scheduled": True, "message": "Regression running in background; poll /regression/latest"}
    result = run_regression_sync()
    return result


@router.get("/skills/{name}/smoke")
async def get_skill_domain_smoke(name: str):
    """Domain smoke suite for a skill (save-gate tasks, no LLM)."""
    from skillos.evaluation.save_gate import run_domain_smoke_suite
    from skillos.skills.skill_store import load_skill_raw

    try:
        raw = load_skill_raw(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}") from None
    meta = raw.get("meta", {})
    body = raw.get("body", "")
    suite = run_domain_smoke_suite(
        name,
        body,
        bench_categories=meta.get("bench_categories"),
        domain_template=meta.get("domain_template") or meta.get("domain_template_id"),
    )
    min_score = min((r["with_score"] for r in suite), default=0)
    return {
        "skill": name,
        "domain_template": meta.get("domain_template"),
        "suite": suite,
        "min_with_score": min_score,
        "smoke_pass": min_score >= 80,
    }


@router.get("/skills/{name}")
async def get_skill_bench_summary(name: str):
    try:
        return latest_for_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")


@router.get("/skills/{name}/plan")
async def get_skill_bench_plan(name: str):
    try:
        return plan_for_skill(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")


@router.post("/skills/{name}/export")
async def export_skill_for_bench(name: str):
    try:
        return export_skill_to_dir(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")


@router.get("/skills/{name}/local")
async def get_skill_local_bench(name: str):
    """Latest local quick8 / structural benchmark for a skill."""
    from skillos.official_skillsbench.export import SKILLS_ROOT

    if not (SKILLS_ROOT / name / "SKILL.md").exists():
        raise HTTPException(404, f"Skill not found: {name}")
    return local_bench_summary(name)


@router.post("/skills/{name}/quick8")
async def run_skill_quick8(name: str, domain_only: bool = False):
    """Run local quick8 for one skill (uses LLM + cache). domain_only=仅域内可注入题."""
    try:
        return run_quick8_for_skill(name, domain_only=domain_only)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Quick8 failed: {exc}") from exc


@router.post("/skills/{name}/trigger-ci")
async def trigger_skill_official_ci(name: str, preset: str = "", auth: AuthContext = Depends(require_auth)):
    """Request GitHub Actions official bench run (needs GITHUB_TOKEN + GITHUB_REPOSITORY)."""
    try:
        return trigger_official_ci(name, preset=preset or None)
    except FileNotFoundError:
        raise HTTPException(404, f"Skill not found: {name}")
