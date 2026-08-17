from __future__ import annotations

import sqlite3

from services.inventory_service import receive_items


class OrderStateError(ValueError):
    pass


ALLOWED_TRANSITIONS = {
    "Pendiente": {"Entregado", "Cancelado"},
    "Entregado": set(),
    "Cancelado": set(),
}


def transition_order(conn: sqlite3.Connection, order_id: int, new_state: str, *, delivery_date: str | None = None) -> None:
    row = conn.execute("SELECT estado FROM pedidos WHERE id=?", (order_id,)).fetchone()
    if row is None:
        raise OrderStateError("Pedido no encontrado")

    current = row["estado"]
    if new_state not in ALLOWED_TRANSITIONS.get(current, set()):
        raise OrderStateError(f"Transición no permitida: {current} -> {new_state}")

    if new_state == "Entregado":
        items = [dict(r) for r in conn.execute(
            "SELECT referencia,cantidad FROM pedido_items WHERE pedido_id=?", (order_id,)
        ).fetchall()]
        receive_items(conn, items)
        conn.execute(
            "UPDATE pedidos SET estado=?,fecha_entrega=COALESCE(?,date('now')) WHERE id=?",
            (new_state, delivery_date, order_id),
        )
    elif new_state == "Cancelado":
        conn.execute(
            "UPDATE pedidos SET estado=?,fecha_cancelacion=date('now') WHERE id=?",
            (new_state, order_id),
        )
