"""Knowledge Refresher — auto-re-digest when source content changes.

Inspired by Crawl4AI's adaptive extraction: when a page layout changes,
re-extract. Here: when a source URL's content changes, re-digest and
update the knowledge package.

Also: confidence-based refresh — when knowledge confidence drops below
threshold, re-verify against source.
"""

import hashlib
import logging
import time
import threading
from pathlib import Path
from typing import Callable

_log = logging.getLogger(__name__)

# Legacy directory — migrated into data/incremental/ on first access
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "source_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def check_source_changed(url: str, content: str) -> bool:
    """Check if source content has changed since last digest."""
    from skillos.knowledge.incremental_store import get_incremental_store
    return get_incremental_store().check_source_changed(url, hash_content(content))


def mark_source_refreshed(url: str, content_hash: str = ""):
    """Update the source hash cache after a successful refresh."""
    from skillos.knowledge.incremental_store import get_incremental_store
    get_incremental_store().set_source_hash(url, content_hash or hash_content(""))


def refresh_if_changed(url: str, llm_args: tuple) -> dict | None:
    """If source content changed, re-digest and update knowledge package.

    Returns digest result dict if refreshed, None if unchanged.
    """
    from skillos.utils.web_fetch import fetch
    from skillos.knowledge.deep_digest import deep_digest, save_digest

    content = fetch(url)
    if not content or len(content) < 200:
        return None

    if not check_source_changed(url, content):
        _log.debug("Source unchanged: %s", url[:60])
        return None

    _log.info("Source changed — re-digesting: %s", url[:60])
    result = deep_digest(content, url, llm_args=llm_args)

    if result.glossary or result.patterns:
        save_digest(result)
        content_hash = hash_content(content)
        mark_source_refreshed(url, content_hash)
        from skillos.knowledge.ingest_pipeline import finalize_ingest
        payload = finalize_ingest(
            content,
            url,
            source_title=result.title,
            digest_result=result,
            channel="refresher",
            payload={
                "url": url, "title": result.title,
                "glossary": len(result.glossary), "patterns": len(result.patterns),
                "elapsed_s": result.elapsed_s,
            },
        )
        return payload

    return None


def check_stale_knowledge() -> list[str]:
    """Find knowledge items whose confidence has dropped below threshold.

    Returns list of source URLs that need re-verification.
    """
    from skillos.knowledge.extractor import load_all_knowledge

    items = load_all_knowledge()
    stale = []
    for item in items:
        if hasattr(item, 'invalid_at') and item.invalid_at > 0:
            continue  # Already invalidated
        if item.confidence < 0.3:
            stale.append(item.source_url)
    return list(set(stale))


# Periodic refresh scheduler
_refresh_thread: threading.Thread | None = None
_refresh_running = False


def start_periodic_refresh(interval_hours: float = 24.0):
    """Start periodic knowledge refresh in background."""
    global _refresh_thread, _refresh_running
    if _refresh_running:
        return

    _refresh_running = True

    def _loop():
        while _refresh_running:
            time.sleep(interval_hours * 3600)
            try:
                from skillos.config import get_config
                cfg = get_config()
                llm_args = cfg.to_llm_args()

                # Check stale knowledge
                stale_urls = check_stale_knowledge()
                for url in stale_urls[:5]:  # Limit per cycle
                    refresh_if_changed(url, llm_args)

                _log.info("Periodic refresh: checked %d stale sources", len(stale_urls))
            except Exception as e:
                _log.warning("Periodic refresh error: %s", e)

    _refresh_thread = threading.Thread(target=_loop, daemon=True)
    _refresh_thread.start()
    _log.info("Periodic knowledge refresh started (every %.1fh)", interval_hours)


def stop_periodic_refresh():
    global _refresh_running
    _refresh_running = False


def is_periodic_refresh_running() -> bool:
    return _refresh_running
