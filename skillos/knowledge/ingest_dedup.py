"""Ingest deduplication — skip re-processing unchanged URL content."""


from skillos.knowledge.refresher import hash_content, mark_source_refreshed


def should_skip_ingest(url: str, content: str) -> bool:
    """Return True if this URL was already ingested with the same content hash."""
    if not url or not content:
        return False
    from skillos.knowledge.incremental_store import get_incremental_store

    store = get_incremental_store()
    old = store.get_source_hash(url)
    if old is None:
        return False
    return old == hash_content(content)


def mark_ingest_complete(url: str, content: str) -> None:
    """Record successful ingest so identical content can be skipped later."""
    if url and content:
        mark_source_refreshed(url, hash_content(content))
