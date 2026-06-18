"""SkillHub Registry — SQLite-backed skill catalog for the marketplace.

Tables:
  - skill_registry: published skills with metadata, scores, review status
  - skill_versions: version history per skill
  - subscriptions: user→skill subscriptions with auto-update flag
  - review_queue: pending reviews with audit results

Zero extra dependencies — sqlite3 is Python stdlib.
"""


import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "skillhub.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_local = threading.local()

STATUSES = ("pending", "approved", "rejected", "archived")
CATEGORIES = ("automation", "development", "data-science", "writing", "design",
              "legal", "finance", "devops", "security", "other")


@dataclass
class HubSkill:
    """A skill published on SkillHub."""
    skill_id: str = ""           # uuid
    name: str = ""               # display name
    slug: str = ""               # unique kebab-case identifier
    author: str = ""             # publisher user id
    version: int = 1
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = "other"
    content: str = ""            # full SKILL.md content
    score: float = 0.0           # overall score (0-100)
    execution_score: float = 0.0 # fresh-agent test score
    audit_score: float = 0.0     # Auditor 8-dim score
    audit_json: str = ""         # full audit report JSON
    status: str = "pending"      # pending | approved | rejected | archived
    review_notes: str = ""
    downloads: int = 0
    subscriptions: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    published_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id, "name": self.name, "slug": self.slug,
            "author": self.author, "version": self.version,
            "description": self.description, "tags": self.tags,
            "category": self.category, "score": round(self.score, 1),
            "execution_score": round(self.execution_score, 1),
            "audit_score": round(self.audit_score, 1),
            "status": self.status, "review_notes": self.review_notes,
            "downloads": self.downloads, "subscriptions": self.subscriptions,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════
# Database init
# ═══════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    """Get thread-local connection via central db.py."""
    if not hasattr(_local, "conn") or _local.conn is None:
        from skillos.db import get_conn
        _local.conn = get_conn("skillhub.db")
        _local.conn.row_factory = sqlite3.Row
        _init_tables(_local.conn)
    return _local.conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS skill_registry (
            skill_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            author TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 1,
            description TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            category TEXT NOT NULL DEFAULT 'other',
            content TEXT NOT NULL DEFAULT '',
            score REAL NOT NULL DEFAULT 0.0,
            execution_score REAL NOT NULL DEFAULT 0.0,
            audit_score REAL NOT NULL DEFAULT 0.0,
            audit_json TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            review_notes TEXT NOT NULL DEFAULT '',
            downloads INTEGER NOT NULL DEFAULT 0,
            subscriptions INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL DEFAULT 0.0,
            updated_at REAL NOT NULL DEFAULT 0.0,
            published_at REAL NOT NULL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS skill_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id TEXT NOT NULL,
            version_num INTEGER NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            score REAL NOT NULL DEFAULT 0.0,
            audit_json TEXT NOT NULL DEFAULT '',
            changelog TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (skill_id) REFERENCES skill_registry(skill_id)
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            auto_update INTEGER NOT NULL DEFAULT 1,
            subscribed_at REAL NOT NULL DEFAULT 0.0,
            UNIQUE(user_id, skill_id)
        );

        CREATE INDEX IF NOT EXISTS idx_registry_status ON skill_registry(status);
        CREATE INDEX IF NOT EXISTS idx_registry_category ON skill_registry(category);
        CREATE INDEX IF NOT EXISTS idx_registry_score ON skill_registry(score DESC);
        CREATE INDEX IF NOT EXISTS idx_registry_author ON skill_registry(author);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
    """)
    conn.commit()


# ═══════════════════════════════════════════════════════════════
# CRUD: Skills
# ═══════════════════════════════════════════════════════════════

def publish_skill(
    name: str,
    content: str,
    *,
    author: str = "anonymous",
    description: str = "",
    tags: list[str] | None = None,
    category: str = "other",
) -> HubSkill:
    """Submit a skill to the registry. Status starts as 'pending'."""
    conn = _get_conn()
    now = time.time()
    sid = uuid.uuid4().hex[:12]
    slug = _slugify(name)

    # Check for duplicate slug
    existing = conn.execute(
        "SELECT skill_id FROM skill_registry WHERE slug = ? AND status != 'archived'",
        (slug,)
    ).fetchone()
    if existing:
        # Append random suffix to make unique
        slug = f"{slug}-{sid[:6]}"

    skill = HubSkill(
        skill_id=sid, name=name, slug=slug, author=author, version=1,
        description=description, tags=tags or [], category=category,
        content=content, status="pending", created_at=now, updated_at=now,
    )

    conn.execute("""
        INSERT INTO skill_registry
            (skill_id, name, slug, author, version, description, tags, category,
             content, score, execution_score, audit_score, audit_json,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sid, name, slug, author, 1, description,
        json.dumps(tags or [], ensure_ascii=False), category,
        content, 0.0, 0.0, 0.0, "", "pending", now, now,
    ))
    conn.commit()

    _log.info("Skill published: %s (slug=%s author=%s)", name, slug, author)
    return skill


def update_skill_score(
    skill_id: str,
    execution_score: float,
    audit_score: float,
    audit_json: str,
    version_num: int | None = None,
) -> HubSkill | None:
    """Update the score and audit results for a skill."""
    conn = _get_conn()
    now = time.time()
    overall = round(execution_score * 0.6 + audit_score * 0.4, 1)

    # Auto-gate based on score
    if overall >= 70:
        status = "approved"
        notes = f"自动通过 (综合评分 {overall})"
    elif overall >= 50:
        status = "pending"
        notes = f"待人工复审 (综合评分 {overall})"
    else:
        status = "rejected"
        notes = f"自动拒绝 (综合评分 {overall} < 50)。请根据审计建议修改后重新提交。"

    conn.execute("""
        UPDATE skill_registry
        SET score = ?, execution_score = ?, audit_score = ?, audit_json = ?,
            status = ?, review_notes = ?, updated_at = ?,
            published_at = CASE WHEN ? = 'approved' AND published_at = 0 THEN ? ELSE published_at END
        WHERE skill_id = ?
    """, (overall, execution_score, audit_score, audit_json,
          status, notes, now, status, now, skill_id))

    if version_num:
        conn.execute("""
            INSERT INTO skill_versions (skill_id, version_num, score, audit_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (skill_id, version_num, overall, audit_json, now))

    conn.commit()
    return get_skill(skill_id)


def get_skill(skill_id: str) -> HubSkill | None:
    """Get a single skill by ID."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM skill_registry WHERE skill_id = ?", (skill_id,)).fetchone()
    return _row_to_skill(row) if row else None


def get_skill_by_slug(slug: str) -> HubSkill | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM skill_registry WHERE slug = ?", (slug,)).fetchone()
    return _row_to_skill(row) if row else None


def list_skills(
    *,
    status: str = "approved",
    category: str = "",
    author: str = "",
    search: str = "",
    sort_by: str = "score",
    limit: int = 50,
    offset: int = 0,
) -> list[HubSkill]:
    """Search and list published skills."""
    conn = _get_conn()
    where = ["status = ?"]
    params = [status]

    if category:
        where.append("category = ?")
        params.append(category)
    if author:
        where.append("author = ?")
        params.append(author)
    if search:
        where.append("(name LIKE ? OR description LIKE ? OR tags LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    order = {"score": "score DESC", "newest": "created_at DESC", "popular": "downloads DESC"}.get(sort_by, "score DESC")

    rows = conn.execute(
        f"SELECT * FROM skill_registry WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    return [_row_to_skill(r) for r in rows]


def list_my_skills(author: str) -> list[HubSkill]:
    """List all skills by a specific author (any status)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM skill_registry WHERE author = ? ORDER BY updated_at DESC",
        (author,)
    ).fetchall()
    return [_row_to_skill(r) for r in rows]


def get_pending_reviews() -> list[HubSkill]:
    """Get skills awaiting manual review (score 50-69)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM skill_registry WHERE status = 'pending' AND score >= 50 ORDER BY created_at ASC"
    ).fetchall()
    return [_row_to_skill(r) for r in rows]


def review_skill(skill_id: str, approved: bool, notes: str = "") -> HubSkill | None:
    """Manual review: approve or reject a pending skill."""
    conn = _get_conn()
    status = "approved" if approved else "rejected"
    now = time.time()
    conn.execute(
        "UPDATE skill_registry SET status = ?, review_notes = ?, updated_at = ? WHERE skill_id = ?",
        (status, notes, now, skill_id)
    )
    conn.commit()
    return get_skill(skill_id)


def sync_version(skill_id: str, new_content: str, new_version: int) -> HubSkill | None:
    """Sync an updated version from the author. Re-triggers scoring."""
    conn = _get_conn()
    now = time.time()
    conn.execute(
        "UPDATE skill_registry SET content = ?, version = ?, score = 0, status = 'pending', updated_at = ? WHERE skill_id = ?",
        (new_content, new_version, now, skill_id)
    )
    conn.commit()
    _log.info("Skill synced: %s v%d — re-queued for scoring", skill_id, new_version)
    return get_skill(skill_id)


# ═══════════════════════════════════════════════════════════════
# Subscriptions
# ═══════════════════════════════════════════════════════════════

def subscribe(user_id: str, skill_id: str, auto_update: bool = True) -> bool:
    """Subscribe a user to a skill. Returns True if newly subscribed."""
    conn = _get_conn()
    now = time.time()
    existing = conn.execute(
        "SELECT id FROM subscriptions WHERE user_id = ? AND skill_id = ?",
        (user_id, skill_id)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE subscriptions SET auto_update = ?, subscribed_at = ? WHERE user_id = ? AND skill_id = ?",
            (1 if auto_update else 0, now, user_id, skill_id)
        )
        conn.commit()
        return False  # already subscribed
    conn.execute(
        "INSERT INTO subscriptions (user_id, skill_id, auto_update, subscribed_at) VALUES (?, ?, ?, ?)",
        (user_id, skill_id, 1 if auto_update else 0, now)
    )
    conn.execute(
        "UPDATE skill_registry SET subscriptions = subscriptions + 1 WHERE skill_id = ?",
        (skill_id,)
    )
    conn.commit()
    return True


def unsubscribe(user_id: str, skill_id: str) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM subscriptions WHERE user_id = ? AND skill_id = ?", (user_id, skill_id))
    conn.execute(
        "UPDATE skill_registry SET subscriptions = MAX(0, subscriptions - 1) WHERE skill_id = ?",
        (skill_id,)
    )
    conn.commit()
    return True


def get_subscriptions(user_id: str) -> list[str]:
    """Get list of skill_ids a user is subscribed to."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT skill_id FROM subscriptions WHERE user_id = ?", (user_id,)
    ).fetchall()
    return [r[0] for r in rows]


def is_subscribed(user_id: str, skill_id: str) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id FROM subscriptions WHERE user_id = ? AND skill_id = ?",
        (user_id, skill_id)
    ).fetchone()
    return row is not None


# ═══════════════════════════════════════════════════════════════
# Categories & Stats
# ═══════════════════════════════════════════════════════════════

def get_stats() -> dict:
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM skill_registry WHERE status = 'approved'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM skill_registry WHERE status = 'pending'").fetchone()[0]
    avg_score = conn.execute("SELECT AVG(score) FROM skill_registry WHERE status = 'approved'").fetchone()[0] or 0
    cat_counts = {}
    for cat in CATEGORIES:
        c = conn.execute(
            "SELECT COUNT(*) FROM skill_registry WHERE category = ? AND status = 'approved'", (cat,)
        ).fetchone()[0]
        if c: cat_counts[cat] = c
    return {
        "total": total, "pending_review": pending,
        "avg_score": round(avg_score, 1), "categories": cat_counts,
    }


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _row_to_skill(row: sqlite3.Row) -> HubSkill:
    return HubSkill(
        skill_id=row["skill_id"], name=row["name"], slug=row["slug"],
        author=row["author"], version=row["version"],
        description=row["description"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        category=row["category"], content=row["content"],
        score=row["score"], execution_score=row["execution_score"],
        audit_score=row["audit_score"], audit_json=row["audit_json"],
        status=row["status"], review_notes=row["review_notes"],
        downloads=row["downloads"], subscriptions=row["subscriptions"],
        created_at=row["created_at"], updated_at=row["updated_at"],
        published_at=(row["published_at"] if "published_at" in row.keys() else 0.0) or 0.0,
    )


def _slugify(name: str) -> str:
    import re
    slug = re.sub(r'[^\w一-鿿\-]+', '-', name.strip().lower(), flags=re.UNICODE)
    return re.sub(r'-+', '-', slug).strip('-')[:64] or "skill"
