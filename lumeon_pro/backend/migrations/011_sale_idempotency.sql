ALTER TABLE ventas ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ventas_idempotency_key
ON ventas(idempotency_key)
WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';
