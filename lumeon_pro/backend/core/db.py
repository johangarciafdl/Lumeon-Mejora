from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DB_PATH = Path(__file__).resolve().parents[1] / "database.db"


class CompatRow(dict):
    """Dict row that also supports legacy numeric indexing."""
    def __getitem__(self, key: Any):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


_QMARK = re.compile(r"\?")


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
        return CompatRow(zip([d.name for d in self._cursor.description], row))

    def fetchall(self):
        columns = [d.name for d in self._cursor.description]
        return [CompatRow(zip(columns, row)) for row in self._cursor.fetchall()]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        raise RuntimeError("PostgreSQL no usa lastrowid; usa INSERT ... RETURNING id")


class PostgresConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()):
        cursor = self._conn.cursor()
        return PostgresCursor(cursor).execute(sql, params)

    def cursor(self):
        return PostgresCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _postgres_connection():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("DATABASE_URL está configurada pero falta psycopg") from exc
    url = os.getenv("DATABASE_URL", "").strip()
    return PostgresConnection(psycopg.connect(url, connect_timeout=10))


def get_db():
    """Use Supabase/PostgreSQL when DATABASE_URL exists; SQLite only for local fallback."""
    if os.getenv("DATABASE_URL", "").strip():
        return _postgres_connection()
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
