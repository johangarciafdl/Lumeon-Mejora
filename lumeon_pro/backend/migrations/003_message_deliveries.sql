-- Additive migration for Supabase/PostgreSQL.
-- Run after the existing Lumeon schema migrations.
CREATE TABLE IF NOT EXISTS message_deliveries (
    id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT REFERENCES ventas(id) ON DELETE SET NULL,
    channel VARCHAR(30) NOT NULL,
    provider VARCHAR(60) NOT NULL,
    recipient VARCHAR(160) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    provider_message_id VARCHAR(255),
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    UNIQUE (venta_id, channel, recipient)
);

CREATE INDEX IF NOT EXISTS idx_message_deliveries_venta ON message_deliveries(venta_id);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_status ON message_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_message_deliveries_created_at ON message_deliveries(created_at);
