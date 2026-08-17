from __future__ import annotations

from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _versions():
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)


def ensure_tracking_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()


def apply_pending(conn) -> list[str]:
    ensure_tracking_table(conn)
    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    completed: list[str] = []
    for path in _versions():
        if path.name in applied or path.name == "005_migration_runner.sql":
            continue
        sql = path.read_text(encoding="utf-8")
        conn.executescript(sql) if hasattr(conn, "executescript") else conn.execute(sql)
        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (path.name,))
        conn.commit()
        completed.append(path.name)
    return completed
