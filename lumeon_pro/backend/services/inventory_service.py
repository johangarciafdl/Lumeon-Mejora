from __future__ import annotations

from dataclasses import dataclass
import sqlite3


class InventoryError(ValueError):
    """Raised when an inventory operation cannot be completed safely."""


@dataclass(frozen=True)
class StockItem:
    referencia: str
    cantidad: int


def validate_items(conn: sqlite3.Connection, items: list[dict]) -> None:
    if not items:
        raise InventoryError("La venta debe contener al menos un producto")

    for item in items:
        try:
            quantity = int(item.get("cantidad", 0))
        except (TypeError, ValueError) as exc:
            raise InventoryError("La cantidad debe ser un entero") from exc
        if quantity <= 0:
            raise InventoryError("La cantidad debe ser mayor que cero")

        reference = str(item.get("referencia", "")).strip()
        if not reference:
            raise InventoryError("Cada producto debe tener referencia")

        row = conn.execute(
            "SELECT stock FROM productos WHERE referencia=?",
            (reference,),
        ).fetchone()
        if row is None:
            raise InventoryError(f"Producto no encontrado: {reference}")
        if int(row["stock"]) < quantity:
            raise InventoryError(
                f"Stock insuficiente para {reference}: "
                f"disponible {row['stock']}, solicitado {quantity}"
            )


def reserve_items(conn: sqlite3.Connection, items: list[dict]) -> None:
    """Atomically decrements stock; caller controls the transaction."""
    validate_items(conn, items)
    for item in items:
        quantity = int(item["cantidad"])
        reference = str(item["referencia"]).strip()
        cursor = conn.execute(
            "UPDATE productos SET stock=stock-? "
            "WHERE referencia=? AND stock>=?",
            (quantity, reference, quantity),
        )
        if cursor.rowcount != 1:
            raise InventoryError(f"Stock insuficiente para {reference}")


def receive_items(conn: sqlite3.Connection, items: list[dict]) -> None:
    for item in items:
        quantity = int(item.get("cantidad", 0))
        if quantity <= 0:
            raise InventoryError("La cantidad recibida debe ser mayor que cero")
        reference = str(item.get("referencia", "")).strip()
        if not reference:
            raise InventoryError("El producto recibido requiere referencia")
        cursor = conn.execute(
            "UPDATE productos SET stock=stock+? WHERE referencia=?",
            (quantity, reference),
        )
        if cursor.rowcount != 1:
            raise InventoryError(f"Producto no encontrado: {reference}")
