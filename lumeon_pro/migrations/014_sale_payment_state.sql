-- Payment summary fields used by the sales management API/UI.
ALTER TABLE ventas ADD COLUMN total_abonado NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE ventas ADD COLUMN saldo_pendiente NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE ventas ADD COLUMN estado_pago TEXT NOT NULL DEFAULT 'Pendiente';

UPDATE ventas
SET total_abonado = CASE WHEN estado = 'Pagado' THEN total ELSE 0 END,
    saldo_pendiente = CASE WHEN estado = 'Pagado' THEN 0 ELSE total END,
    estado_pago = CASE
        WHEN estado = 'Pagado' THEN 'Pagado'
        WHEN estado = 'Cancelado' THEN 'Cancelado'
        ELSE 'Pendiente'
    END;
