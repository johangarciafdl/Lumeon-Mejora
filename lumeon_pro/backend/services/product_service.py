from __future__ import annotations

import sqlite3


class ProductError(ValueError):
    pass


def search_products(conn: sqlite3.Connection, term: str, limit: int = 20) -> list[dict]:
    term = str(term or "").strip()
    if not term:
        return []
    limit = max(1, min(int(limit), 100))
    like = f"%{term}%"
    rows = conn.execute(
        "SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos "
        "WHERE nombre LIKE ? OR referencia LIKE ? ORDER BY nombre LIMIT ?",
        (like, like, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def create_product(conn: sqlite3.Connection, data: dict) -> int:
    name = str(data.get("nombre", "")).strip()
    reference = str(data.get("referencia", "")).strip()
    if len(name) < 2:
        raise ProductError("El nombre del producto es obligatorio")
    if not reference:
        raise ProductError("La referencia es obligatoria")
    try:
        stock = int(data.get("stock", 0))
        minimum = int(data.get("stock_minimo", 0))
        price = float(data.get("precio_venta", 0))
    except (TypeError, ValueError) as exc:
        raise ProductError("Stock y precio deben ser numéricos") from exc
    if stock < 0 or minimum < 0 or price < 0:
        raise ProductError("Stock y precio no pueden ser negativos")
    if conn.execute("SELECT id FROM productos WHERE referencia=?", (reference,)).fetchone():
        raise ProductError("Ya existe un producto con esa referencia")
    cursor = conn.execute(
        "INSERT INTO productos(nombre,referencia,stock,stock_minimo,precio_venta) VALUES(?,?,?,?,?)",
        (name, reference, stock, minimum, price),
    )
    return int(cursor.lastrowid)


def low_stock(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        "SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos "
        "WHERE stock <= stock_minimo ORDER BY stock ASC LIMIT ?",
        (max(1, min(int(limit), 100)),),
    ).fetchall()
    return [dict(row) for row in rows]
