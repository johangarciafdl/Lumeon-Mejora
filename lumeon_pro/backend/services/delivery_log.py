from __future__ import annotations

import sqlite3


def ensure_delivery_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS message_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            provider TEXT NOT NULL,
            recipient TEXT NOT NULL,
            reference TEXT,
            status TEXT NOT NULL,
            provider_message_id TEXT,
            error TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sent_at TEXT
        )"""
    )


def record_delivery(conn: sqlite3.Connection, *, channel: str, provider: str, recipient: str, reference: str | None, status: str, provider_message_id: str | None = None, error: str | None = None) -> int:
    ensure_delivery_table(conn)
    cursor = conn.execute(
        """INSERT INTO message_deliveries
        (channel,provider,recipient,reference,status,provider_message_id,error,attempts,sent_at)
        VALUES (?,?,?,?,?,?,?,?,CASE WHEN ?='SENT' THEN CURRENT_TIMESTAMP ELSE NULL END)""",
        (channel, provider, recipient, reference, status, provider_message_id, error, 1, status),
    )
    return int(cursor.lastrowid)
