"""Unified incremental cache — file SHA256, URL content hash, account seen URLs.

Consolidates:
  - skillos/utils/data/ingest_cache/
  - data/source_cache/
  - data/watched_accounts/*_seen.json
"""


import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

INCREMENTAL_DIR = Path(__file__).parent.parent.parent / "data" / "incremental"
LEGACY_INGEST_CACHE = Path(__file__).parent.parent / "utils" / "data" / "ingest_cache"
LEGACY_SOURCE_CACHE = Path(__file__).parent.parent.parent / "data" / "source_cache"
LEGACY_WATCH_DIR = Path(__file__).parent.parent.parent / "data" / "watched_accounts"


def _url_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _safe_account_name(name: str) -> str:
    return re.sub(r"[^\w一-鿿]", "_", name)[:50]


class IncrementalStore:
    def __init__(self, root: Path):
        self.root = root
        self.files_dir = root / "files"
        self.index_path = root / "index.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"files": {}, "sources": {}, "accounts": {}, "migrated": False}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"files": {}, "sources": {}, "accounts": {}, "migrated": False}

    def _save_index(self, doc: dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_migrated(self) -> None:
        doc = self._load_index()
        if doc.get("migrated"):
            return
        migrated_any = False

        if LEGACY_INGEST_CACHE.exists():
            for fp in LEGACY_INGEST_CACHE.glob("*.json"):
                key = fp.stem
                dest = self.files_dir / f"{key}.json"
                if not dest.exists():
                    dest.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
                doc.setdefault("files", {})[key] = {"updated_at": fp.stat().st_mtime}
                migrated_any = True

        if LEGACY_SOURCE_CACHE.exists():
            for fp in LEGACY_SOURCE_CACHE.glob("*.hash"):
                key = fp.stem
                doc.setdefault("sources", {})[key] = {
                    "content_hash": fp.read_text(encoding="utf-8").strip(),
                    "updated_at": fp.stat().st_mtime,
                }
                migrated_any = True

        if LEGACY_WATCH_DIR.exists():
            for fp in LEGACY_WATCH_DIR.glob("*_seen.json"):
                name = fp.stem.replace("_seen", "")
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                except Exception:
                    continue
                doc.setdefault("accounts", {})[_safe_account_name(name)] = {
                    "display_name": name,
                    "urls": data.get("urls", []),
                    "last_check": data.get("last_check", 0),
                    "interval_hours": data.get("interval_hours", 6),
                    "active": data.get("active", False),
                }
                migrated_any = True

        doc["migrated"] = True
        self._save_index(doc)
        if migrated_any:
            _log.info("IncrementalStore migrated legacy caches into %s", self.root)

    # ── File ingest (SHA256) ──────────────────────────────────

    def get_file_ingest(self, file_hash: str) -> dict | None:
        key = file_hash[:16]
        path = self.files_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def put_file_ingest(self, file_hash: str, result: dict) -> None:
        key = file_hash[:16]
        path = self.files_dir / f"{key}.json"
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        doc = self._load_index()
        doc.setdefault("files", {})[key] = {"updated_at": time.time(), "hash_prefix": key}
        self._save_index(doc)

    # ── URL source content hash ───────────────────────────────

    def get_source_hash(self, url: str) -> str | None:
        key = _url_key(url)
        doc = self._load_index()
        entry = doc.get("sources", {}).get(key)
        if not entry:
            return None
        return entry.get("content_hash")

    def set_source_hash(self, url: str, content_hash: str) -> None:
        key = _url_key(url)
        doc = self._load_index()
        doc.setdefault("sources", {})[key] = {
            "url": url,
            "content_hash": content_hash,
            "updated_at": time.time(),
        }
        self._save_index(doc)

    def check_source_changed(self, url: str, content_hash: str) -> bool:
        """Return True if content hash differs from last recorded value."""
        old = self.get_source_hash(url)
        if old is None:
            self.set_source_hash(url, content_hash)
            return False
        if old != content_hash:
            self.set_source_hash(url, content_hash)
            return True
        return False

    # ── Account seen URLs ─────────────────────────────────────

    def _account_key(self, account_name: str) -> str:
        return _safe_account_name(account_name)

    def _get_account_entry(self, account_name: str) -> dict:
        doc = self._load_index()
        key = self._account_key(account_name)
        accounts = doc.setdefault("accounts", {})
        if key not in accounts:
            accounts[key] = {
                "display_name": account_name,
                "urls": [],
                "last_check": 0,
                "interval_hours": 6,
                "active": False,
            }
            self._save_index(doc)
        return accounts[key]

    def is_account_url_seen(self, account_name: str, article_url: str) -> bool:
        doc = self._load_index()
        entry = doc.get("accounts", {}).get(self._account_key(account_name))
        if not entry:
            return False
        return article_url in entry.get("urls", [])

    def mark_account_url_seen(self, account_name: str, article_url: str) -> None:
        doc = self._load_index()
        key = self._account_key(account_name)
        entry = doc.setdefault("accounts", {}).setdefault(key, {
            "display_name": account_name,
            "urls": [],
            "last_check": 0,
            "interval_hours": 6,
            "active": False,
        })
        if article_url not in entry["urls"]:
            entry["urls"].append(article_url)
        entry["last_check"] = time.time()
        self._save_index(doc)
        self._sync_legacy_account_file(account_name, entry)

    def update_account_meta(self, account_name: str, **fields: Any) -> dict:
        doc = self._load_index()
        key = self._account_key(account_name)
        entry = doc.setdefault("accounts", {}).setdefault(key, {
            "display_name": account_name,
            "urls": [],
            "last_check": 0,
            "interval_hours": 6,
            "active": False,
        })
        entry.update({k: v for k, v in fields.items() if v is not None})
        self._save_index(doc)
        self._sync_legacy_account_file(account_name, entry)
        return entry

    def list_accounts(self) -> list[dict]:
        doc = self._load_index()
        results = []
        for key, entry in doc.get("accounts", {}).items():
            results.append({
                "name": entry.get("display_name", key),
                "articles_seen": len(entry.get("urls", [])),
                "last_check": entry.get("last_check", 0),
                "interval_hours": entry.get("interval_hours", 6),
                "active": entry.get("active", False),
            })
        return sorted(results, key=lambda x: x["name"])

    def list_active_account_names(self) -> list[str]:
        return [a["name"] for a in self.list_accounts() if a.get("active")]

    def _sync_legacy_account_file(self, account_name: str, entry: dict) -> None:
        """Keep data/watched_accounts/*_seen.json for backward-compatible API reads."""
        LEGACY_WATCH_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = LEGACY_WATCH_DIR / f"{_safe_account_name(account_name)}_seen.json"
        payload = {
            "urls": entry.get("urls", []),
            "last_check": entry.get("last_check", 0),
            "interval_hours": entry.get("interval_hours", 6),
            "active": entry.get("active", False),
        }
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


_store: IncrementalStore | None = None


def get_incremental_store(root: Path | None = None) -> IncrementalStore:
    global _store
    if root is not None:
        return IncrementalStore(root)
    if _store is None:
        _store = IncrementalStore(INCREMENTAL_DIR)
        _store.ensure_migrated()
    return _store


def reset_incremental_store() -> None:
    global _store
    _store = None
