from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    status: str
    provider_message_id: str | None = None
    error: str | None = None


def record_attempt(conn, *, venta_id: int, channel: str, provider: str, recipient: str, result: DeliveryResult) -> None:
    now = datetime.now(timezone.utc)
    existing = conn.execute(
        "SELECT id, attempts FROM invoice_deliveries WHERE venta_id=? AND channel=? AND recipient=? ORDER BY id DESC LIMIT 1",
        (venta_id, channel, recipient),
    ).fetchone()
    attempts = int(existing["attempts"] or 0) + 1 if existing else 1
    if existing:
        conn.execute(
            """UPDATE invoice_deliveries
               SET provider=?, status=?, attempts=?, error=?, created_at=?
             WHERE id=?""",
            (provider, result.status, attempts, result.error, now, existing["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO invoice_deliveries
               (venta_id, channel, provider, recipient, status, attempts, error, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (venta_id, channel, provider, recipient, result.status, attempts, result.error, now),
        )


def can_retry(conn, *, venta_id: int, channel: str, recipient: str, max_attempts: int = 5) -> bool:
    row = conn.execute(
        "SELECT status, attempts FROM invoice_deliveries WHERE venta_id=? AND channel=? AND recipient=? ORDER BY id DESC LIMIT 1",
        (venta_id, channel, recipient),
    ).fetchone()
    if row is None:
        return True
    return str(row["status"]).upper() != "SENT" and int(row["attempts"] or 0) < max_attempts
