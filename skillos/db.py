"""Database migration — versioned schema management for SQLite.

All modules register their table definitions here. Migrations are
applied automatically on first access, in version order.
"""

import logging
import os
import sqlite3
import threading
from pathlib import Path

_log = logging.getLogger(__name__)


def get_db_dir() -> Path:
    """Database directory; override with ``SKILLOS_DATA_DIR``."""
    env = os.getenv("SKILLOS_DATA_DIR", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
    else:
        p = (Path(__file__).parent.parent / "data").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


DB_DIR = get_db_dir()

_local = threading.local()

# Migration registry: (version, description, sql)
MIGRATIONS: list[tuple[int, str, str]] = []


def register_migration(version: int, description: str, sql: str):
    """Register a migration. Lower versions run first."""
    MIGRATIONS.append((version, description, sql))
    MIGRATIONS.sort()


# ── Core migrations ───────────────────────────────────────────

register_migration(1, "skill_registry", """
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
    )
""")

register_migration(2, "users_and_tokens", """
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'member',
        email TEXT NOT NULL DEFAULT '',
        team TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at REAL NOT NULL DEFAULT 0.0,
        last_login REAL NOT NULL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS api_tokens (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        label TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL DEFAULT 0.0,
        last_used REAL NOT NULL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL DEFAULT '',
        username TEXT NOT NULL DEFAULT '',
        action TEXT NOT NULL DEFAULT '',
        target TEXT NOT NULL DEFAULT '',
        detail TEXT NOT NULL DEFAULT '',
        ip_address TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL DEFAULT 0.0
    )
""")

register_migration(3, "pricing_and_purchases", """
    CREATE TABLE IF NOT EXISTS pricing (
        skill_id TEXT PRIMARY KEY,
        model TEXT NOT NULL DEFAULT 'free',
        price REAL NOT NULL DEFAULT 0.0,
        trial_days INTEGER NOT NULL DEFAULT 0,
        created_at REAL NOT NULL DEFAULT 0.0,
        updated_at REAL NOT NULL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS purchases (
        purchase_id TEXT PRIMARY KEY,
        skill_id TEXT NOT NULL,
        buyer_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        model TEXT NOT NULL DEFAULT 'free',
        amount REAL NOT NULL DEFAULT 0.0,
        commission REAL NOT NULL DEFAULT 0.0,
        author_earnings REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at REAL NOT NULL DEFAULT 0.0,
        completed_at REAL NOT NULL DEFAULT 0.0,
        expires_at REAL NOT NULL DEFAULT 0.0
    )
""")

register_migration(4, "conversations", """
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
    CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(created_at)
""")

register_migration(5, "identity_tenants", """
    CREATE TABLE IF NOT EXISTS tenants (
        tenant_id TEXT PRIMARY KEY,
        tenant_type TEXT NOT NULL,
        owner_user_id TEXT NOT NULL DEFAULT '',
        org_id TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS organizations (
        org_id TEXT PRIMARY KEY,
        slug TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        plan TEXT NOT NULL DEFAULT 'team',
        created_at REAL NOT NULL DEFAULT 0.0
    );
    CREATE TABLE IF NOT EXISTS memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        org_id TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        dept_id TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL DEFAULT 0.0,
        UNIQUE(user_id, org_id)
    );
    CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id);
    CREATE INDEX IF NOT EXISTS idx_memberships_org ON memberships(org_id);
    CREATE TABLE IF NOT EXISTS skill_metadata (
        tenant_id TEXT NOT NULL,
        skill_slug TEXT NOT NULL,
        name TEXT NOT NULL,
        visibility TEXT NOT NULL DEFAULT 'private',
        creator_user_id TEXT NOT NULL DEFAULT '',
        dept_id TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL DEFAULT 0.0,
        updated_at REAL NOT NULL DEFAULT 0.0,
        PRIMARY KEY (tenant_id, skill_slug)
    );
    CREATE INDEX IF NOT EXISTS idx_skill_meta_tenant ON skill_metadata(tenant_id);
""")

register_migration(6, "user_workspaces", """
    CREATE TABLE IF NOT EXISTS user_workspaces (
        user_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        tenant_type TEXT NOT NULL DEFAULT 'personal',
        label TEXT NOT NULL DEFAULT '',
        org_id TEXT NOT NULL DEFAULT '',
        is_default INTEGER NOT NULL DEFAULT 0,
        created_at REAL NOT NULL DEFAULT 0.0,
        PRIMARY KEY (user_id, tenant_id)
    );
    CREATE INDEX IF NOT EXISTS idx_user_workspaces_user ON user_workspaces(user_id);
""")

register_migration(7, "skill_approval_status", """
    ALTER TABLE skill_metadata ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'draft';
    ALTER TABLE skill_metadata ADD COLUMN reviewed_by TEXT NOT NULL DEFAULT '';
    ALTER TABLE skill_metadata ADD COLUMN reviewed_at REAL NOT NULL DEFAULT 0.0;
    ALTER TABLE skill_metadata ADD COLUMN review_notes TEXT NOT NULL DEFAULT '';
""")

register_migration(8, "usage_events_and_byok", """
    CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        user_id TEXT NOT NULL DEFAULT '',
        event_type TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_usage_tenant_time ON usage_events(tenant_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_events(event_type);
    CREATE TABLE IF NOT EXISTS user_llm_keys (
        user_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL DEFAULT 'deepseek',
        api_key TEXT NOT NULL DEFAULT '',
        use_own_key INTEGER NOT NULL DEFAULT 0,
        updated_at REAL NOT NULL DEFAULT 0.0
    );
""")

register_migration(9, "departments_and_org_settings", """
    CREATE TABLE IF NOT EXISTS departments (
        dept_id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at REAL NOT NULL DEFAULT 0.0
    );
    CREATE INDEX IF NOT EXISTS idx_departments_org ON departments(org_id);
    CREATE TABLE IF NOT EXISTS org_settings (
        org_id TEXT PRIMARY KEY,
        max_skills INTEGER NOT NULL DEFAULT 9999,
        max_llm_monthly INTEGER NOT NULL DEFAULT 9999,
        updated_at REAL NOT NULL DEFAULT 0.0
    );
""")

register_migration(10, "dept_quotas", """
    CREATE TABLE IF NOT EXISTS dept_quotas (
        dept_id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        max_skills INTEGER NOT NULL DEFAULT 50,
        max_llm_monthly INTEGER NOT NULL DEFAULT 200,
        updated_at REAL NOT NULL DEFAULT 0.0
    );
    CREATE INDEX IF NOT EXISTS idx_dept_quotas_org ON dept_quotas(org_id);
""")

register_migration(11, "user_plans", """
    CREATE TABLE IF NOT EXISTS user_plans (
        user_id TEXT PRIMARY KEY,
        plan TEXT NOT NULL DEFAULT 'personal_free',
        expires_at REAL NOT NULL DEFAULT 0.0,
        updated_at REAL NOT NULL DEFAULT 0.0
    );
""")

register_migration(12, "purchases_payment_refs", """
    ALTER TABLE purchases ADD COLUMN payment_method TEXT NOT NULL DEFAULT '';
    ALTER TABLE purchases ADD COLUMN payment_ref TEXT NOT NULL DEFAULT '';
""")


# ── Migration runner ──────────────────────────────────────────

def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _apply_migration_sql(conn: sqlite3.Connection, sql: str) -> None:
    """Run migration SQL; skip ADD COLUMN when column already exists."""
    import re

    pending: list[str] = []
    for raw in sql.split(";"):
        stmt = raw.strip()
        if not stmt:
            continue
        m = re.match(
            r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)\s+(.+)",
            stmt,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            table, column, col_def = m.group(1), m.group(2), m.group(3).strip()
            if column in _table_columns(conn, table):
                _log.warning("Skip existing column %s.%s", table, column)
                continue
            pending.append(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        else:
            pending.append(stmt)

    for stmt in pending:
        conn.execute(stmt)


def get_conn(db_path: str = "skillhub.db") -> sqlite3.Connection:
    """Get a thread-local SQLite connection with migrations applied."""
    if not hasattr(_local, "conns"):
        _local.conns = {}

    db_dir = get_db_dir()
    cache_key = str(db_dir / db_path)
    if cache_key not in _local.conns:
        full_path = db_dir / db_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(full_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _run_migrations(conn, full_path)
        _local.conns[cache_key] = conn

    return _local.conns[cache_key]


def _run_migrations(conn: sqlite3.Connection, db_file: Path):
    """Apply pending migrations."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version INTEGER PRIMARY KEY,
            description TEXT,
            applied_at REAL NOT NULL
        )
    """)

    applied = {
        row[0] for row in
        conn.execute("SELECT version FROM _migrations").fetchall()
    }

    import time
    for version, description, sql in MIGRATIONS:
        if version not in applied:
            _log.info("Applying migration v%d: %s", version, description)
            try:
                _apply_migration_sql(conn, sql)
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    conn.rollback()
                    _log.warning("Migration v%d duplicate column (marking applied): %s", version, e)
                else:
                    raise
            conn.execute(
                "INSERT INTO _migrations (version, description, applied_at) VALUES (?, ?, ?)",
                (version, description, time.time())
            )
            conn.commit()
