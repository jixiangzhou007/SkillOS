"""Channel webhooks — Feishu bot α (Sprint 3)."""


import os

from fastapi import APIRouter, Header, Request

router = APIRouter()


@router.post("/feishu")
async def feishu_webhook(
    request: Request,
    authorization: str | None = Header(None),
):
    """Feishu event subscription endpoint → dispatch extract/chat."""
    body = await request.json()
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        token = os.getenv("SKILLOS_FEISHU_SERVICE_TOKEN", "").strip()

    from skillos.channels.feishu_webhook import handle_feishu_event
    return await handle_feishu_event(body, auth_token=token)
