from __future__ import annotations

import sqlite3

import pytest

from services.sale_service import SaleError, create_sale


def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE productos (
        id INTEGER PRIMARY KEY,
        referencia TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        precio_compra REAL NOT NULL DEFAULT 0,
        precio_venta REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura TEXT NOT NULL,
        idempotency_key TEXT,
        cliente_id INTEGER,
        cliente_nombre TEXT,
        cliente_email TEXT,
        cliente_telefono TEXT,
        fecha TEXT,
        forma_pago TEXT,
        subtotal REAL,
        total REAL,
        ganancia REAL,
        estado TEXT,
        notas TEXT,
        usuario_id INTEGER
    );
    CREATE TABLE venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto_id INTEGER,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio_compra REAL,
        precio_venta REAL,
        subtotal REAL,
        ganancia REAL
    );
    CREATE TABLE auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id INTEGER,
        action TEXT,
        entity TEXT,
        entity_id INTEGER,
        details TEXT,
        created_at TEXT
    );
    """)
    conn.execute("INSERT INTO productos VALUES (1,'P-1','Producto',10,25,5)")
    conn.commit()
    return conn


def test_sale_uses_database_price_and_decrements_stock():
    conn = db()
    sale_id = create_sale(conn, data={"cliente_id": 1, "cliente_nombre": "Cliente", "items":[{"referencia":"P-1","cantidad":2,"precio_venta":9999,"precio_compra":9999}]}, user_id=7)
    conn.commit()
    sale = conn.execute("SELECT subtotal FROM ventas WHERE id=?", (sale_id,)).fetchone()
    stock = conn.execute("SELECT stock FROM productos WHERE referencia='P-1'").fetchone()[0]
    assert sale["subtotal"] == 50
    assert stock == 3


def test_sale_rejects_insufficient_stock_without_partial_decrement():
    conn = db()
    with pytest.raises(SaleError):
        create_sale(conn, data={"cliente_id": 1, "items":[{"referencia":"P-1","cantidad":6}]}, user_id=7)
    assert conn.execute("SELECT stock FROM productos WHERE referencia='P-1'").fetchone()[0] == 5
    assert conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 0


def test_same_idempotency_key_returns_same_sale():
    conn = db()
    payload = {"cliente_id":1,"items":[{"referencia":"P-1","cantidad":1}],"idempotency_key":"abc-123"}
    first = create_sale(conn, data=payload, user_id=7)
    conn.commit()
    second = create_sale(conn, data=payload, user_id=7)
    assert first == second
    assert conn.execute("SELECT stock FROM productos WHERE referencia='P-1'").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 1
