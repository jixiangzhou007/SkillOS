"""File Ingest — convert any file to Markdown via MarkItDown.

Bridges the gap between local files and Skill Distiller's knowledge pipeline:
  PDF/Word/Excel/PPT/image/audio/HTML → MarkItDown → clean Markdown
  → feed into deep_digest / skill extraction / knowledge extraction.

Supports 30+ formats via Microsoft's MarkItDown (optional dependency).
Falls back gracefully to plain text reading for .txt/.md/.csv/.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

# Try importing MarkItDown — it's optional
try:
    from markitdown import MarkItDown as _MarkItDown
    _HAS_MARKITDOWN = True
except ImportError:
    _HAS_MARKITDOWN = False
    _MarkItDown = None


# ═══════════════════════════════════════════════════════════════
# File type detection
# ═══════════════════════════════════════════════════════════════

MARKITDOWN_FORMATS = {
    '.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
    '.html', '.htm', '.xml', '.epub', '.rtf', '.odt', '.ods', '.odp',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
    '.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac',
    '.zip', '.7z',
}

PLAIN_TEXT_FORMATS = {'.txt', '.md', '.csv', '.json', '.jsonl', '.yaml', '.yml', '.py', '.js', '.ts', '.log', '.env'}

ALL_SUPPORTED = MARKITDOWN_FORMATS | PLAIN_TEXT_FORMATS


def is_supported(filename: str) -> bool:
    """Check if a file format is supported."""
    ext = Path(filename).suffix.lower()
    return ext in ALL_SUPPORTED


def get_file_category(filename: str) -> str:
    """Get a human-readable category for a file."""
    ext = Path(filename).suffix.lower()
    if ext in ('.pdf',): return 'PDF'
    if ext in ('.docx', '.doc', '.odt', '.rtf'): return '文档'
    if ext in ('.pptx', '.ppt', '.odp'): return '演示文稿'
    if ext in ('.xlsx', '.xls', '.ods', '.csv'): return '表格'
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'): return '图片'
    if ext in ('.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac'): return '音频'
    if ext in ('.html', '.htm', '.xml'): return '网页'
    if ext in ('.epub',): return '电子书'
    if ext in ('.zip', '.7z'): return '压缩包'
    if ext in ('.txt', '.md'): return '文本'
    if ext in ('.json', '.jsonl', '.yaml', '.yml'): return '数据'
    return '文件'


# ═══════════════════════════════════════════════════════════════
# Conversion
# ═══════════════════════════════════════════════════════════════

def convert_to_markdown(
    filepath: str,
    original_filename: str = "",
    *,
    use_llm_for_images: bool = False,
) -> tuple[str, dict]:
    """Convert any supported file to Markdown text.

    Args:
        filepath: Path to the uploaded file (in temp directory).
        original_filename: Original filename (for format detection).
        use_llm_for_images: If True, use LLM to describe images (requires OpenAI client).

    Returns:
        (markdown_text, metadata_dict)
        metadata includes: source_format, file_size, method_used, conversion_time_s
    """
    import time
    t0 = time.time()

    filename = original_filename or Path(filepath).name
    ext = Path(filename).suffix.lower()
    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

    metadata = {
        "source_format": ext,
        "source_filename": filename,
        "file_size": file_size,
        "method_used": "unknown",
    }

    # ── Plain text formats: read directly ──
    if ext in PLAIN_TEXT_FORMATS:
        try:
            text = Path(filepath).read_text(encoding="utf-8")
            metadata["method_used"] = "direct_read"
            metadata["conversion_time_s"] = round(time.time() - t0, 2)
            return text, metadata
        except UnicodeDecodeError:
            # Fall through to MarkItDown if available
            if not _HAS_MARKITDOWN:
                try:
                    text = Path(filepath).read_text(encoding="latin-1")
                    metadata["method_used"] = "direct_read_latin1"
                    metadata["conversion_time_s"] = round(time.time() - t0, 2)
                    return text, metadata
                except Exception:
                    return f"[无法读取文件: {filename}]", metadata

    # ── MarkItDown for complex formats ──
    text = ""
    if _HAS_MARKITDOWN:
        try:
            md = _MarkItDown()
            result = md.convert(filepath)
            text = result.text_content or ""
            metadata["method_used"] = "markitdown"
            metadata["conversion_time_s"] = round(time.time() - t0, 2)
            if not text.strip():
                return f"[文件 {filename} 转换后无文本内容，可能是扫描件或纯图片]", metadata
            return text, metadata
        except Exception as e:
            _log.warning("MarkItDown conversion failed for %s: %s", filename, e)
            metadata["method_used"] = "markitdown_failed"
            metadata["error"] = str(e)

    # ── Fallback: can't handle this format ──
    if not _HAS_MARKITDOWN:
        return (
            f"[不支持的文件格式: {ext}]\n\n"
            "安装 MarkItDown 以支持 PDF/Word/Excel/PPT 等格式:\n"
            "  pip install markitdown[all]\n\n"
            f"文件名: {filename}\n"
            f"大小: {file_size:,} bytes",
            metadata
        )

    if not text or not text.strip():
        return f"[文件 {filename} 转换失败: 无文本内容]", metadata

    return text, metadata


# ═══════════════════════════════════════════════════════════════
# Full Pipeline: file → markdown → knowledge extraction
# ═══════════════════════════════════════════════════════════════

INGEST_CACHE_DIR = Path(__file__).parent / "data" / "ingest_cache"  # legacy path (migration only)


def _write_ingest_cache(cache_file: Path, file_hash: str, result: dict) -> dict:
    """Persist ingest result keyed by source file SHA256 (skip errors / cache hits)."""
    if result.get("error") or result.get("from_cache"):
        return result
    try:
        result["cached_hash"] = file_hash[:12]
        from skillos.knowledge.incremental_store import get_incremental_store
        get_incremental_store().put_file_ingest(file_hash, result)
    except Exception:
        _log.debug("Failed to write ingest cache for %s", file_hash[:12], exc_info=True)
    return result


def ingest_and_learn(
    filepath: str,
    original_filename: str,
    *,
    existing_skills: list[str] | None = None,
    llm_args: tuple | None = None,
) -> dict:
    """Full pipeline: convert file → extract knowledge or create skill.

    Returns a dict suitable for API response:
        {filename, file_category, markdown_length, conversion_metadata,
         digest_result (optional), skill_result (optional), error (optional)}
    """
    # SHA256 incremental cache — skip unchanged files (LLM Wiki inspired)
    from skillos.knowledge.incremental_store import get_incremental_store
    store = get_incremental_store()
    with open(filepath, "rb") as fh:
        file_hash = hashlib.sha256(fh.read()).hexdigest()
    cached = store.get_file_ingest(file_hash)
    if cached is not None:
        _log.info("Cache hit: %s (hash=%s)", original_filename, file_hash[:12])
        cached = dict(cached)
        cached["from_cache"] = True
        return cached

    # 1. Convert to Markdown
    md_text, conv_meta = convert_to_markdown(filepath, original_filename)

    if md_text.startswith("[不支持的") or md_text.startswith("[文件"):
        return {
            "filename": original_filename,
            "file_category": get_file_category(original_filename),
            "markdown_length": len(md_text),
            "conversion": conv_meta,
            "error": md_text,
        }

    result = {
        "filename": original_filename,
        "file_category": get_file_category(original_filename),
        "markdown_length": len(md_text),
        "conversion": conv_meta,
    }

    if len(md_text) < 200:
        result["note"] = "内容太短，跳过知识提取"
        return result

    # 2. Route through learning pipeline
    if existing_skills is None:
        from skillos.skills import skill_store
        existing_skills = [s for s in skill_store.list_skills()
                          if s not in ('brainstorming', 'skill-creator', 'deep-digest', 'cold-start-interview')]

    if llm_args is None:
        from skillos.config import get_config
        cfg = get_config()
        llm_args = (cfg.api_key, cfg.base_url, cfg.model, cfg.to_llm_args()[3])

    # 3. Try deep digest first (structured knowledge package)
    try:
        from skillos.knowledge.deep_digest import deep_digest, save_digest
        dd_result = deep_digest(
            md_text, f"file://{original_filename}",
            existing_skills=existing_skills,
            llm_args=llm_args,
        )
        if dd_result.glossary or dd_result.patterns or dd_result.sections:
            save_digest(dd_result)
            extracted_items: list = []
            # Also extract individual knowledge items to global KB
            try:
                from skillos.knowledge.extractor import extract_knowledge, save_knowledge
                extracted_items = extract_knowledge(md_text, f"file://{original_filename}")
                if extracted_items:
                    save_knowledge(extracted_items)
            except Exception:
                pass
            from skillos.knowledge.ingest_pipeline import finalize_ingest
            result = finalize_ingest(
                md_text,
                f"file://{original_filename}",
                source_title=dd_result.title,
                digest_result=dd_result,
                extractor_items=extracted_items,
                channel="file_ingest",
                payload=result,
            )
            result["digest"] = {
                "slug": dd_result.slug,
                "title": dd_result.title,
                "doc_type": dd_result.doc_type,
                "glossary_terms": len(dd_result.glossary),
                "patterns": len(dd_result.patterns),
                "sections": len(dd_result.sections),
                "cross_references": len(dd_result.cross_references),
                "elapsed_s": dd_result.elapsed_s,
            }
            return _write_ingest_cache(Path(), file_hash, result)
    except Exception as e:
        _log.warning("Deep digest failed for file %s: %s", original_filename, e)

    # 4. Fallback: flat knowledge extraction
    try:
        from skillos.knowledge import extractor as _ke
        ke_result = _ke.learn_knowledge(md_text, f"file://{original_filename}", llm_args)
        result["knowledge"] = {
            "extracted": ke_result.get("extracted", 0),
            "verified": ke_result.get("verified", 0),
            "needs_review": ke_result.get("needs_review", 0),
            "saved": ke_result.get("saved", 0),
        }
        if ke_result.get("lineage"):
            result["lineage"] = ke_result["lineage"]
        if ke_result.get("lineage_notice"):
            result["lineage_notice"] = ke_result["lineage_notice"]
        if ke_result.get("warnings"):
            result.setdefault("warnings", []).extend(ke_result["warnings"])
        if ke_result.get("needs_review", 0) > 0:
            result.setdefault("warnings", []).append(
                f"⚠ {ke_result['needs_review']} 条知识待人工复核"
            )
    except Exception as e:
        _log.warning("Knowledge extraction failed for file %s: %s", original_filename, e)
        result["note"] = f"知识提取失败: {e}"

    return _write_ingest_cache(Path(), file_hash, result)
