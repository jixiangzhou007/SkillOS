"""WeChat Official Account Watcher — auto-crawl articles + periodic refresh.

Usage:
  account_watcher.add_account("腾讯云开发者")  → fetches recent articles
  account_watcher.start_scheduler()           → checks every N hours for new articles
"""

import hashlib
import json
import logging
import re
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable

_log = logging.getLogger(__name__)

WATCH_DIR = Path(__file__).parent.parent.parent / "data" / "watched_accounts"
WATCH_DIR.mkdir(parents=True, exist_ok=True)


def _cdp_eval(target_id: str, js: str) -> str:
    """Execute JS in CDP browser tab."""
    data = js.encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:3456/eval?target={target_id}",
        data=data, method="POST",
        headers={"Content-Type": "text/plain"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        result = json.loads(r.read().decode())
        return result.get("value", "")


def _cdp_new_tab(url: str) -> str:
    """Open a new CDP tab, return targetId."""
    data = url.encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:3456/new", data=data, method="POST",
        headers={"Content-Type": "text/plain"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode()).get("targetId", "")


def _cdp_close(target_id: str):
    try:
        urllib.request.urlopen(f"http://localhost:3456/close?target={target_id}", timeout=5)
    except Exception:
        pass


def fetch_account_articles(account_name: str, max_articles: int = 10) -> list[dict]:
    """Search for a WeChat account and fetch its recent article list.

    Uses Sogou WeChat search via CDP browser.
    Returns list of {title, url, summary, publish_time}.
    """
    search_url = f"https://weixin.sogou.com/weixin?type=1&query={urllib.request.quote(account_name)}"
    target_id = _cdp_new_tab(search_url)
    if not target_id:
        return []

    time.sleep(2)

    articles = []
    try:
        # Extract article list from Sogou search results
        js = """
(() => {
  const items = document.querySelectorAll('.news-list li, .txt-box');
  const results = [];
  items.forEach(function(item) {
    const link = item.querySelector('a');
    const title = item.querySelector('h3, .txt-box h3')?.textContent?.trim() || '';
    const summary = item.querySelector('.txt-info, p')?.textContent?.trim() || '';
    const time = item.querySelector('.s-p, .time')?.textContent?.trim() || '';
    if (link && link.href && title) {
      results.push({ title, url: link.href, summary, time });
    }
  });
  return JSON.stringify(results.slice(0, 15));
})()
"""
        raw = _cdp_eval(target_id, js)
        articles = json.loads(raw) if raw else []
    except Exception as e:
        _log.warning("Sogou search failed: %s", e)
    finally:
        _cdp_close(target_id)

    return articles[:max_articles]


def is_new_article(account_name: str, article_url: str) -> bool:
    """Check if this article has been seen before."""
    from skillos.knowledge.incremental_store import get_incremental_store
    return not get_incremental_store().is_account_url_seen(account_name, article_url)


def mark_seen(account_name: str, article_url: str):
    """Mark an article as seen."""
    from skillos.knowledge.incremental_store import get_incremental_store
    get_incremental_store().mark_account_url_seen(account_name, article_url)


def add_account(account_name: str) -> dict:
    """Add a WeChat account to watch. Fetches current articles.

    Returns {account, articles_found, new_articles, ingested}.
    """
    articles = fetch_account_articles(account_name)
    new_count = 0
    ingested = 0

    for article in articles:
        url = article.get("url", "")
        if not url or not is_new_article(account_name, url):
            continue
        new_count += 1
        mark_seen(account_name, url)

        # Auto-ingest via enqueue (LLM Wiki queue pattern) or direct pipeline
        try:
            from skillos.knowledge.ingestion_queue import enqueue
            enqueue("url", url, meta={"account": account_name, "source": "wechat_mp"})
            _log.info("Enqueued WeChat article for ingestion: %s (%s)", url[:60], account_name)
            ingested += 1
        except Exception:
            # Fallback: direct processing
            try:
                from skillos.utils.wechat_fetch import fetch as wechat_fetch
                from skillos.knowledge.deep_digest import deep_digest, save_digest
                from skillos.knowledge.extractor import extract_knowledge, save_knowledge
                from skillos.config import get_config

                content = wechat_fetch(url)
                if content and len(content) > 200:
                    from skillos.knowledge.ingest_dedup import mark_ingest_complete, should_skip_ingest
                    if should_skip_ingest(url, content):
                        _log.debug("Account watcher skip unchanged: %s", url[:60])
                        continue
                    cfg = get_config()
                    dd = deep_digest(content, url, llm_args=cfg.to_llm_args())
                    extracted_items: list = []
                    if dd.glossary or dd.patterns:
                        save_digest(dd)
                    extracted_items = extract_knowledge(content, url)
                    if extracted_items:
                        save_knowledge(extracted_items)
                    from skillos.knowledge.ingest_pipeline import finalize_ingest, format_lineage_notice
                    fin = finalize_ingest(
                        content, url, source_title=dd.title,
                        digest_result=dd if (dd.glossary or dd.patterns or dd.sections) else None,
                        extractor_items=extracted_items, channel="account_watcher",
                    )
                    lineage = fin.get("lineage") or {}
                    if not lineage.get("lineage_applied"):
                        _log.warning("Account watcher lineage not applied for %s: %s",
                                    url[:80], format_lineage_notice(lineage))
                    ingested += 1
            except Exception as e:
                _log.warning("Failed to ingest %s: %s", url, e)

    return {
        "account": account_name,
        "articles_found": len(articles),
        "new_articles": new_count,
        "ingested": ingested,
    }


def check_all_accounts() -> dict:
    """Check all watched accounts for new articles."""
    from skillos.knowledge.incremental_store import get_incremental_store
    results = {}
    for acct in get_incremental_store().list_accounts():
        results[acct["name"]] = add_account(acct["name"])
    for f in WATCH_DIR.glob("*_seen.json"):
        legacy_name = f.stem.replace("_seen", "")
        if legacy_name not in results:
            results[legacy_name] = add_account(legacy_name)
    return results


# ── Scheduler ───────────────────────────────────────────────

_scheduler_running = False
_scheduler_thread = None


def start_scheduler(interval_hours: float = 6.0, callback: Callable | None = None):
    """Start periodic checking for new articles from watched accounts."""
    global _scheduler_running, _scheduler_thread
    if _scheduler_running:
        return

    _scheduler_running = True

    def _loop():
        while _scheduler_running:
            time.sleep(interval_hours * 3600)
            try:
                results = check_all_accounts()
                total_new = sum(r.get("new_articles", 0) for r in results.values())
                if total_new > 0:
                    _log.info("Account watcher: %d new articles ingested", total_new)
                    if callback:
                        callback(results)
            except Exception as e:
                _log.warning("Scheduler error: %s", e)

    _scheduler_thread = threading.Thread(target=_loop, daemon=True)
    _scheduler_thread.start()
    _log.info("Account watcher started (every %.1fh)", interval_hours)


def stop_scheduler():
    global _scheduler_running
    _scheduler_running = False


def get_login_qrcode() -> str | None:
    """Get WeChat MP login QR code image URL from CDP browser."""
    try:
        req = urllib.request.Request("http://localhost:3456/new",
                                     data="https://mp.weixin.qq.com/".encode(), method="POST",
                                     headers={"Content-Type": "text/plain"})
        tid = json.loads(urllib.request.urlopen(req, timeout=15).read())["targetId"]
        time.sleep(2)
        # Extract QR code image src
        js = "document.querySelector('img[src*=\"qrcode\"], .login__type__container__scan__qrcode')?.src || ''"
        req2 = urllib.request.Request(f"http://localhost:3456/eval?target={tid}",
                                      data=js.encode(), method="POST",
                                      headers={"Content-Type": "text/plain"})
        src = json.loads(urllib.request.urlopen(req2, timeout=10).read().decode()).get("value", "")
        if src:
            return f"https://mp.weixin.qq.com{src}" if src.startswith("/") else src
    except Exception as e:
        _log.warning("QR code fetch failed: %s", e)
    return None


def is_wechat_logged_in() -> bool:
    """Check if CDP browser has WeChat login session."""
    try:
        req = urllib.request.Request("http://localhost:3456/new",
                                     data="https://mp.weixin.qq.com/".encode(), method="POST",
                                     headers={"Content-Type": "text/plain"})
        tid = json.loads(urllib.request.urlopen(req, timeout=15).read())["targetId"]
        time.sleep(2)
        js = "document.querySelector('.login__type__container__scan__qrcode') ? 'no' : 'yes'"
        req2 = urllib.request.Request(f"http://localhost:3456/eval?target={tid}",
                                      data=js.encode(), method="POST",
                                      headers={"Content-Type": "text/plain"})
        result = json.loads(urllib.request.urlopen(req2, timeout=10).read().decode()).get("value", "no")
        try: urllib.request.urlopen(f"http://localhost:3456/close?target={tid}", timeout=3)
        except: pass
        return result == "yes"
    except Exception:
        return False


def _safe_name(name: str) -> str:
    return re.sub(r'[^\w一-鿿]', '_', name)[:50]
