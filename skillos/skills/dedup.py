"""Similar-skill detection for org dedup hints (Sprint 4)."""

from __future__ import annotations

from skillos.skills.variants import _name_similarity


def _body_snippet(body: str, limit: int = 500) -> str:
    return " ".join(body.split())[:limit].lower()


def _body_overlap(a: str, b: str) -> float:
    wa = set(_body_snippet(a).split())
    wb = set(_body_snippet(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def find_similar_skills(
    name: str,
    body: str = "",
    *,
    tenant=None,
    name_threshold: float = 0.55,
    body_threshold: float = 0.35,
    limit: int = 5,
) -> list[dict]:
    """Return similar skills in the same tenant (name + body overlap)."""
    from skillos.skills.skill_store import list_skills, load_skill_raw, get_skill_body

    candidates: list[dict] = []
    for other in list_skills(tenant=tenant):
        if other == name:
            continue
        name_score = _name_similarity(name, other)
        try:
            raw = load_skill_raw(other, tenant=tenant)
            other_body = get_skill_body(raw.get("content") or raw.get("body", ""))
            if not other_body and "body" in raw:
                other_body = raw["body"]
        except Exception:
            other_body = ""
        body_score = _body_overlap(body, other_body) if body else 0.0
        score = max(name_score, body_score * 0.9)
        if name_score >= name_threshold or body_score >= body_threshold:
            reason = "name" if name_score >= name_threshold else "content"
            candidates.append({
                "name": other,
                "score": round(score, 3),
                "name_similarity": round(name_score, 3),
                "body_overlap": round(body_score, 3),
                "reason": reason,
            })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]
