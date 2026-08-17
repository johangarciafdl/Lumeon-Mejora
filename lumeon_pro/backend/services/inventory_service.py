from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class InventoryError(ValueError):
    """Raised when an inventory operation cannot be completed safely."""


@dataclass(frozen=True)
class StockItem:
    referencia: str
    cantidad: int


def _validate_item(item: dict[str, Any]) -> tuple[str, int]:
    try:
        quantity = int(item.get("cantidad", 0))
    except (TypeError, ValueError) as exc:
        raise InventoryError("La cantidad debe ser un entero") from exc
    if quantity <= 0:
        raise InventoryError("La cantidad debe ser mayor que cero")
    reference = str(item.get("referencia", "")).strip()
    if not reference:
        raise InventoryError("Cada producto debe tener referencia")
    return reference, quantity


def validate_items(conn, items: list[dict]) -> None:
    if not items:
        raise InventoryError("La venta debe contener al menos un producto")
    for item in items:
        reference, quantity = _validate_item(item)
        row = conn.execute(
            "SELECT stock FROM productos WHERE referencia=?",
            (reference,),
        ).fetchone()
        if row is None:
            raise InventoryError(f"Producto no encontrado: {reference}")
        if int(row["stock"]) < quantity:
            raise InventoryError(
                f"Stock insuficiente para {reference}: disponible {row['stock']}, solicitado {quantity}"
            )


def reserve_items(conn, items: list[dict]) -> None:
    """Reserve stock using conditional UPDATEs inside the caller's transaction.

    The UPDATE itself is the concurrency guard: two concurrent sales cannot both
    decrement the same stock below zero.
    """
    if not items:
        raise InventoryError("La venta debe contener al menos un producto")

    # Aggregate duplicate references so a sale containing the same product twice
    # reserves the combined quantity atomically.
    requested: dict[str, int] = {}
    for item in items:
        reference, quantity = _validate_item(item)
        requested[reference] = requested.get(reference, 0) + quantity

    for reference, quantity in requested.items():
        cursor = conn.execute(
            "UPDATE productos SET stock=stock-? WHERE referencia=? AND stock>=?",
            (quantity, reference, quantity),
        )
        if cursor.rowcount != 1:
            raise InventoryError(f"Stock insuficiente o producto no encontrado: {reference}")


def receive_items(conn, items: list[dict]) -> None:
    for item in items:
        reference, quantity = _validate_item(item)
        cursor = conn.execute(
            "UPDATE productos SET stock=stock+? WHERE referencia=?",
            (quantity, reference),
        )
        if cursor.rowcount != 1:
            raise InventoryError(f"Producto no encontrado: {reference}")
