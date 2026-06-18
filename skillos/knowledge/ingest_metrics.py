"""Ingest metrics — precipitation success rate and lineage coverage."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

METRICS_PATH = Path(__file__).parent.parent.parent / "data" / "incremental" / "ingest_metrics.jsonl"
DEFAULT_WINDOW_HOURS = 168  # 7 days


def _is_soft_success(lineage: dict | None) -> bool:
    if not lineage:
        return False
    if lineage.get("lineage_applied"):
        return True
    reason = lineage.get("reason", "")
    return reason in ("no_items", "dedup_skip")


def record_ingest_event(
    *,
    channel: str,
    source_url: str = "",
    lineage: dict | None = None,
    event_kind: str = "ingest",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one ingest / cycle outcome for metrics aggregation."""
    lineage = lineage or {}
    event = {
        "event_id": f"im_{uuid.uuid4().hex[:10]}",
        "timestamp": time.time(),
        "event_kind": event_kind,
        "channel": channel or lineage.get("channel", ""),
        "source_url": (source_url or "")[:200],
        "lineage_applied": bool(lineage.get("lineage_applied")),
        "items_added": int(lineage.get("items_added", 0) or 0),
        "edges_created": int(lineage.get("edges_created", 0) or 0),
        "reason": str(lineage.get("reason", "")),
        "success": _is_soft_success(lineage),
        "session_id": lineage.get("session_id", ""),
    }
    if extra:
        event.update(extra)
    try:
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:
        _log.debug("Failed to record ingest metric: %s", exc)
    return event


def _load_events(window_hours: float = DEFAULT_WINDOW_HOURS) -> list[dict[str, Any]]:
    if not METRICS_PATH.exists():
        return []
    cutoff = time.time() - window_hours * 3600
    events: list[dict[str, Any]] = []
    for line in METRICS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (ev.get("timestamp") or 0) >= cutoff:
            events.append(ev)
    return events


def get_metrics_summary(window_hours: float = DEFAULT_WINDOW_HOURS) -> dict[str, Any]:
    """Aggregate success rate and lineage coverage for dashboard/API."""
    events = _load_events(window_hours)
    total = len(events)
    success_count = sum(1 for e in events if e.get("success"))
    lineage_count = sum(1 for e in events if e.get("lineage_applied"))
    skip_count = sum(1 for e in events if e.get("event_kind") == "skip" or e.get("reason") == "dedup_skip")

    by_channel: dict[str, dict[str, int]] = {}
    recent_failures: list[dict[str, Any]] = []
    for ev in events:
        ch = ev.get("channel") or "unknown"
        bucket = by_channel.setdefault(ch, {"total": 0, "success": 0, "lineage": 0})
        bucket["total"] += 1
        if ev.get("success"):
            bucket["success"] += 1
        if ev.get("lineage_applied"):
            bucket["lineage"] += 1
        if not ev.get("success"):
            recent_failures.append({
                "event_id": ev.get("event_id"),
                "channel": ch,
                "source_url": ev.get("source_url", ""),
                "reason": ev.get("reason", ""),
                "timestamp": ev.get("timestamp", 0),
            })

    recent_failures.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)

    try:
        from skillos.knowledge.refresher import is_periodic_refresh_running
        from skillos.config import get_config
        cfg = get_config()
        refresher_running = is_periodic_refresh_running()
        refresher_interval = cfg.refresh_interval_hours
        refresher_enabled = cfg.enable_periodic_refresh
    except Exception:
        refresher_running = False
        refresher_interval = 24.0
        refresher_enabled = True

    return {
        "window_hours": window_hours,
        "total_events": total,
        "success_count": success_count,
        "success_rate": round(success_count / total, 3) if total else None,
        "lineage_applied_count": lineage_count,
        "lineage_coverage_rate": round(lineage_count / total, 3) if total else None,
        "skip_count": skip_count,
        "by_channel": {
            ch: {
                **counts,
                "success_rate": round(counts["success"] / counts["total"], 3) if counts["total"] else None,
                "lineage_coverage_rate": round(counts["lineage"] / counts["total"], 3) if counts["total"] else None,
            }
            for ch, counts in sorted(by_channel.items(), key=lambda x: -x[1]["total"])
        },
        "recent_failures": recent_failures[:10],
        "refresher": {
            "enabled": refresher_enabled,
            "running": refresher_running,
            "interval_hours": refresher_interval,
        },
    }
