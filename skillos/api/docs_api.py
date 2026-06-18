"""Public documentation API (Sprint 7)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _docs_roots() -> list[Path]:
    """Candidate directories for markdown docs (repo, cwd, env, frontend bundle)."""
    roots: list[Path] = []
    env = os.getenv("SKILLOS_DOCS_DIR", "").strip()
    if env:
        roots.append(Path(env).expanduser().resolve())
    roots.extend([
        _PROJECT_ROOT / "docs",
        _PROJECT_ROOT / "frontend" / "docs",
        Path.cwd().resolve() / "docs",
        Path.cwd().resolve() / "frontend" / "docs",
    ])
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in roots:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _read_doc(*relative_paths: str) -> str:
    for root in _docs_roots():
        for rel in relative_paths:
            path = root / rel
            if path.is_file():
                return path.read_text(encoding="utf-8")
    raise HTTPException(
        status_code=404,
        detail=f"Document not found (tried: {', '.join(relative_paths)})",
    )


@router.get("/guide")
async def user_guide():
    """Return USER_GUIDE markdown for in-app docs site."""
    content = _read_doc("USER_GUIDE.md", "user_guide.md")
    return {"title": "SkillOS 用户指南", "format": "markdown", "content": content}


@router.get("/quickstart")
async def quickstart():
    content = _read_doc("sprint7/QUICKSTART.md", "quickstart.md")
    return {"title": "快速开始", "format": "markdown", "content": content}
