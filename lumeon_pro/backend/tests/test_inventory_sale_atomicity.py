import pytest

from core.db import get_db
from services.inventory_service import InventoryError, reserve_items
from services.sale_service import SaleError, create_sale


def _conn(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    conn = get_db()
    conn.executescript("""
        CREATE TABLE productos (id INTEGER PRIMARY KEY, referencia TEXT UNIQUE, stock INTEGER NOT NULL);
        CREATE TABLE ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_factura TEXT UNIQUE, cliente_id INTEGER,
          cliente_nombre TEXT, cliente_email TEXT, cliente_telefono TEXT, fecha TEXT, forma_pago TEXT,
          subtotal REAL, total REAL, ganancia REAL, estado TEXT, notas TEXT, usuario_id INTEGER);
        CREATE TABLE venta_items (id INTEGER PRIMARY KEY AUTOINCREMENT, venta_id INTEGER, producto_id INTEGER,
          referencia TEXT, nombre TEXT, cantidad INTEGER, precio_compra REAL, precio_venta REAL,
          subtotal REAL, ganancia REAL);
        INSERT INTO productos(referencia, stock) VALUES ('P1', 2);
    """)
    conn.commit()
    return conn


def test_reservation_prevents_overselling(monkeypatch, tmp_path):
    conn = _conn(monkeypatch, tmp_path)
    try:
        reserve_items(conn, [{"referencia": "P1", "cantidad": 2}])
        with pytest.raises(InventoryError):
            reserve_items(conn, [{"referencia": "P1", "cantidad": 1}])
    finally:
        conn.close()


def test_failed_sale_rolls_back_stock(monkeypatch, tmp_path):
    conn = _conn(monkeypatch, tmp_path)
    try:
        with pytest.raises(SaleError):
            create_sale(conn, user_id=1, data={
                "numero_factura": "TEST-1",
                "items": [{"referencia": "P1", "cantidad": 3, "precio_venta": 10, "precio_compra": 5}],
            })
        row = conn.execute("SELECT stock FROM productos WHERE referencia='P1'").fetchone()
        assert row["stock"] == 2
    finally:
        conn.rollback()
        conn.close()
