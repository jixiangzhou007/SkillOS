"""Web search tool for LLM to look up information online."""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse

_log = logging.getLogger(__name__)


def search(query: str, max_results: int = 5) -> str:
    """Search the web and return results as formatted text."""
    try:
        results = _duckduckgo_search(query, max_results)
        if results:
            return _format_results(results)
    except Exception as exc:
        _log.warning("Search failed: %s", exc)

    return f"No results found for: {query}"


def _duckduckgo_search(query: str, max_results: int = 5) -> list[dict]:
    """Search using Bing (works in China, no API key needed)."""
    import re
    url = f"https://cn.bing.com/search?q={urllib.parse.quote(query)}&count={max_results}"

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    results = []
    # Bing result blocks: <li class="b_algo">
    blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL)
    for block in blocks[:max_results]:
        link_match = re.search(r'<a[^>]*href="(https?://[^"]*)"[^>]*>(.*?)</a>', block, re.DOTALL)
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
        if link_match:
            url = link_match.group(1)
            title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip() if snippet_match else ""
            results.append({"title": title, "url": url, "snippet": snippet})

    return results


def _format_results(results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:200]}")
        lines.append("")
    return "\n".join(lines)


def get_tool_definition() -> dict:
    """Return OpenAI-compatible function definition."""
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet for information. Use this when the user "
                "asks about current events, wants to reference online content, "
                "or needs information you don't have. Search in Chinese or English."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language",
                    },
                },
                "required": ["query"],
            },
        },
    }
