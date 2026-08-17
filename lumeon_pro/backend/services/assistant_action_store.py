from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import uuid


TTL_MINUTES = 10


def create_pending(conn, *, user_id: int, intent: str, payload: dict) -> str:
    action_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO assistant_pending_actions
           (id,user_id,intent,payload,created_at,expires_at)
           VALUES (?,?,?,?,?,?)""",
        (action_id, user_id, intent, json.dumps(payload, ensure_ascii=False),
         now.isoformat(), (now + timedelta(minutes=TTL_MINUTES)).isoformat()),
    )
    return action_id


def consume_pending(conn, *, user_id: int, action_id: str):
    row = conn.execute(
        "SELECT id,intent,payload,expires_at FROM assistant_pending_actions "
        "WHERE id=? AND user_id=?",
        (action_id, user_id),
    ).fetchone()
    if not row:
        return None
    expires_at = datetime.fromisoformat(str(row["expires_at"]))
    if expires_at < datetime.now(timezone.utc):
        conn.execute("DELETE FROM assistant_pending_actions WHERE id=?", (action_id,))
        return None
    conn.execute("DELETE FROM assistant_pending_actions WHERE id=?", (action_id,))
    return str(row["intent"]), json.loads(str(row["payload"]))
