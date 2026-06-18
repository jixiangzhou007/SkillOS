"""Web fetch tool — read content from URLs for skill extraction and research."""

from __future__ import annotations

import logging
import re
import urllib.request
import urllib.error

_log = logging.getLogger(__name__)

TIMEOUT = 15
MAX_CONTENT_LENGTH = 8000  # keep responses manageable for LLM context


def fetch(url: str) -> str:
    """Fetch a URL and extract readable text content.

    Strips HTML tags, scripts, styles, and returns clean text.
    """
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()

            raw = resp.read()
            # Try to decode
            for enc in [charset, "utf-8", "gbk", "gb2312", "latin-1"]:
                try:
                    html = raw.decode(enc, errors="strict")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                html = raw.decode("utf-8", errors="ignore")

    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] Failed to fetch {url}"
    except urllib.error.URLError as e:
        return f"[Network Error] Could not reach {url}: {e.reason}"
    except Exception as e:
        return f"[Error] Failed to fetch {url}: {e}"

    return _extract_text(html, url)


def _extract_text(html: str, url: str) -> str:
    """Extract readable text from HTML."""
    # Remove scripts, styles, and head
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Replace block elements with newlines
    for tag in ['br', 'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr', 'section', 'article']:
        html = re.sub(rf'</?{tag}[^>]*>', '\n', html, flags=re.IGNORECASE)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Decode HTML entities
    import html as _html
    text = _html.unescape(text)

    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    # Truncate if too long
    if len(text) > MAX_CONTENT_LENGTH:
        text = text[:MAX_CONTENT_LENGTH] + f"\n\n... (truncated, original: {len(text)} chars)"

    if not text.strip():
        return f"[No readable content] The page at {url} appears to be empty or requires JavaScript."

    return f"[Content from {url}]\n\n{text}"


def get_tool_definition() -> dict:
    """OpenAI-compatible function definition for web fetch."""
    return {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch and read the content of a web page by URL. "
                "Use this when the user provides a link and wants you to "
                "read, summarize, or extract information from it. "
                "Returns the page's readable text content (up to 8000 chars)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch (e.g., https://example.com/article)",
                    },
                },
                "required": ["url"],
            },
        },
    }
