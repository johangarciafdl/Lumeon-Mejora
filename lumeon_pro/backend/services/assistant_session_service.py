from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_session(conn, session_id: str) -> dict:
    row = conn.execute(
        "SELECT session_id,pending_intent,pending_payload,updated_at FROM assistant_sessions WHERE session_id=?",
        (session_id,),
    ).fetchone()
    if row is None:
        return {"session_id": session_id, "pending_intent": None, "pending_payload": {}, "updated_at": _now()}
    payload = row["pending_payload"]
    if isinstance(payload, str):
        payload = json.loads(payload or "{}")
    return {"session_id": row["session_id"], "pending_intent": row["pending_intent"], "pending_payload": payload or {}, "updated_at": row["updated_at"]}


def save_session(conn, session_id: str, pending_intent: str | None, pending_payload: dict) -> None:
    payload = json.dumps(pending_payload, ensure_ascii=False)
    if isinstance(conn, sqlite3.Connection):
        conn.execute(
            "INSERT INTO assistant_sessions(session_id,pending_intent,pending_payload,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET pending_intent=excluded.pending_intent,pending_payload=excluded.pending_payload,updated_at=excluded.updated_at",
            (session_id, pending_intent, payload, _now()),
        )
    else:
        conn.execute(
            "INSERT INTO assistant_sessions(session_id,pending_intent,pending_payload,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET pending_intent=EXCLUDED.pending_intent,pending_payload=EXCLUDED.pending_payload,updated_at=EXCLUDED.updated_at",
            (session_id, pending_intent, payload, _now()),
        )
