from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    data: list[dict] | None = None


class AssistantActions:
    """Safe read/write facade for the assistant; never accepts raw SQL from users."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def search_customer(self, query: str) -> ActionResult:
        q = f"%{query.strip()}%"
        rows = self.conn.execute(
            "SELECT id,nombre,email,telefono FROM clientes WHERE nombre LIKE ? OR email LIKE ? OR telefono LIKE ? LIMIT 20",
            (q, q, q),
        ).fetchall()
        return ActionResult(True, f"Encontrados {len(rows)} clientes", [dict(row) for row in rows])

    def search_product(self, query: str) -> ActionResult:
        q = f"%{query.strip()}%"
        rows = self.conn.execute(
            "SELECT id,referencia,nombre,precio_venta,stock FROM productos WHERE referencia LIKE ? OR nombre LIKE ? LIMIT 20",
            (q, q),
        ).fetchall()
        return ActionResult(True, f"Encontrados {len(rows)} productos", [dict(row) for row in rows])

    def inventory_status(self, low_stock: int = 5) -> ActionResult:
        rows = self.conn.execute(
            "SELECT id,referencia,nombre,stock FROM productos WHERE stock <= ? ORDER BY stock ASC LIMIT 50",
            (low_stock,),
        ).fetchall()
        return ActionResult(True, f"{len(rows)} productos con stock bajo", [dict(row) for row in rows])

    def today_sales(self) -> ActionResult:
        rows = self.conn.execute(
            "SELECT id,numero_factura,cliente_nombre,total,forma_pago,fecha FROM ventas WHERE date(fecha)=date('now','localtime') ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return ActionResult(True, f"{len(rows)} ventas hoy", [dict(row) for row in rows])
