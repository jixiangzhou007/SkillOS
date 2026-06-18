"""Marketplace (SkillHub) endpoints — publish, search, subscribe, scoring.

Wired to real marketplace modules from Phase 3.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from skillos.identity.middleware import AuthContext, get_optional_auth, require_auth

router = APIRouter()


def _marketplace_readonly() -> bool:
    import os
    return os.getenv("SKILLHUB_READONLY", "true").lower() in ("1", "true", "yes")


class PublishRequest(BaseModel):
    name: str
    content: str
    description: str = ""
    category: str = "other"
    tags: list[str] = []
    author: str = "anonymous"


@router.get("/stats")
async def marketplace_stats():
    """Get marketplace statistics."""
    from skillos.marketplace.registry import get_stats
    return get_stats()


@router.get("/catalog")
async def public_catalog(q: str = "", category: str = "", sort: str = "score", limit: int = 50):
    """Read-only public skill catalog (no UGC publish in Sprint 9)."""
    from collections import Counter
    from skillos.marketplace.registry import list_skills

    readonly = _marketplace_readonly()
    all_approved = list_skills(status="approved", sort_by=sort)
    cat_counts = Counter(s.category or "other" for s in all_approved)
    categories = [
        {"name": name, "count": count}
        for name, count in sorted(cat_counts.items(), key=lambda x: (-x[1], x[0]))
    ]
    skills = list_skills(status="approved", category=category, search=q, sort_by=sort)
    items = []
    for s in skills[: max(1, min(limit, 100))]:
        d = s.to_dict()
        d.pop("content", None)
        d["read_only"] = readonly
        items.append(d)
    return {
        "read_only": readonly,
        "ugc_publish": not readonly,
        "total": len(skills),
        "categories": categories,
        "skills": items,
    }


@router.get("/search")
async def search_skills(q: str = "", category: str = "", sort: str = "score", author: str = ""):
    """Search published skills."""
    from skillos.marketplace.registry import list_skills
    skills = list_skills(status="approved", category=category, search=q, sort_by=sort, author=author)
    return {"total": len(skills), "skills": [s.to_dict() for s in skills]}


@router.post("/publish")
async def publish_skill(req: PublishRequest, auth: AuthContext | None = Depends(get_optional_auth)):
    """Submit a skill to the marketplace. Disabled when SKILLHUB_READONLY=true."""
    if _marketplace_readonly():
        if not auth or auth.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="公共市场当前为只读目录，暂不支持 UGC 发布。",
            )
    from skillos.config import get_config
    from skillos.marketplace.scorer import publish_and_score

    cfg = get_config()
    llm_args = cfg.to_llm_args()

    try:
        result = publish_and_score(
            name=req.name, content=req.content, llm_args=llm_args,
            author=req.author, description=req.description,
            tags=req.tags, category=req.category,
        )
        return {"published": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skill/{skill_id}")
async def get_skill(skill_id: str):
    """Get a published skill by ID or slug."""
    from skillos.marketplace.registry import get_skill, get_skill_by_slug
    skill = get_skill(skill_id) or get_skill_by_slug(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {**skill.to_dict(), "content": skill.content}


@router.post("/subscribe")
async def subscribe(skill_id: str, user_id: str = "anonymous", auto_update: bool = True):
    """Subscribe to a skill."""
    from skillos.marketplace.registry import subscribe
    new_sub = subscribe(user_id, skill_id, auto_update)
    return {"subscribed": True, "new": new_sub, "skill_id": skill_id}


@router.post("/unsubscribe")
async def unsubscribe(skill_id: str, user_id: str = "anonymous"):
    """Unsubscribe from a skill."""
    from skillos.marketplace.registry import unsubscribe
    unsubscribe(user_id, skill_id)
    return {"unsubscribed": True}


@router.get("/pending-reviews")
async def pending_reviews():
    """Get skills awaiting manual review (score 50-69)."""
    from skillos.marketplace.registry import get_pending_reviews
    pending = get_pending_reviews()
    return {"pending": [s.to_dict() for s in pending], "count": len(pending)}


@router.post("/review")
async def review_skill(skill_id: str, approved: bool, notes: str = ""):
    """Approve or reject a pending skill."""
    from skillos.marketplace.registry import review_skill
    skill = review_skill(skill_id, approved, notes)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"reviewed": True, "status": skill.status, "skill": skill.to_dict()}


@router.get("/check-updates")
async def check_updates(skills: str = "[]"):
    """Check which subscribed skills have newer versions."""
    import json
    from skillos.marketplace.registry import get_skill
    try:
        client_skills = json.loads(skills)
        updates = []
        for cs in client_skills:
            s = get_skill(cs.get("skill_id", ""))
            if s and s.version > cs.get("version", 0):
                updates.append({"skill_id": cs["skill_id"], "name": s.name,
                               "current_version": cs["version"], "latest_version": s.version})
        return {"updates_available": len(updates), "updates": updates}
    except json.JSONDecodeError:
        return {"updates_available": 0, "updates": []}


@router.get("/revenue/author")
async def author_revenue(author_id: str):
    """Get revenue dashboard for an author."""
    from skillos.marketplace.payments import get_author_revenue
    return get_author_revenue(author_id)


@router.get("/pricing/get")
async def pricing_get(skill_id: str):
    """Get pricing tier for a marketplace skill."""
    from skillos.marketplace.payments import get_price, format_price
    tier = get_price(skill_id)
    return {
        "skill_id": skill_id,
        "model": tier.model.value,
        "price": tier.price,
        "trial_days": tier.trial_days,
        "formatted": format_price(tier.price),
    }


class PricingSetRequest(BaseModel):
    skill_id: str
    model: str = "free"
    price: float = 0.0
    trial_days: int = 0


@router.post("/pricing/set")
async def pricing_set(req: PricingSetRequest, auth: AuthContext | None = Depends(get_optional_auth)):
    """Set pricing for a marketplace skill."""
    if _marketplace_readonly() and (not auth or auth.role != "admin"):
        raise HTTPException(
            status_code=403,
            detail="只读市场暂不支持修改定价",
        )
    from skillos.marketplace.payments import set_price, format_price
    tier = set_price(req.skill_id, req.model, req.price, req.trial_days)
    return {
        "pricing": {
            "skill_id": tier.skill_id,
            "model": tier.model.value,
            "price": tier.price,
            "formatted": format_price(tier.price),
        }
    }


@router.get("/recommendations")
async def recommend_skills(limit: int = 6, auth: AuthContext | None = Depends(get_optional_auth)):
    """Recommend catalog skills (v0): top scored, excluding tenant-owned/similar names."""
    from skillos.marketplace.registry import list_skills as list_market
    from skillos.skills.skill_store import list_skills as list_tenant
    from skillos.skills.variants import _name_similarity

    approved = list_market(status="approved", sort_by="score")
    owned: set[str] = set()
    if auth:
        try:
            owned = set(list_tenant(tenant=auth.tenant_context()))
        except Exception:
            owned = set()

    recs: list[dict] = []
    cap = max(1, min(limit, 20))
    for skill in approved:
        if skill.name in owned:
            continue
        if any(_name_similarity(skill.name, o) >= 0.55 for o in owned):
            continue
        d = skill.to_dict()
        d.pop("content", None)
        if skill.score >= 70:
            d["recommend_reason"] = "高分精选"
        elif skill.category and skill.category != "other":
            d["recommend_reason"] = "同类目"
        else:
            d["recommend_reason"] = "热门"
        recs.append(d)
        if len(recs) >= cap:
            break

    return {"total": len(recs), "recommendations": recs}


@router.get("/revenue/platform")
async def platform_revenue():
    """Get platform-wide revenue dashboard (admin)."""
    from skillos.marketplace.payments import get_platform_revenue
    return get_platform_revenue()
