import os

from core.db import get_db


def test_sqlite_memory_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    conn = get_db()
    try:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO t (name) VALUES (?)", ("ok",))
        row = conn.execute("SELECT name FROM t").fetchone()
        assert row["name"] == "ok"
    finally:
        conn.close()


def test_empty_url_uses_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    conn = get_db()
    try:
        assert conn.__class__.__module__ == "sqlite3"
    finally:
        conn.close()
