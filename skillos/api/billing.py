"""Billing & plan API (Sprint 9)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skillos.billing.plans import PLAN_PERSONAL_PRO, get_user_plan, plan_limits, set_user_plan
from skillos.identity.middleware import AuthContext, require_auth

router = APIRouter()


class EnableProRequest(BaseModel):
    beta_code: str = ""


@router.get("/plan")
async def current_plan(auth: AuthContext = Depends(require_auth)):
    plan = get_user_plan(auth.user_id)
    skills, llm = plan_limits(plan)
    return {
        "plan": plan,
        "limits": {"skills": skills, "llm_monthly": llm},
        "billing_provider": "none",
        "note": "Stripe/国内支付集成预留 — 见 docs/sprint9/BILLING_RESEARCH.md",
    }


@router.get("/creator-summary")
async def creator_summary(auth: AuthContext = Depends(require_auth)):
    """Creator revenue summary — payout integration reserved (Sprint 11)."""
    from skillos.marketplace.payments import get_author_revenue

    revenue = get_author_revenue(auth.user_id)
    return {
        **revenue,
        "payout_status": "reserved",
        "payout_provider": "none",
        "note": "Creator 分成结算预留 — 见 docs/sprint11/GOVERNANCE.md",
    }


@router.post("/enable-pro")
async def enable_pro_beta(req: EnableProRequest, auth: AuthContext = Depends(require_auth)):
    """Enable Personal Pro (beta) with invite code."""
    expected = os.getenv("SKILLOS_PRO_BETA_CODE", "skillos-pro-beta")
    if req.beta_code.strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid beta code")
    if not auth.tenant_id.startswith("personal:"):
        raise HTTPException(status_code=400, detail="Pro plan applies to personal workspace only")
    set_user_plan(auth.user_id, PLAN_PERSONAL_PRO)
    skills, llm = plan_limits(PLAN_PERSONAL_PRO)
    return {"ok": True, "plan": PLAN_PERSONAL_PRO, "limits": {"skills": skills, "llm_monthly": llm}}
