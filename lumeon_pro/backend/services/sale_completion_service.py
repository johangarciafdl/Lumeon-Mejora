from __future__ import annotations

from services.invoice_delivery_service import deliver_invoice


def deliver_sale_invoice(conn, sale_id: int, *, force_retry: bool = False) -> dict:
    """Create the invoice payload and automatically deliver it by WhatsApp when a phone exists.

    This function never raises for a WhatsApp delivery failure; the sale remains committed and
    the delivery result is returned to the caller for logging/UI feedback.
    """
    sale = conn.execute(
        """SELECT id, numero_factura, cliente_nombre, cliente_telefono, total, estado
           FROM ventas WHERE id=? LIMIT 1""",
        (sale_id,),
    ).fetchone()
    if not sale:
        return {"status": "NOT_FOUND", "error": "Venta no encontrada"}

    items = [dict(row) for row in conn.execute(
        """SELECT referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia
           FROM venta_items WHERE venta_id=? ORDER BY id""",
        (sale_id,),
    ).fetchall()]

    result = deliver_invoice(
        conn,
        sale_id=int(sale["id"]),
        invoice_number=sale["numero_factura"],
        customer_name=sale["cliente_nombre"] or "Cliente",
        phone=sale["cliente_telefono"] or "",
        items=items,
        total=float(sale["total"] or 0),
        force_retry=force_retry,
    )
    delivery = result.get("whatsapp")
    return {
        "status": getattr(delivery, "status", None),
        "error": getattr(delivery, "error", None),
    }
