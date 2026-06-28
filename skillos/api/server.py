"""SkillOS API Server — FastAPI-based, clean routing, auto-documented."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

_log = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


@asynccontextmanager
async def _lifespan(app):
    from skillos.config import get_config
    cfg = get_config()
    for issue in cfg.validate():
        _log.warning("Config: %s", issue)
    _log.info("SkillOS %s — %s", "cloud" if cfg.api_key != "ollama" else "ollama", cfg.model)
    try:
        from skillos.hermes_bridge import check_compatibility
        compat = check_compatibility()
        if compat["hermes_version"]:
            _log.info("Hermes %s %s", compat["hermes_version"],
                      "OK" if compat["compatible"] else "MISMATCH")
    except Exception: pass
    try:
        from skillos.db import get_conn; get_conn()
    except Exception: pass
    # Start autonomous evolution scheduler
    try:
        from skillos.evolution.engine import start_evolution_scheduler
        start_evolution_scheduler(interval_hours=6)
        _log.info("Evolution auto-scheduler started (6h interval)")
    except Exception: pass
    # Opt-in file inbox watcher; periodic refresh enabled by default (SKILLOS_DISABLE_REFRESH=1 to off)
    if cfg.enable_periodic_refresh:
        try:
            from skillos.knowledge.refresher import start_periodic_refresh
            start_periodic_refresh(interval_hours=cfg.refresh_interval_hours)
            _log.info("Knowledge refresher started (%.1fh interval)", cfg.refresh_interval_hours)
        except Exception as exc:
            _log.warning("Knowledge refresher failed to start: %s", exc)
    if cfg.enable_file_watcher:
        try:
            from skillos.utils.watcher import start_watching
            start_watching(interval=cfg.watcher_poll_interval)
            _log.info("File inbox watcher started (poll=%.1fs)", cfg.watcher_poll_interval)
        except Exception as exc:
            _log.warning("File watcher failed to start: %s", exc)
    # Ingestion queue processor (serialises watcher outputs, enables gap research)
    try:
        from skillos.knowledge.ingestion_queue import recover_pending, start_queue_processor
        pending = recover_pending()
        if pending:
            _log.info("Recovered %d pending ingestion tasks after restart", len(pending))
        start_queue_processor(llm_args=None, interval_s=30, auto_gap_research=True)
        _log.info("Ingestion queue processor started")
    except Exception as exc:
        _log.warning("Ingestion queue processor failed to start: %s", exc)
    yield
    # Shutdown
    try:
        from skillos.knowledge.ingestion_queue import stop_queue_processor
        stop_queue_processor()
    except Exception:
        pass
    try:
        from skillos.evolution.engine import stop_evolution_scheduler
        stop_evolution_scheduler()
    except Exception: pass
    try:
        from skillos.knowledge.refresher import stop_periodic_refresh
        stop_periodic_refresh()
    except Exception: pass
    try:
        from skillos.utils.watcher import stop_watching
        stop_watching()
    except Exception: pass


app = FastAPI(
    title="SkillOS API",
    version="0.3.5",
    description="AI Skill Operating System — extract, verify, evolve Agent Skills. OpenAPI docs for MCP integration.",
    lifespan=_lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)

# Cache static assets with version query strings for 1 year
from starlette.middleware.base import BaseHTTPMiddleware
class CacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if any(path.endswith(ext) for ext in ('.css','.js','.html','.svg','.png','.ico')):
            if '?v=' in str(request.url.query) or path.endswith(('.png','.ico','.svg')):
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
app.add_middleware(CacheStaticMiddleware)


@app.exception_handler(HTTPException)
async def _http_exception_handler(request, exc: HTTPException):
    if exc.status_code >= 500:
        try:
            from skillos.analytics.funnel import track_api_error
            track_api_error(path=str(request.url.path), status=exc.status_code)
        except Exception:
            pass
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


from skillos.api import (
    analytics,
    approval,
    auth,
    bench_official,
    billing,
    channels,
    docs_api,
    evolution,
    intelligence,
    knowledge,
    marketplace,
    org_admin,
    organizations,
    skills,
    usage,
    voice,
    workspaces,
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(organizations.router, prefix="/api/orgs", tags=["Organizations"])
app.include_router(org_admin.router, prefix="/api/orgs", tags=["OrgAdmin"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(docs_api.router, prefix="/api/docs", tags=["Docs"])
app.include_router(approval.router, prefix="/api/approval", tags=["Approval"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(usage.router, prefix="/api/usage", tags=["Usage"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
app.include_router(bench_official.router, prefix="/api/bench/official", tags=["OfficialBench"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(evolution.router, prefix="/api/evolution", tags=["Evolution"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["Intelligence"])
app.include_router(marketplace.router, prefix="/api/marketplace", tags=["Marketplace"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    # Minimal 1x1 transparent ico to avoid 404 in browser console
    return Response(content=b'\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', media_type='image/x-icon')


@app.get("/health")
async def health():
    try:
        from skillos.analytics.sla import record_health_ping
        record_health_ping()
    except Exception:
        pass
    return {"status": "ok", "version": "0.2.1", "agent_opening": "domain-v2"}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def start(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start()
