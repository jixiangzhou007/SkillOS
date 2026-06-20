"""Per-skill knowledge base — file-based, keyword matching, zero downloads."""


import json
import logging
import re
from pathlib import Path

_log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def kb_dir(skill_name: str) -> Path:
    return SKILLS_DIR / _safe(skill_name) / "kb"


def add_document(skill_name: str, source: str, content: str) -> int:
    if not content or not content.strip():
        return 0
    chunks = _chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
    d = kb_dir(skill_name)
    d.mkdir(parents=True, exist_ok=True)
    idx = _load_index(skill_name)
    for chunk_text in chunks:
        cid = len(idx) + 1
        (d / f"c_{cid:04d}.txt").write_text(chunk_text, encoding="utf-8")
        idx.append({"id": cid, "source": source, "chunk": chunk_text[:200], "keywords": _kw(chunk_text)})
    _save_index(skill_name, idx)
    return len(chunks)


def search(skill_name: str, query: str, top_k: int = 5,
           state_context: str = "", alpha: float = 0.5) -> list[str]:
    """Search skill KB with optional state-grounded dual-signal scoring.

    SGDR-inspired: retrieval score = α × task_relevance + (1-α) × state_relevance.

    Args:
        skill_name: which skill's KB to search
        query: the user's task/goal
        top_k: max results
        state_context: current page/state description (e.g., "on login page, form visible")
        alpha: weight for task relevance vs state relevance (default 0.5)
    """
    idx = _load_index(skill_name)
    if not idx:
        return []
    qkw = set(_kw(query))
    skw = set(_kw(state_context)) if state_context else set()

    if not qkw and not skw:
        return []

    # Dual-signal scoring
    scored = []
    for e in idx:
        ekw = set(e.get("keywords", []))
        task_score = len(qkw & ekw) / max(len(qkw), 1) if qkw else 0.0
        state_score = len(skw & ekw) / max(len(skw), 1) if skw else 0.0
        combined = alpha * task_score + (1 - alpha) * state_score
        scored.append((combined, e))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    d = kb_dir(skill_name)
    for score, entry in scored[:top_k]:
        if score > 0:
            f = d / f"c_{entry['id']:04d}.txt"
            if f.exists():
                results.append(f.read_text(encoding="utf-8"))
    return results


def search_high_level(skill_name: str, query: str, top_k: int = 3, graph_traversal_depth: int = 2) -> list[str]:
    """LightRAG-inspired high-level retrieval: traverse knowledge graph for abstract themes.

    Unlike low-level search (keyword/embedding match on chunks), this walks the
    knowledge graph from matching nodes outward, aggregating connected concepts.
    This catches cross-document patterns that keyword matching misses.

    Use this for questions like "how do these concepts relate?" or "what are the
    broader themes?", not for "what is X?".
    """
    idx = _load_index(skill_name)
    if not idx:
        return []

    # Low-level first: find seed nodes
    qkw = set(_kw(query))
    scored = []
    for e in idx:
        ekw = set(e.get("keywords", []))
        score = len(qkw & ekw) / max(len(qkw), 1) if qkw else 0
        if score > 0:
            scored.append((score, e))

    if not scored:
        return []

    scored.sort(key=lambda x: x[0], reverse=True)

    # Graph traversal: from seed nodes, walk outward
    try:
        from skillos.knowledge.graph import get_graph
        g = get_graph()
    except Exception:
        # Fallback: return top low-level results
        d = kb_dir(skill_name)
        results = []
        for score, entry in scored[:top_k]:
            f = d / f"c_{entry['id']:04d}.txt"
            if f.exists():
                results.append(f.read_text(encoding="utf-8"))
        return results

    # Walk from seed concepts
    seed_concepts = [s[1].get("source", "") for s in scored[:3]]
    expanded = set()
    for seed in seed_concepts:
        node = g.find_node(seed) or g.find_node(seed[:40])
        if node:
            neighbors = g.get_neighbors(node.id)
            for neighbor, _edge in neighbors[:graph_traversal_depth * 3]:
                expanded.add(f"{neighbor.name}: {neighbor.description[:200]}")

    # Combine low-level results with graph-expanded context
    d = kb_dir(skill_name)
    results = []
    for score, entry in scored[:top_k]:
        f = d / f"c_{entry['id']:04d}.txt"
        if f.exists():
            results.append(f.read_text(encoding="utf-8"))

    if expanded:
        results.append("\n## 图谱扩展上下文 (LightRAG high-level)\n" + "\n".join(
            f"- {e}" for e in list(expanded)[:10]
        ))

    return results


def get_all_chunks(skill_name: str) -> str:
    idx = _load_index(skill_name)
    if not idx:
        return ""
    d = kb_dir(skill_name)
    parts = [(d / f"c_{e['id']:04d}.txt").read_text(encoding="utf-8") for e in idx if (d / f"c_{e['id']:04d}.txt").exists()]
    return "\n\n---\n\n".join(parts)


def list_sources(skill_name: str) -> list[str]:
    return list({e["source"] for e in _load_index(skill_name)})


def clear_kb(skill_name: str) -> None:
    d = kb_dir(skill_name)
    if d.exists():
        import shutil; shutil.rmtree(str(d))


def kb_size(skill_name: str) -> int:
    return len(_load_index(skill_name))


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', name)[:64]


def _kw(text: str) -> list[str]:
    cn = re.findall(r'[一-鿿]{2,4}', text)
    en = re.findall(r'[a-zA-Z]{3,}', text)
    return list(dict.fromkeys(cn + [w.lower() for w in en]))[:30]


def _load_index(skill_name: str) -> list[dict]:
    f = kb_dir(skill_name) / "index.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_index(skill_name: str, idx: list[dict]) -> None:
    d = kb_dir(skill_name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end]
        if end < len(text):
            tail = chunk[-100:]
            for sep in ["。", "！", "？", ".", "!", "?", "\n\n", "\n"]:
                idx = tail.rfind(sep)
                if idx > 0:
                    end = start + len(chunk) - 100 + idx + len(sep)
                    chunk = text[start:end]; break
        chunks.append(chunk.strip())
        start = end - overlap if end < len(text) else end
        if start >= len(text): break
    return chunks
