from __future__ import annotations

import sqlite3

from services.invoice_delivery_service import can_send_invoice


def db(status="Pendiente"):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE ventas (id INTEGER PRIMARY KEY, estado TEXT, cliente_telefono TEXT);
    CREATE TABLE invoice_deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT, venta_id INTEGER, channel TEXT, status TEXT, attempts INTEGER DEFAULT 0);
    """)
    conn.execute("INSERT INTO ventas VALUES (1, ?, '+573000000000')", (status,))
    conn.commit()
    return conn


def test_cancelled_sale_cannot_send():
    conn = db("Cancelada")
    allowed, reason = can_send_invoice(conn, 1, "whatsapp")
    assert allowed is False
    assert reason


def test_returned_sale_cannot_send():
    conn = db("Devuelta")
    allowed, reason = can_send_invoice(conn, 1, "whatsapp")
    assert allowed is False
    assert reason


def test_pending_sale_with_phone_can_send():
    conn = db("Pendiente")
    allowed, reason = can_send_invoice(conn, 1, "whatsapp")
    assert allowed is True
    assert reason is None
