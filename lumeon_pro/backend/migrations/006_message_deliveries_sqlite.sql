-- SQLite equivalent of the canonical PostgreSQL message delivery schema.
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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    UNIQUE (venta_id, channel, recipient)
);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_sale ON message_deliveries(venta_id);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_status ON message_deliveries(status);
