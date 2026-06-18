"""Disk cache for SkillsBench LLM responses (reduces benchmark variance & cost)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmarks" / "llm_cache"


def cache_enabled() -> bool:
    return os.getenv("SKILLSBENCH_LLM_CACHE", "1").lower() not in ("0", "false", "no")


def cache_key(*, model: str, system: str, user: str) -> str:
    payload = f"{model}\n---\n{system}\n---\n{user}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:40]


def get_cached_response(*, model: str, system: str, user: str) -> str | None:
    if not cache_enabled():
        return None
    path = CACHE_DIR / f"{cache_key(model=model, system=system, user=user)}.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def store_cached_response(*, model: str, system: str, user: str, text: str) -> None:
    if not cache_enabled():
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{cache_key(model=model, system=system, user=user)}.txt"
    path.write_text(text, encoding="utf-8")
