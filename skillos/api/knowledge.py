"""Knowledge ingestion, retrieval, lineage, and wisdom endpoints."""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class KnowledgeCycleRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Source text to internalize")
    source_url: str = Field("manual://cycle", description="Provenance URL or file:// path")


@router.get("/")
async def list_knowledge(
    category: str = Query("", description="Filter by category"),
    show: str = Query("valid", description="valid | all | superseded"),
    q: str = Query("", description="Search content or id"),
):
    """List global knowledge items with validity filtering."""
    try:
        from skillos.knowledge.extractor import load_all_knowledge
        items = load_all_knowledge()
        if show == "valid":
            from skillos.knowledge.epistemology import get_store
            store = get_store()
            valid_ids = {c.claim_id for c in store.get_knowledge() if c.is_current}
            items = [i for i in items if getattr(i, 'item_id', '') in valid_ids or i.category == 'verified']
        elif show == "superseded":
            from skillos.knowledge.epistemology import get_store
            store = get_store()
            superseded = [c for c in store.claims.values() if not c.is_current]
            items = [i for i in items if any(s.claim_id == getattr(i, 'item_id', '') for s in superseded)]

        if category:
            items = [i for i in items if getattr(i, 'category', '') == category]

        if q:
            ql = q.lower()
            items = [
                i for i in items
                if ql in getattr(i, 'content', '').lower()
                or ql in getattr(i, 'item_id', '').lower()
            ]

        return {
            "total": len(items), "show": show,
            "items": [{
                "id": getattr(i, "item_id", ""),
                "content": getattr(i, "content", "")[:500],
                "category": getattr(i, "category", "unknown"),
                "confidence": getattr(i, "confidence", 0.5),
                "needs_review": getattr(i, "needs_review", False),
                "source_url": getattr(i, "source_url", ""),
                "created_at": getattr(i, "created_at", 0),
            } for i in items[:50]]
        }
    except Exception as e:
        return {"total": 0, "show": show, "items": [], "error": str(e)}


@router.get("/lineage")
async def list_lineages():
    """List all knowledge lineage sessions."""
    try:
        from skillos.knowledge.lineage import list_lineages
        sessions = list_lineages()
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        return {"sessions": [], "count": 0, "error": str(e)}


@router.post("/cycle")
async def run_knowledge_cycle(req: KnowledgeCycleRequest):
    """Enqueue full knowledge internalization (digest → lineage → graph → wisdom).

    Returns immediately with task_id; poll GET /cycle/{task_id} for result.
    """
    try:
        from skillos.config import get_config
        from skillos.knowledge.cycle_tasks import submit_cycle_task

        llm_args = get_config().to_llm_args()
        task = submit_cycle_task(req.content, req.source_url, llm_args)
        return task.to_public_dict()
    except Exception as e:
        return {"error": str(e), "task_id": "", "status": "failed"}


@router.get("/cycle/recent")
async def list_recent_knowledge_cycles(limit: int = Query(10, ge=1, le=50)):
    """List recent async knowledge cycle tasks."""
    try:
        from skillos.knowledge.cycle_tasks import list_cycle_tasks
        tasks = list_cycle_tasks(limit=limit)
        return {"count": len(tasks), "tasks": tasks}
    except Exception as e:
        return {"count": 0, "tasks": [], "error": str(e)}


@router.get("/cycle/{task_id}")
async def get_knowledge_cycle_status(task_id: str):
    """Poll async knowledge cycle task status and result."""
    try:
        from skillos.knowledge.cycle_tasks import get_cycle_task

        task = get_cycle_task(task_id)
        if task is None:
            return {"task_id": task_id, "status": "not_found", "error": "task not found"}
        return task.to_public_dict()
    except Exception as e:
        return {"task_id": task_id, "status": "error", "error": str(e)}


@router.get("/queue")
async def get_ingestion_queue_status(limit: int = Query(10, ge=1, le=50)):
    """Persistent ingestion queue stats and recent tasks."""
    try:
        from skillos.knowledge.ingestion_queue import list_recent_queue_tasks, queue_stats

        return {
            "stats": queue_stats(),
            "tasks": list_recent_queue_tasks(limit=limit),
        }
    except Exception as e:
        return {"stats": {}, "tasks": [], "error": str(e)}


@router.get("/skill-lineage")
async def skill_precipitation_lineage(
    skill_name: str = Query("", description="Filter by skill name"),
    chat_id: str = Query("", description="Filter by chat/group id"),
    user_id: str = Query("", description="Filter by user id"),
    session_id: str = Query("", description="Filter by session id"),
):
    """Query skill precipitation lineage — who, which chat, which session."""
    try:
        from skillos.knowledge.lineage import query_skill_precipitations
        events = query_skill_precipitations(
            skill_name=skill_name,
            chat_id=chat_id,
            user_id=user_id,
            session_id=session_id,
        )
        return {"count": len(events), "events": events}
    except Exception as e:
        return {"count": 0, "events": [], "error": str(e)}


@router.get("/lineage/{session_id}")
async def get_lineage(session_id: str):
    """Get a specific lineage session with its knowledge items."""
    try:
        from skillos.knowledge.lineage import load_lineage
        lg = load_lineage(session_id)
        if lg is None:
            return {"session_id": session_id, "items": [], "found": False}
        return {
            "session_id": session_id,
            "source_url": lg.source_url,
            "source_title": lg.source_title,
            "total_items": lg.total_items,
            "items": [{"id": i.item_id, "content": i.content[:200], "category": i.category}
                      for i in lg.items[:30]],
            "found": True,
        }
    except Exception as e:
        return {"session_id": session_id, "items": [], "error": str(e)}


@router.get("/lineage/{session_id}/graph")
async def get_lineage_graph(session_id: str):
    """Get lineage graph in cytoscape and mermaid formats."""
    try:
        from skillos.knowledge.lineage import load_lineage
        lg = load_lineage(session_id)
        if lg is None:
            return {"session_id": session_id, "cytoscape": {"nodes": [], "edges": []}, "mermaid": ""}

        # Build cytoscape nodes/edges
        nodes, edges = [], []
        for item in lg.items:
            nodes.append({
                "data": {
                    "id": item.item_id,
                    "label": item.content[:80],
                    "type": item.category or "knowledge",
                    "category": item.category,
                    "confidence": getattr(item, "confidence", 0.5),
                    "level": getattr(item, "level", "experience"),
                }
            })
        for i in range(len(lg.items) - 1):
            edges.append({"data": {"source": lg.items[i].item_id, "target": lg.items[i+1].item_id,
                                   "label": "derived_from"}})

        # Build mermaid
        mermaid = "graph LR\n"
        for i, item in enumerate(lg.items[:20]):
            node_id = f"n{i}"
            label = item.content[:40].replace('"', "'")
            mermaid += f"    {node_id}[\"{label}\"]\n"
            if i > 0:
                mermaid += f"    n{i-1} --> {node_id}\n"

        return {"session_id": session_id, "cytoscape": {"nodes": nodes, "edges": edges}, "mermaid": mermaid}
    except Exception as e:
        return {"session_id": session_id, "cytoscape": {"nodes": [], "edges": []}, "mermaid": "", "error": str(e)}


@router.get("/graph/clusters")
async def get_graph_clusters():
    """Get knowledge graph community clusters."""
    try:
        from skillos.knowledge.graph import get_graph
        g = get_graph()
        clusters = g.detect_clusters(min_cluster_size=2)
        return {
            "clusters": [
                {
                    "id": c.id,
                    "label": c.label,
                    "nodes": len(c.node_ids),
                    "cohesion": round(c.cohesion, 3),
                    "central_node": c.central_node,
                }
                for c in clusters
            ],
            "total_nodes": len(g.nodes),
            "total_edges": len(g.edges),
        }
    except Exception as e:
        return {"clusters": [], "total_nodes": 0, "total_edges": 0, "error": str(e)}


@router.get("/metrics")
async def get_knowledge_metrics(
    window_hours: float = Query(168, ge=1, le=720, description="Aggregation window in hours"),
):
    """Precipitation success rate, lineage coverage, and refresher status."""
    try:
        from skillos.knowledge.ingest_metrics import get_metrics_summary
        return get_metrics_summary(window_hours=window_hours)
    except Exception as e:
        return {"error": str(e), "total_events": 0}


@router.get("/wisdom")
async def get_wisdom():
    """Get cross-lineage meta-patterns and insights."""
    try:
        from skillos.knowledge.lineage import extract_wisdom
        w = extract_wisdom()
        return {"wisdom": bool(w.get("wisdom")), "insights": w.get("insights", [])}
    except Exception as e:
        return {"wisdom": False, "insights": [], "error": str(e)}


@router.get("/journal")
async def get_journal(limit: int = Query(50, description="Max entries to return")):
    """Get learning journal entries."""
    try:
        from skillos.evolution.learning_theory import read_journal
        entries = read_journal(limit=limit)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        return {"entries": [], "count": 0, "error": str(e)}


@router.get("/review")
async def get_review_queue():
    """Get knowledge items flagged for human review."""
    try:
        from skillos.knowledge.epistemology import get_store
        from skillos.knowledge.extractor import load_all_knowledge

        store = get_store()
        items: list[dict] = []
        seen: set[str] = set()

        for exp in store.get_experiences():
            items.append({
                "id": exp.claim_id,
                "content": exp.content[:500],
                "confidence": exp.confidence,
                "source": exp.source,
                "is_stale": exp.is_stale,
                "needs_review": True,
                "review_kind": "experience",
                "created_at": exp.created_at,
            })
            seen.add(exp.claim_id)

        for ki in load_all_knowledge():
            if not ki.needs_review or ki.item_id in seen:
                continue
            items.append({
                "id": ki.item_id,
                "content": ki.content[:500],
                "confidence": ki.confidence,
                "source": ki.source_url or ki.item_id,
                "is_stale": ki.invalid_at != 0,
                "needs_review": True,
                "review_kind": "extractor",
                "review_reason": ki.review_reason or "低置信度",
                "created_at": ki.created_at,
            })

        items.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        return {"count": len(items), "items": items[:50]}
    except Exception as e:
        return {"count": 0, "items": [], "error": str(e)}


# ── Account Watcher ──────────────────────────────────────────

@router.get("/accounts")
async def list_watched_accounts():
    """List all watched WeChat accounts."""
    from skillos.knowledge.incremental_store import get_incremental_store
    accounts = get_incremental_store().list_accounts()
    return {"accounts": accounts, "count": len(accounts)}


@router.post("/accounts/add")
async def add_watched_account(name: str = "", interval_hours: float = 6.0):
    """Add a WeChat account to watch and optionally start scheduler."""
    if not name:
        return {"error": "name required"}
    from skillos.utils.account_watcher import add_account, start_scheduler
    from skillos.knowledge.incremental_store import get_incremental_store
    result = add_account(name)
    get_incremental_store().update_account_meta(
        name, interval_hours=interval_hours, active=True,
    )
    start_scheduler(interval_hours)
    return result


@router.post("/accounts/remove")
async def remove_watched_account(name: str = ""):
    """Stop watching an account."""
    from skillos.knowledge.incremental_store import get_incremental_store
    get_incremental_store().update_account_meta(name, active=False)
    return {"removed": name}


@router.post("/accounts/interval")
async def set_interval(name: str = "", hours: float = 6.0):
    """Set check interval for an account."""
    from skillos.knowledge.incremental_store import get_incremental_store
    get_incremental_store().update_account_meta(name, interval_hours=hours)
    return {"name": name, "interval_hours": hours}


@router.post("/accounts/check")
async def check_now():
    """Manually trigger a check of all watched accounts."""
    from skillos.utils.account_watcher import check_all_accounts
    return check_all_accounts()


@router.get("/accounts/login-qr")
async def get_login_qr():
    """Get WeChat MP login QR code URL for scanning."""
    from skillos.utils.account_watcher import get_login_qrcode
    qr = get_login_qrcode()
    return {"qr_url": qr, "logged_in": qr is None}


@router.get("/accounts/login-status")
async def check_login_status():
    """Check if WeChat MP is logged in."""
    from skillos.utils.account_watcher import is_wechat_logged_in
    return {"logged_in": is_wechat_logged_in()}
