"""Background tasks for full knowledge cycle (POST /api/knowledge/cycle)."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

TASKS_DIR = Path(__file__).parent.parent.parent / "data" / "cycle_tasks"
_lock = threading.Lock()
_running: set[str] = set()


@dataclass
class CycleTask:
    task_id: str
    status: str  # pending | running | completed | failed
    source_url: str
    content_chars: int
    created_at: float
    started_at: float = 0.0
    finished_at: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "task_id": self.task_id,
            "status": self.status,
            "source_url": self.source_url,
            "content_chars": self.content_chars,
            "created_at": self.created_at,
            "poll_url": f"/api/knowledge/cycle/{self.task_id}",
        }
        if self.started_at:
            out["started_at"] = self.started_at
        if self.finished_at:
            out["finished_at"] = self.finished_at
            out["elapsed_s"] = round(self.finished_at - self.started_at, 2) if self.started_at else 0
        if self.status == "completed" and self.result:
            out["result"] = self.result
            out["session_id"] = self.result.get("session_id", "")
        if self.status == "failed" and self.error:
            out["error"] = self.error
        return out


def _task_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.json"


def _save_task(task: CycleTask) -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    payload = asdict(task)
    _task_path(task.task_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_task(task_id: str) -> CycleTask | None:
    path = _task_path(task_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CycleTask(**data)
    except Exception as exc:
        _log.warning("Failed to load cycle task %s: %s", task_id, exc)
        return None


def get_cycle_task(task_id: str) -> CycleTask | None:
    with _lock:
        return _load_task(task_id)


def list_cycle_tasks(limit: int = 20) -> list[dict[str, Any]]:
    if not TASKS_DIR.exists():
        return []
    tasks: list[CycleTask] = []
    for path in sorted(TASKS_DIR.glob("kc_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        task = _load_task(path.stem)
        if task:
            tasks.append(task)
        if len(tasks) >= limit:
            break
    return [t.to_public_dict() for t in tasks]


def submit_cycle_task(content: str, source_url: str, llm_args: tuple) -> CycleTask:
    """Enqueue a knowledge cycle; returns task handle immediately."""
    task = CycleTask(
        task_id=f"kc_{uuid.uuid4().hex[:12]}",
        status="pending",
        source_url=source_url,
        content_chars=len(content),
        created_at=time.time(),
    )
    with _lock:
        _save_task(task)

    thread = threading.Thread(
        target=_run_task,
        args=(task.task_id, content, source_url, llm_args),
        daemon=True,
        name=f"cycle-{task.task_id}",
    )
    thread.start()
    return task


def _run_task(task_id: str, content: str, source_url: str, llm_args: tuple) -> None:
    with _lock:
        if task_id in _running:
            return
        _running.add(task_id)
        task = _load_task(task_id)
        if task is None:
            _running.discard(task_id)
            return
        task.status = "running"
        task.started_at = time.time()
        _save_task(task)

    try:
        from skillos.knowledge.ingest_dedup import should_skip_ingest

        if should_skip_ingest(source_url, content):
            with _lock:
                task = _load_task(task_id)
                if task:
                    task.status = "completed"
                    task.result = {
                        "skipped": True,
                        "reason": "unchanged",
                        "source_url": source_url,
                        "lineage": {"lineage_applied": False, "reason": "dedup_skip"},
                    }
                    task.finished_at = time.time()
                    _save_task(task)
            try:
                from skillos.knowledge.ingest_metrics import record_ingest_event
                record_ingest_event(
                    channel="full_knowledge_cycle",
                    source_url=source_url,
                    lineage={"lineage_applied": False, "reason": "dedup_skip", "channel": "full_knowledge_cycle"},
                    event_kind="skip",
                    extra={"skipped": True},
                )
            except Exception:
                pass
            return

        from skillos.knowledge.ingest_pipeline import run_full_knowledge_cycle

        result = run_full_knowledge_cycle(content, source_url, llm_args)
        with _lock:
            task = _load_task(task_id)
            if task:
                task.status = "completed"
                task.result = result
                task.finished_at = time.time()
                _save_task(task)
        try:
            from skillos.knowledge.ingest_metrics import record_ingest_event
            lineage = result.get("lineage") or {}
            record_ingest_event(
                channel="full_knowledge_cycle",
                source_url=source_url,
                lineage={
                    "lineage_applied": bool(lineage.get("lineage_applied")),
                    "items_added": lineage.get("total_items", 0),
                    "edges_created": lineage.get("edges_created", 0),
                    "session_id": result.get("session_id", ""),
                    "channel": "full_knowledge_cycle",
                },
                event_kind="cycle",
                extra={"elapsed_s": result.get("elapsed_s", 0)},
            )
        except Exception:
            pass
    except Exception as exc:
        _log.exception("Knowledge cycle task %s failed", task_id)
        with _lock:
            task = _load_task(task_id)
            if task:
                task.status = "failed"
                task.error = str(exc)
                task.finished_at = time.time()
                _save_task(task)
        try:
            from skillos.knowledge.ingest_metrics import record_ingest_event
            record_ingest_event(
                channel="full_knowledge_cycle",
                source_url=source_url,
                lineage={"lineage_applied": False, "reason": str(exc), "channel": "full_knowledge_cycle"},
                event_kind="cycle",
            )
        except Exception:
            pass
    finally:
        with _lock:
            _running.discard(task_id)
