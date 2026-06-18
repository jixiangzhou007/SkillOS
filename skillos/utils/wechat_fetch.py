"""WeChat / anti-crawl URL fetcher — uses CDP browser to bypass restrictions.

Platforms like WeChat public articles (mp.weixin.qq.com) block regular HTTP
requests with anti-crawling measures. CDP browser access bypasses this because
it uses a real browser with proper JavaScript execution and headers.

Also works for other platforms that are known to block static fetching:
  - mp.weixin.qq.com (WeChat articles)
  - xiaohongshu.com (RED)
  - weibo.com (Weibo)
  - zhuanlan.zhihu.com (Zhihu columns, some articles)

Fallback: if CDP proxy isn't running, tries a best-effort HTTP fetch with
search-engine User-Agent. This is less reliable but works for some URLs.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
import urllib.error
from typing import Optional

_log = logging.getLogger(__name__)

CDP_PROXY = "http://localhost:3456"
TIMEOUT = 20

# Platforms that need CDP
CDP_REQUIRED_DOMAINS = [
    "mp.weixin.qq.com",
    "xiaohongshu.com", "xhslink.com",
    "weibo.com", "m.weibo.cn",
]


def needs_cdp(url: str) -> bool:
    """Check if this URL likely needs CDP browser access."""
    for domain in CDP_REQUIRED_DOMAINS:
        if domain in url:
            return True
    return False


def _cdp_available() -> bool:
    """Check if CDP proxy is running."""
    try:
        req = urllib.request.Request(f"{CDP_PROXY}/targets")
        with urllib.request.urlopen(req, timeout=2) as resp:
            json.loads(resp.read().decode())
        return True
    except Exception:
        return False


def _cdp_fetch(url: str) -> str:
    """Fetch a URL using CDP browser. Opens a new tab, extracts content, closes tab."""
    # Open new tab
    try:
        data = url.encode("utf-8")
        req = urllib.request.Request(
            f"{CDP_PROXY}/new",
            data=data, method="POST",
            headers={"Content-Type": "text/plain"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
        target_id = result.get("targetId", "")
        if not target_id:
            return ""
    except Exception as e:
        _log.warning("CDP new tab failed: %s", e)
        return ""

    # Wait for page to load
    time.sleep(2)

    # Extract content
    try:
        js = """
(() => {
  // Try multiple selectors for different platforms
  const title = document.querySelector('#activity-name')?.textContent?.trim()
             || document.querySelector('h1')?.textContent?.trim()
             || document.title || '';
  const author = document.querySelector('#js_name')?.textContent?.trim()
              || document.querySelector('.author')?.textContent?.trim()
              || '';
  const body = document.querySelector('#js_content')?.innerText?.trim()
            || document.querySelector('.rich_media_content')?.innerText?.trim()
            || document.querySelector('article')?.innerText?.trim()
            || document.body?.innerText?.trim()
            || '';
  return JSON.stringify({ title, author, content: body });
})()
"""
        req = urllib.request.Request(
            f"{CDP_PROXY}/eval?target={target_id}",
            data=js.encode("utf-8"), method="POST",
            headers={"Content-Type": "text/plain"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())

        content_json = result.get("value", "{}")
        try:
            data = json.loads(content_json) if isinstance(content_json, str) else content_json
            title = data.get("title", "")
            author = data.get("author", "")
            body = data.get("content", "")

            lines = []
            if title:
                lines.append(f"# {title}")
            if author:
                lines.append(f"作者: {author}")
            lines.append("")
            lines.append(body)
            return "\n".join(lines)
        except (json.JSONDecodeError, TypeError):
            return str(content_json)[:8000]
    except Exception as e:
        _log.warning("CDP eval failed: %s", e)
        return ""
    finally:
        # Always close the tab
        try:
            urllib.request.urlopen(
                f"{CDP_PROXY}/close?target={target_id}", timeout=3
            )
        except Exception:
            pass


def _http_fetch(url: str) -> str:
    """Best-effort HTTP fetch with search-engine UA (fallback)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com/",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        return _extract_text(html)
    except Exception as e:
        _log.warning("HTTP fetch failed: %s", e)
        return f"[无法获取: {url}]"


def _extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    # Remove scripts, styles, comments
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    # Simple tag stripping
    text = re.sub(r'<[^>]+>', '\n', html)
    # Clean whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()[:8000]


def fetch(url: str) -> str:
    """Fetch URL content. Uses CDP browser for WeChat/anti-crawl platforms,
    falls back to HTTP for normal URLs.

    Returns the extracted text content.
    """
    url = url.strip()

    # Determine fetch strategy
    if needs_cdp(url):
        if _cdp_available():
            _log.info("CDP fetch: %s", url[:80])
            content = _cdp_fetch(url)
            if content and len(content) > 100:
                return content[:8000]
            _log.warning("CDP fetch returned short content, trying HTTP fallback")
        else:
            _log.info("CDP not available for %s, using HTTP fallback", url[:80])

    # Default: HTTP fetch
    return _http_fetch(url)


def fetch_with_metadata(url: str) -> dict:
    """Fetch URL and return {content, method_used, url, length}."""
    content = fetch(url)
    method = "cdp" if (needs_cdp(url) and _cdp_available()) else "http"
    return {
        "url": url,
        "content": content,
        "method_used": method,
        "length": len(content),
    }
