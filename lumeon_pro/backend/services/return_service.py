from __future__ import annotations

from services.audit_service import record as audit


class ReturnError(ValueError):
    pass


def return_sale(conn, *, sale_id: int, user_id: int, idempotency_key: str, reason: str = "") -> dict:
    key = str(idempotency_key or "").strip()
    if not key:
        raise ReturnError("idempotency_key es obligatorio")

    existing = conn.execute(
        "SELECT id, venta_id FROM venta_devoluciones WHERE idempotency_key=?", (key,)
    ).fetchone()
    if existing:
        return {"return_id": int(existing["id"]), "venta_id": int(existing["venta_id"]), "already_processed": True}

    sale = conn.execute("SELECT id, estado FROM ventas WHERE id=?", (sale_id,)).fetchone()
    if not sale:
        raise ReturnError("Venta no encontrada")
    if str(sale["estado"]).lower() in {"anulada", "devuelta", "cancelada"}:
        raise ReturnError("La venta ya está anulada o devuelta")

    items = conn.execute(
        "SELECT producto_id, cantidad FROM venta_items WHERE venta_id=? AND producto_id IS NOT NULL", (sale_id,)
    ).fetchall()
    if not items:
        raise ReturnError("La venta no tiene productos retornables")

    try:
        conn.execute(
            "INSERT INTO venta_devoluciones (venta_id,idempotency_key,motivo,usuario_id) VALUES (?,?,?,?)",
            (sale_id, key, reason.strip()[:500], user_id),
        )
        for item in items:
            updated = conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id=? RETURNING id",
                (int(item["cantidad"]), int(item["producto_id"])),
            ).fetchone()
            if not updated:
                raise ReturnError("Producto de la devolución no encontrado")
        conn.execute("UPDATE ventas SET estado='Devuelta' WHERE id=?", (sale_id,))
        audit(conn, actor_id=user_id, action="sale.returned", entity="venta", entity_id=sale_id,
              details={"items": len(items), "reason": reason[:500]})
        row = conn.execute("SELECT id FROM venta_devoluciones WHERE idempotency_key=?", (key,)).fetchone()
        return {"return_id": int(row["id"]), "venta_id": sale_id, "already_processed": False}
    except ReturnError:
        raise
    except Exception as exc:
        if "unique" in str(exc).lower():
            existing = conn.execute(
                "SELECT id, venta_id FROM venta_devoluciones WHERE idempotency_key=?", (key,)
            ).fetchone()
            if existing:
                return {"return_id": int(existing["id"]), "venta_id": int(existing["venta_id"]), "already_processed": True}
        raise ReturnError("No fue posible procesar la devolución") from exc
