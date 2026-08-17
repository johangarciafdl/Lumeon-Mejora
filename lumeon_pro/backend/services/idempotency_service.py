from __future__ import annotations

import hashlib
import json
import sqlite3


def key_for(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def already_processed(conn: sqlite3.Connection, key: str) -> bool:
    row = conn.execute("SELECT 1 FROM idempotency_keys WHERE key=?", (key,)).fetchone()
    return row is not None


def remember(conn: sqlite3.Connection, key: str, operation: str) -> None:
    conn.execute(
        "INSERT INTO idempotency_keys(key,operation) VALUES(?,?)",
        (key, operation),
    )
