"""Database migration idempotency tests."""


import sqlite3


def test_migration_v12_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLOS_DATA_DIR", str(tmp_path / "data"))
    import skillos.db as db_mod

    db_mod._local.conns = {}

    conn = db_mod.get_conn("test_migrate.db")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS purchases (
            purchase_id TEXT PRIMARY KEY,
            payment_method TEXT NOT NULL DEFAULT ''
        )"""
    )
    conn.commit()
    conn.close()
    db_mod._local.conns = {}

    conn2 = db_mod.get_conn("test_migrate.db")
    cols = {row[1] for row in conn2.execute("PRAGMA table_info(purchases)").fetchall()}
    assert "payment_method" in cols
    assert "payment_ref" in cols
    applied = {row[0] for row in conn2.execute("SELECT version FROM _migrations").fetchall()}
    assert 12 in applied
