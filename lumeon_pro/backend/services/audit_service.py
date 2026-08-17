from __future__ import annotations

import json
from datetime import datetime, timezone


def record(conn, *, actor_id=None, action: str, entity: str, entity_id=None, details: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO audit_logs(actor_id,action,entity,entity_id,details,created_at) VALUES(?,?,?,?,?,?)",
        (actor_id, action, entity, str(entity_id) if entity_id is not None else None, json.dumps(details or {}, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
    )
