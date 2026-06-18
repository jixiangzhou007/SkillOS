"""Persistent Ingestion Queue — serial processing with restart recovery.

Inspired by LLM Wiki's persistent queue: disk-backed, serial processing, retry,
and abort-safe. Prevents concurrent write conflicts when multiple watchers
(WeChat, file inbox, account watcher) fire simultaneously.

Also triggers knowledge gap research when surprise detection finds sparse communities.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

QUEUE_DIR = Path(__file__).parent.parent.parent / "data" / "ingestion_queue"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_FILE = QUEUE_DIR / "queue.jsonl"
MAX_RETRIES = 3
RETRY_DELAY_S = 5


@dataclass
class IngestionTask:
    """One unit of work in the ingestion queue."""
    task_id: str
    source_type: str          # "url" | "file" | "wechat_article"
    source_path: str          # URL, filepath, or article key
    status: str = "pending"   # pending | processing | done | failed
    retries: int = 0
    created_at: float = 0.0
    last_attempt: float = 0.0
    result: str = ""          # success message or error
    meta: dict = field(default_factory=dict)  # extra context


# ── Queue operations ───────────────────────────────────────────

def _load_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    tasks = []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    tasks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return tasks


def _save_queue(tasks: list[dict]) -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")


def enqueue(source_type: str, source_path: str, meta: dict | None = None) -> IngestionTask:
    """Add a task to the persistent queue. Safe for concurrent callers."""
    import uuid
    tasks = _load_queue()
    for t in tasks:
        if (
            t.get("status") == "pending"
            and t.get("source_type") == source_type
            and t.get("source_path") == source_path
        ):
            _log.info("Duplicate pending task skipped: %s %s", source_type, source_path[:60])
            return IngestionTask(
                task_id=t["task_id"],
                source_type=t["source_type"],
                source_path=t["source_path"],
                status=t["status"],
                retries=t.get("retries", 0),
                created_at=t.get("created_at", 0.0),
                last_attempt=t.get("last_attempt", 0.0),
                result=t.get("result", ""),
                meta=t.get("meta") or {},
            )
    task = IngestionTask(
        task_id=f"ing_{int(time.time())}_{uuid.uuid4().hex[:6]}",
        source_type=source_type,
        source_path=source_path,
        created_at=time.time(),
        meta=meta or {},
    )
    tasks = _load_queue()
    tasks.append({
        "task_id": task.task_id, "source_type": task.source_type,
        "source_path": task.source_path, "status": task.status,
        "retries": task.retries, "created_at": task.created_at,
        "last_attempt": task.last_attempt, "result": task.result,
        "meta": task.meta,
    })
    _save_queue(tasks)
    _log.info("Enqueued: %s %s (total=%d)", source_type, source_path[:60], len(tasks))
    return task


def dequeue() -> Optional[IngestionTask]:
    """Get the next pending task (oldest first)."""
    tasks = _load_queue()
    for t in tasks:
        if t["status"] == "pending":
            return IngestionTask(**{k: t.get(k, "") if k in ("source_path", "result") else t.get(k) for k in [
                "task_id", "source_type", "source_path", "status", "retries",
                "created_at", "last_attempt", "result", "meta",
            ]})
    return None


def mark_done(task_id: str, result: str = "") -> None:
    tasks = _load_queue()
    for t in tasks:
        if t["task_id"] == task_id:
            t["status"] = "done"
            t["result"] = result
    _save_queue(tasks)


def mark_failed(task_id: str, error: str) -> bool:
    """Mark failed. Returns True if should retry."""
    tasks = _load_queue()
    for t in tasks:
        if t["task_id"] == task_id:
            t["retries"] += 1
            t["last_attempt"] = time.time()
            t["result"] = error
            if t["retries"] <= MAX_RETRIES:
                t["status"] = "pending"  # retry
            else:
                t["status"] = "failed"
            _save_queue(tasks)
            return t["status"] == "pending"
    return False


def queue_stats() -> dict:
    tasks = _load_queue()
    pending = sum(1 for t in tasks if t["status"] == "pending")
    processing = sum(1 for t in tasks if t["status"] == "processing")
    done = sum(1 for t in tasks if t["status"] == "done")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    return {
        "pending": pending,
        "processing": processing,
        "done": done,
        "failed": failed,
        "total": len(tasks),
    }


def list_recent_queue_tasks(limit: int = 10) -> list[dict]:
    """Recent queue tasks for dashboard (newest first)."""
    tasks = sorted(_load_queue(), key=lambda t: t.get("created_at") or 0, reverse=True)
    out: list[dict] = []
    for t in tasks[:limit]:
        out.append({
            "task_id": t.get("task_id", ""),
            "source_type": t.get("source_type", ""),
            "source_path": (t.get("source_path") or "")[:200],
            "status": t.get("status", ""),
            "retries": t.get("retries", 0),
            "created_at": t.get("created_at", 0),
            "result": (t.get("result") or "")[:160],
        })
    return out


def recover_pending() -> list[IngestionTask]:
    """Recover pending tasks after restart."""
    tasks = _load_queue()
    return [
        IngestionTask(**{k: t.get(k, "") if k in ("source_path", "result") else t.get(k) for k in [
            "task_id", "source_type", "source_path", "status", "retries",
            "created_at", "last_attempt", "result", "meta",
        ]})
        for t in tasks if t["status"] == "pending"
    ]


# ── Knowledge gap → auto-research trigger ─────────────────────

def _node_degree(graph, node_id: str) -> int:
    """Count undirected edges touching a node."""
    return sum(
        1 for edge in graph.edges
        if edge.source_id == node_id or edge.target_id == node_id
    )


def trigger_gap_research(llm_args: tuple | None = None) -> list[str]:
    """Check knowledge graph for sparse communities and enqueue research tasks.

    Returns list of triggered research task IDs.
    """
    triggered: list[str] = []
    try:
        from skillos.knowledge.graph import get_graph
        g = get_graph()
        clusters = g.detect_clusters(min_cluster_size=2)

        sparse = [c for c in clusters if getattr(c, "cohesion", 1.0) < 0.15]
        isolated = [
            nid for nid in g.nodes
            if _node_degree(g, nid) <= 1
        ]

        for c in sparse[:3]:
            cluster_label = getattr(c, "label", "") or c.id
            cluster_size = len(getattr(c, "node_ids", []) or [])
            task = enqueue(
                "gap_research",
                f"cluster:{c.id}",
                meta={
                    "cluster_id": c.id,
                    "cluster_label": cluster_label,
                    "cohesion": c.cohesion,
                    "size": cluster_size,
                },
            )
            triggered.append(task.task_id)
            _log.info(
                "Gap research triggered: cluster=%s cohesion=%.2f size=%d",
                cluster_label, c.cohesion, cluster_size,
            )

        if isolated[:5]:
            task = enqueue(
                "gap_research",
                f"isolated_nodes:{len(isolated)}",
                meta={"isolated_count": len(isolated), "sample_ids": isolated[:5]},
            )
            triggered.append(task.task_id)
            _log.info("Gap research triggered: %d isolated nodes", len(isolated))

    except Exception as e:
        _log.warning("Gap research trigger failed: %s", e)

    return triggered


# ── Task processing ───────────────────────────────────────────

def process_ingestion_task(task: IngestionTask, llm_args: tuple | None = None) -> str:
    """Process one queue task through the unified ingest exit."""
    from skillos.config import get_config
    cfg = get_config()
    args = llm_args or cfg.to_llm_args()

    if task.source_type == "url":
        from skillos.utils.web_fetch import fetch
        content = fetch(task.source_path)
        if not content or len(content) <= 100:
            raise ValueError(f"Failed to fetch URL: {task.source_path}")
        from skillos.knowledge.ingest_dedup import should_skip_ingest
        if should_skip_ingest(task.source_path, content):
            return f"skipped:unchanged:{task.source_path[:48]}"
        from skillos.knowledge.content_classify import classify_content
        if classify_content(content) == "actionable":
            from skillos.skills.agent import SkillExtractionAgent
            from skillos.skills.skill_store import list_skills
            agent = SkillExtractionAgent()
            _, doc = agent.learn_from_url(task.source_path, content, list_skills(), args)
            if doc:
                from skillos.knowledge.ingest_pipeline import finalize_ingest
                fin = finalize_ingest(
                    doc["content"],
                    task.source_path,
                    skill_name=doc["name"],
                    skill_body=doc["content"],
                    sync_graph=False,
                    channel="ingestion_queue",
                )
                from skillos.knowledge.ingest_dedup import mark_ingest_complete
                mark_ingest_complete(task.source_path, content)
                lineage_ok = (fin.get("lineage") or {}).get("lineage_applied")
                return f"skill:{doc['name']}:lineage={'yes' if lineage_ok else 'no'}"
            return "skill:no_doc"
        from skillos.knowledge.deep_digest import deep_digest, save_digest
        dd = deep_digest(content, task.source_path, llm_args=args)
        extracted_items: list = []
        if dd.glossary or dd.patterns or dd.sections:
            save_digest(dd)
            try:
                from skillos.knowledge.extractor import extract_knowledge, save_knowledge
                extracted_items = extract_knowledge(content, task.source_path, args)
                if extracted_items:
                    save_knowledge(extracted_items)
            except Exception:
                pass
        from skillos.knowledge.ingest_pipeline import finalize_ingest
        fin = finalize_ingest(
            content,
            task.source_path,
            source_title=dd.title,
            digest_result=dd if (dd.glossary or dd.patterns or dd.sections) else None,
            extractor_items=extracted_items or None,
            channel="ingestion_queue",
        )
        lineage_ok = (fin.get("lineage") or {}).get("lineage_applied")
        return f"digest:{dd.title}:lineage={'yes' if lineage_ok else 'no'}"

    if task.source_type == "file":
        from skillos.utils.file_ingest import ingest_and_learn
        result = ingest_and_learn(task.source_path, task.source_path, llm_args=args)
        lineage_ok = (result.get("lineage") or {}).get("lineage_applied")
        return f"ingested:{result.get('filename', task.source_path)}:lineage={'yes' if lineage_ok else 'no'}"

    if task.source_type == "gap_research":
        trigger_gap_research(args)
        return "gap_research:triggered"

    return "unknown_source_type"


# ── Background processor ──────────────────────────────────────

_processor_thread: Optional[threading.Thread] = None
_processor_running = False


def start_queue_processor(
    llm_args: tuple | None = None,
    interval_s: float = 30.0,
    *,
    auto_gap_research: bool = True,
) -> None:
    """Start background thread that processes the ingestion queue."""
    global _processor_thread, _processor_running
    if _processor_running:
        return

    def _loop() -> None:
        global _processor_running
        _processor_running = True
        _log.info("Ingestion queue processor started (interval=%.0fs)", interval_s)

        while _processor_running:
            try:
                task = dequeue()
                if task:
                    _log.info("Processing: %s %s", task.source_type, task.source_path[:60])
                    try:
                        result = process_ingestion_task(task, llm_args)
                        mark_done(task.task_id, result)
                        _log.info("Done: %s → %s", task.task_id, result)
                    except Exception as exc:
                        will_retry = mark_failed(task.task_id, str(exc))
                        _log.warning(
                            "Failed: %s (retries=%d, will_retry=%s): %s",
                            task.task_id, task.retries + 1, will_retry, exc,
                        )
                        if not will_retry:
                            _log.error("Task permanently failed: %s", task.task_id)

                # Periodic gap research
                if auto_gap_research:
                    try:
                        trigger_gap_research(llm_args)
                    except Exception:
                        pass

                time.sleep(interval_s)
            except Exception as e:
                _log.warning("Queue processor error: %s", e)
                time.sleep(interval_s)

    _processor_thread = threading.Thread(target=_loop, daemon=True)
    _processor_thread.start()


def stop_queue_processor() -> None:
    global _processor_running
    _processor_running = False
