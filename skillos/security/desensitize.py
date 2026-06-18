"""LLM input desensitization (Sprint 7 — v1 rules)."""


import re

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.I), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"\b1[3-9]\d{9}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b\d{17}[\dXx]\b"), "[REDACTED_ID]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?i)(password|passwd|secret|api[_-]?key)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
]


def desensitize_text(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern, repl in _RULES:
        out = pattern.sub(repl, out)
    return out


def desensitize_messages(messages: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for msg in messages:
        m = dict(msg)
        content = m.get("content")
        if isinstance(content, str):
            m["content"] = desensitize_text(content)
        cleaned.append(m)
    return cleaned
