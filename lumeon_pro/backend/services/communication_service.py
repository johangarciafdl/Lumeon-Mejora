from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    status: str
    provider_message_id: str | None = None
    error: str | None = None


def ensure_delivery_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS message_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            channel TEXT NOT NULL,
            provider TEXT NOT NULL,
            recipient TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            provider_message_id TEXT,
            error TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            sent_at TEXT,
            UNIQUE(venta_id, channel, recipient)
        )
    """)


def record_attempt(conn, *, venta_id: int, channel: str, provider: str, recipient: str, result: DeliveryResult) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO message_deliveries
          (venta_id,channel,provider,recipient,status,provider_message_id,error,attempts,created_at,sent_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(venta_id,channel,recipient) DO UPDATE SET
          status=excluded.status,
          provider_message_id=excluded.provider_message_id,
          error=excluded.error,
          attempts=message_deliveries.attempts+1,
          sent_at=CASE WHEN excluded.status='SENT' THEN excluded.sent_at ELSE message_deliveries.sent_at END
    """, (venta_id, channel, provider, recipient, result.status, result.provider_message_id,
          result.error, 1, now, now if result.status == "SENT" else None))


def can_retry(conn, *, venta_id: int, channel: str, recipient: str, max_attempts: int = 5) -> bool:
    row = conn.execute(
        "SELECT status, attempts FROM message_deliveries WHERE venta_id=? AND channel=? AND recipient=?",
        (venta_id, channel, recipient),
    ).fetchone()
    if row is None:
        return True
    return row["status"] != "SENT" and int(row["attempts"]) < max_attempts
