from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _versions():
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)


def _is_postgres(conn) -> bool:
    return conn.__class__.__name__ == "PostgresConnection"


def _sqlite_sql(sql: str) -> str:
    sql = re.sub(r"\bBIGSERIAL\b", "INTEGER", sql, flags=re.I)
    sql = re.sub(r"\bBIGINT\b", "INTEGER", sql, flags=re.I)
    sql = re.sub(r"\bTIMESTAMPTZ\b", "TEXT", sql, flags=re.I)
    sql = re.sub(r"\bTIMESTAMP\b", "TEXT", sql, flags=re.I)
    sql = re.sub(r"\bDEFAULT\s+NOW\(\)", "DEFAULT CURRENT_TIMESTAMP", sql, flags=re.I)
    sql = re.sub(r"\bGENERATED\s+BY\s+DEFAULT\s+AS\s+IDENTITY\b", "", sql, flags=re.I)
    return sql


def _execute_script(conn, sql: str) -> None:
    if hasattr(conn, "executescript"):
        conn.executescript(sql)
        return
    conn._conn.execute(sql)


def ensure_tracking_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()


def apply_pending(conn) -> list[str]:
    ensure_tracking_table(conn)
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    postgres = _is_postgres(conn)
    completed: list[str] = []

    for path in _versions():
        if path.name in applied or path.name == "005_migration_runner.sql":
            continue

        # The two message-delivery migrations describe the same feature. 004 is
        # the canonical PostgreSQL version; 003 is retained as legacy history.
        if postgres and path.name == "003_message_deliveries.sql":
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (path.name,))
            conn.commit()
            completed.append(path.name)
            continue
        if not postgres and path.name in {"003_message_deliveries.sql", "004_message_deliveries.sql"}:
            continue

        sql = path.read_text(encoding="utf-8")
        if not postgres:
            sql = _sqlite_sql(sql)
        _execute_script(conn, sql)
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (path.name,))
        conn.commit()
        completed.append(path.name)

    return completed
