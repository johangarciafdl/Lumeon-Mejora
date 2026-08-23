from __future__ import annotations

from services.audit_service import record as audit


class SaleDeleteError(ValueError):
    pass


def delete_sale(conn, *, sale_id: int, user_id: int) -> dict:
    sale = conn.execute(
        """
        SELECT id, numero_factura, estado, cliente_nombre, total
        FROM ventas
        WHERE id=?
        LIMIT 1
        """,
        (sale_id,),
    ).fetchone()

    if not sale:
        raise SaleDeleteError("Venta no encontrada")

    items = conn.execute(
        """
        SELECT id, producto_id, referencia, nombre, cantidad
        FROM venta_items
        WHERE venta_id=?
        ORDER BY id
        """,
        (sale_id,),
    ).fetchall()

    state = str(sale["estado"] or "").strip().lower()

    # Una devolución ya restauró el inventario.
    stock_restored = state not in {"devuelta", "devuelto"}

    if stock_restored:
        for item in items:
            if item["producto_id"] is None:
                continue

            updated = conn.execute(
                """
                UPDATE productos
                SET stock = stock + ?
                WHERE id=?
                """,
                (
                    int(item["cantidad"] or 0),
                    int(item["producto_id"]),
                ),
            )

            if updated.rowcount != 1:
                raise SaleDeleteError(
                    f"No se pudo restaurar stock de {item['referencia'] or item['producto_id']}"
                )

    # Eliminar información operativa vinculada.
    conn.execute(
        "DELETE FROM invoice_deliveries WHERE venta_id=?",
        (sale_id,),
    )

    conn.execute(
        """
        DELETE FROM venta_devolucion_items
        WHERE devolucion_id IN (
            SELECT id
            FROM venta_devoluciones
            WHERE venta_id=?
        )
        """,
        (sale_id,),
    )

    conn.execute(
        "DELETE FROM venta_devoluciones WHERE venta_id=?",
        (sale_id,),
    )

    conn.execute(
        "DELETE FROM venta_items WHERE venta_id=?",
        (sale_id,),
    )

    # Registrar antes de eliminar la venta.
    audit(
        conn,
        actor_id=user_id,
        action="sale.deleted",
        entity="venta",
        entity_id=sale_id,
        details={
            "invoice": sale["numero_factura"],
            "customer": sale["cliente_nombre"],
            "total": float(sale["total"] or 0),
            "items": len(items),
            "previous_state": sale["estado"],
            "stock_restored": stock_restored,
        },
    )

    conn.execute(
        "DELETE FROM ventas WHERE id=?",
        (sale_id,),
    )

    return {
        "sale_id": sale_id,
        "invoice": sale["numero_factura"],
        "stock_restored": stock_restored,
    }
