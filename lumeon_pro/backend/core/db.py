from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parents[1] / "database.db"
_QMARK = re.compile(r"\?")


class CompatRow(dict):
    def __getitem__(self, key: Any):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql: str, params=()):
        self._cursor.execute(_QMARK.sub("%s", sql), params or ())
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return CompatRow(zip([d.name if hasattr(d, "name") else d[0] for d in self._cursor.description], row))

    def fetchall(self):
        if self._cursor.description is None:
            return []
        columns = [d.name if hasattr(d, "name") else d[0] for d in self._cursor.description]
        return [CompatRow(zip(columns, row)) for row in self._cursor.fetchall()]

    @property
    def rowcount(self):
        return self._cursor.rowcount


class PostgresConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()):
        return PostgresCursor(self._conn.cursor()).execute(sql, params)

    def cursor(self):
        return PostgresCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _postgres_connection(url: str):
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError("DATABASE_URL PostgreSQL está configurada pero falta psycopg2-binary") from exc

    kwargs = {"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10"))}
    if os.getenv("DB_SSLMODE"):
        kwargs["sslmode"] = os.getenv("DB_SSLMODE").strip()
    kwargs["application_name"] = os.getenv("DB_APPLICATION_NAME", "lumeon-pro")
    return PostgresConnection(psycopg2.connect(url, **kwargs))


def get_db():
    """Use PostgreSQL/Supabase when DATABASE_URL is configured; keep SQLite as local fallback."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        if url.startswith(("sqlite://", "sqlite3://")):
            path = url.split("://", 1)[1] or ":memory:"
            if path == "/:memory:":
                path = ":memory:"
            conn = sqlite3.connect(path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 30000")
            return conn
        if not url.startswith(("postgresql://", "postgres://")):
            raise RuntimeError("DATABASE_URL debe usar sqlite://, postgresql:// o postgres://")
        return _postgres_connection(url)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


@contextmanager
def transaction() -> Iterator:
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
