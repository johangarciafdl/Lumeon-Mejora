from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def record(
    conn,
    *,
    actor_id: int | None = None,
    action: str,
    entity: str | None = None,
    entity_id: str | int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append an operational audit event inside the caller's transaction."""
    payload = json.dumps(details or {}, ensure_ascii=False, default=str)
    conn.execute(
        "INSERT INTO audit_log(user_id,action,entity_type,entity_id,metadata,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (
            actor_id,
            action,
            entity,
            str(entity_id) if entity_id is not None else None,
            payload,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
