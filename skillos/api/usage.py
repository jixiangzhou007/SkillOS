"""Usage and BYOK API (Sprint 5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skillos.billing.usage import QuotaExceededError, get_usage_summary, set_user_byok
from skillos.identity.middleware import AuthContext, require_auth

router = APIRouter()


class ByokRequest(BaseModel):
    enabled: bool = True
    api_key: str = ""


@router.get("/me")
async def usage_me(auth: AuthContext = Depends(require_auth)):
    """Current workspace usage vs Personal Free limits."""
    summary = get_usage_summary(auth.tenant_id, auth.platform_user_id)
    return summary.to_dict()


@router.post("/byok")
async def configure_byok(req: ByokRequest, auth: AuthContext = Depends(require_auth)):
    """Enable/disable bring-your-own-key for LLM quota exemption."""
    if req.enabled and len(req.api_key.strip()) < 8:
        raise HTTPException(status_code=400, detail="API key too short")
    set_user_byok(auth.user_id, enabled=req.enabled, api_key=req.api_key.strip())
    return {"ok": True, "byok": req.enabled}
