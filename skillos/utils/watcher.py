"""File System Watcher — auto-ingest files dropped into monitored folders.

LLM Wiki-inspired: watch a folder for new/modified files, auto-trigger
the ingestion pipeline (MarkItDown → Deep Digest → Knowledge Package).

Use: `skillos watch` starts the watcher. Files dropped into
  ~/.skillos/inbox/ are automatically ingested.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable

_log = logging.getLogger(__name__)

DEFAULT_WATCH_DIR = Path.home() / ".skillos" / "inbox"


def get_watch_dir() -> Path:
    """Get the monitored folder. Creates it if missing."""
    watch = DEFAULT_WATCH_DIR
    watch.mkdir(parents=True, exist_ok=True)
    return watch


def _file_signature(path: Path) -> tuple[int, int]:
    st = path.stat()
    return (st.st_mtime_ns, st.st_size)


class FileWatcher:
    """Polls a directory for new or modified files and triggers a callback."""

    def __init__(self, watch_dir: Path, callback: Callable[[Path], None], interval: float = 3.0):
        self.watch_dir = watch_dir
        self.callback = callback
        self.interval = interval
        self._known: dict[str, tuple[int, int]] = {}
        self._running = False
        self._thread: threading.Thread | None = None

    def _scan(self):
        """Scan for new or content-changed files."""
        current: dict[str, tuple[int, int]] = {}
        for p in self.watch_dir.iterdir():
            if not p.is_file() or p.name.startswith("."):
                continue
            sig = _file_signature(p)
            current[p.name] = sig
            prev = self._known.get(p.name)
            if prev is None:
                _log.info("New file detected: %s", p.name)
                try:
                    self.callback(p)
                except Exception as e:
                    _log.error("Callback failed for %s: %s", p.name, e)
            elif prev != sig:
                _log.info("File changed: %s", p.name)
                try:
                    self.callback(p)
                except Exception as e:
                    _log.error("Callback failed for %s: %s", p.name, e)
        self._known = current

    def start(self):
        """Start watching in a background thread."""
        if self._running:
            return
        self._running = True
        self._scan()  # Initial scan

        def _loop():
            while self._running:
                time.sleep(self.interval)
                self._scan()

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        _log.info("Watching %s (interval=%.1fs)", self.watch_dir, self.interval)

    def stop(self):
        """Stop watching."""
        self._running = False
        _log.info("Watcher stopped")


def _archive_watched_file(filepath: Path) -> None:
    """Move a processed inbox file aside so the watcher does not re-enqueue it."""
    archive = get_watch_dir() / ".processed"
    archive.mkdir(exist_ok=True)
    dest = archive / filepath.name
    if dest.exists():
        dest = archive / f"{filepath.stem}_{int(time.time())}{filepath.suffix}"
    filepath.rename(dest)


def ingest_callback(filepath: Path) -> dict:
    """Default callback: enqueue for serial processing (LLM Wiki queue pattern)."""
    try:
        from skillos.knowledge.ingestion_queue import enqueue
        enqueue("file", str(filepath), meta={"filename": filepath.name})
        _log.info("Enqueued file for ingestion: %s", filepath.name)
        _archive_watched_file(filepath)
        return {"enqueued": True, "filename": filepath.name}
    except Exception:
        from skillos.config import get_config
        from skillos.utils.file_ingest import ingest_and_learn
        cfg = get_config()
        result = ingest_and_learn(str(filepath), filepath.name, llm_args=cfg.to_llm_args())
        _archive_watched_file(filepath)
        return result


# Singleton watcher
_watcher: FileWatcher | None = None


def is_watching() -> bool:
    return bool(_watcher and _watcher._running)


def start_watching(watch_dir: Path | None = None, callback: Callable | None = None, interval: float | None = None):
    """Start the file watcher. Call once at app startup."""
    global _watcher
    if _watcher and _watcher._running:
        return
    poll = interval
    if poll is None:
        try:
            from skillos.config import get_config
            poll = get_config().watcher_poll_interval
        except Exception:
            poll = 3.0
    _watcher = FileWatcher(
        watch_dir or get_watch_dir(),
        callback or ingest_callback,
        interval=poll,
    )
    _watcher.start()


def stop_watching():
    global _watcher
    if _watcher:
        _watcher.stop()
