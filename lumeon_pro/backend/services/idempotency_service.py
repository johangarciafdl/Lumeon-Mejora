from __future__ import annotations

import hashlib
import json
from typing import Any


def key_for(actor_id: int, session_id: str, operation: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    raw = f"{actor_id}:{session_id}:{operation}:{canonical}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def claim(conn, key: str, operation: str) -> bool:
    """Atomically claim an operation on SQLite or PostgreSQL."""
    row = conn.execute(
        "INSERT INTO idempotency_keys(key, operation) VALUES(?, ?) "
        "ON CONFLICT(key) DO NOTHING RETURNING key",
        (key, operation),
    ).fetchone()
    return row is not None
