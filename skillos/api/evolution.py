"""Skill evolution endpoints — optimization, MoE routing, decision history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from skillos.identity.middleware import AuthContext, require_auth

router = APIRouter()


def _tenant_token(auth: AuthContext):
    from skillos.api.skills import _reset_tenant, _tenant_context_from_auth

    return _tenant_context_from_auth(auth), _reset_tenant


def _load_skill_body(name: str, auth: AuthContext) -> str:
    from skillos.skills.skill_store import load_skill_raw

    raw = load_skill_raw(name, tenant=auth.tenant_context())
    return raw["body"]


@router.post("/{name}/optimize")
async def optimize_skill(name: str, feedback: dict = {}, auth: AuthContext = Depends(require_auth)):
    """Run an optimization round on a skill using the MoE system."""
    token, reset = _tenant_token(auth)
    try:
        from skillos.config import get_config
        from skillos.evolution.skillopt import compute_skill_state, evolve_with_moe, route

        cfg = get_config()
        llm_args = cfg.to_llm_args()

        try:
            content = _load_skill_body(name, auth)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Skill not found")

        state = compute_skill_state(name, content)
        decision = route(state, mode="auto")
        feedback_text = feedback.get("feedback", "") if feedback else ""

        result = evolve_with_moe(
            skill_name=name,
            skill_content=content,
            decision=decision,
            llm_args=llm_args,
            user_feedback=feedback_text,
        )

        return {
            "skill": name,
            "accepted": result.get("accepted", False),
            "round": result.get("round", 1),
            "expert": decision.primary.value if decision.primary else "unknown",
            "improvement": result.get("improvement", "none"),
            "detail": result.get("detail", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"skill": name, "accepted": False, "round": 0, "detail": str(e)}
    finally:
        reset(token)


@router.get("/{name}/state")
async def get_skill_state(name: str, auth: AuthContext = Depends(require_auth)):
    """Get skill state for MoE routing (trace_count, score_variance, maturity)."""
    token, reset = _tenant_token(auth)
    try:
        from skillos.evolution.skillopt import compute_skill_state

        try:
            content = _load_skill_body(name, auth)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Skill not found")

        state = compute_skill_state(name, content)
        return {
            "skill": name,
            "trace_count": state.trace_count,
            "score_variance": round(state.score_variance, 3),
            "maturity_days": state.maturity_days,
            "avg_score": round(state.avg_score, 1),
            "failure_rate": round(state.failure_rate, 2),
            "staleness": round(state.staleness, 2) if state.staleness else 0,
            "recommended_expert": state.recommended_expert.value if state.recommended_expert else "unknown",
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"skill": name, "trace_count": 0, "score_variance": 0, "maturity_days": 0, "error": str(e)}
    finally:
        reset(token)


@router.post("/{name}/route")
async def route_evolution(name: str, mode: str = "auto", auth: AuthContext = Depends(require_auth)):
    """Route skill to the best evolution expert (MoE gating network)."""
    token, reset = _tenant_token(auth)
    try:
        from skillos.evolution.skillopt import compute_skill_state, route

        try:
            content = _load_skill_body(name, auth)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Skill not found")

        state = compute_skill_state(name, content)
        decision = route(state, mode=mode)

        return {
            "skill": name,
            "routing": {
                "primary": decision.primary.value if decision.primary else "unknown",
                "secondary": decision.secondary.value if decision.secondary else None,
                "confidence": round(decision.confidence, 2),
                "reason": decision.reason,
            },
            "state_summary": {
                "trace_count": state.trace_count,
                "score_variance": round(state.score_variance, 3),
                "maturity_days": state.maturity_days,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"skill": name, "routing": {"primary": "SKILLOPT", "confidence": 0.5}, "error": str(e)}
    finally:
        reset(token)


@router.post("/consolidate")
async def run_consolidation(auth: AuthContext = Depends(require_auth)):
    """Run periodic knowledge consolidation across all skills and knowledge."""
    token, reset = _tenant_token(auth)
    try:
        from skillos.config import get_config
        from skillos.evolution.engine import run_evolution_check
        from skillos.knowledge.epistemology import get_store

        cfg = get_config()
        llm_args = cfg.to_llm_args()

        evo_result = run_evolution_check(llm_args)

        store = get_store()
        expired = store.expire_stale_claims()
        cross = store.cross_reference()
        promoted = store.attempt_promotion(llm_args)

        try:
            from skillos.evolution.learning_theory import get_stale_skills, refresh_skill

            stale = get_stale_skills()
            strengthened = 0
            for s in stale[:5]:
                try:
                    refresh_skill(s)
                    strengthened += 1
                except Exception:
                    pass
        except Exception:
            stale = []
            strengthened = 0

        total = expired + cross + promoted + strengthened
        return {
            "total_items": total,
            "strengthened": strengthened,
            "decayed": expired,
            "evolution_triggers": evo_result["triggers"],
            "top_triggers": evo_result.get("top_triggers", []),
            "epistemic": {
                "expired": expired,
                "cross_referenced": cross,
                "promoted": promoted,
            },
            "learning_theory": {
                "stale_skills": len(stale),
                "strengthened": strengthened,
            },
        }
    except Exception as e:
        return {"total_items": 0, "strengthened": 0, "decayed": 0, "error": str(e)}
    finally:
        reset(token)


@router.get("/triggers")
async def get_evolution_triggers(auth: AuthContext = Depends(require_auth)):
    """Get current evolution triggers without running full consolidation."""
    try:
        from skillos.evolution.engine import run_evolution_check

        result = run_evolution_check()
        return {
            "triggers": result["triggers"],
            "top_triggers": result.get("top_triggers", []),
            "suggestion": result.get("suggestion_text", ""),
        }
    except Exception as e:
        return {"triggers": 0, "top_triggers": [], "error": str(e)}


@router.post("/{name}/export-skillopt")
async def export_skillopt_bundle(name: str, auth: AuthContext = Depends(require_auth)):
    """Export skill + traces as SkillOpt-compatible ``best_skill.md`` bundle."""
    token, reset = _tenant_token(auth)
    try:
        from skillos.evolution.skillopt_export import export_for_skillopt
        from skillos.evolution.skillopt_runner import cli_help, validate_bundle

        result = export_for_skillopt(name, tenant=auth.tenant_context())
        validation = validate_bundle(result.export_dir)
        payload = {"ok": True, **result.to_dict(), "validation": validation}
        payload["cli"] = {
            "export": f"python scripts/skillopt_cli.py export {name}",
            "validate": f"python scripts/skillopt_cli.py validate {result.export_dir}",
            "run_dry": f"python scripts/skillopt_cli.py run {name} --dry-run",
        }
        payload["skillopt_help"] = cli_help()
        return payload
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        reset(token)


@router.get("/skillopt/cli")
async def skillopt_cli_help():
    """External SkillOpt CLI usage and environment variables."""
    from skillos.evolution.skillopt_runner import cli_help

    return cli_help()


@router.post("/{name}/skillopt-run")
async def skillopt_external_run(
    name: str,
    dry_run: bool = True,
    auth: AuthContext = Depends(require_auth),
):
    """Export bundle and optionally run SKILLOPT_EXTERNAL_CMD."""
    token, reset = _tenant_token(auth)
    try:
        from skillos.evolution.skillopt_runner import run_skillopt_external

        return run_skillopt_external(name, tenant=auth.tenant_context(), dry_run=dry_run)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        reset(token)
