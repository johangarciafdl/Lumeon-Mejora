from __future__ import annotations

from datetime import datetime, timezone
import secrets

from services.inventory_service import InventoryError, reserve_items
from services.audit_service import record as audit


class SaleError(ValueError):
    pass


def _invoice_number() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"LUM-{stamp}-{secrets.token_hex(3).upper()}"


def create_sale(conn, *, data: dict, user_id: int) -> int:
    items = data.get("items") or []
    numero_factura = str(data.get("numero_factura", "")).strip() or _invoice_number()
    idempotency_key = str(data.get("idempotency_key", "")).strip() or None
    if not items:
        raise SaleError("Sin productos")

    if idempotency_key:
        existing = conn.execute("SELECT id FROM ventas WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            return int(existing["id"])

    # Re-read product data inside the same transaction that reserves stock.
    # Never trust prices/stock supplied by the assistant or browser.
    normalized = []
    subtotal = 0.0
    profit = 0.0
    aggregated: dict[str, int] = {}
    for item in items:
        try:
            quantity = int(item.get("cantidad", 0))
        except (TypeError, ValueError) as exc:
            raise SaleError("La cantidad debe ser un entero") from exc
        if quantity <= 0:
            raise SaleError("La cantidad debe ser mayor que cero")
        reference = str(item.get("referencia", "")).strip()
        if not reference:
            raise SaleError("Cada producto debe tener referencia")
        aggregated[reference] = aggregated.get(reference, 0) + quantity

    try:
        # The conditional UPDATE is the final concurrency guard.
        reserve_items(conn, [{"referencia": ref, "cantidad": qty} for ref, qty in aggregated.items()])

        for reference, quantity in aggregated.items():
            product = conn.execute(
                "SELECT id, referencia, nombre, precio_compra, precio_venta FROM productos WHERE referencia=?",
                (reference,),
            ).fetchone()
            if product is None:
                raise SaleError(f"Producto no encontrado: {reference}")
            purchase_price = float(product["precio_compra"] or 0)
            sale_price = float(product["precio_venta"] or 0)
            subtotal += quantity * sale_price
            profit += quantity * (sale_price - purchase_price)
            normalized.append((product, quantity, sale_price, purchase_price))

        row = conn.execute(
            """INSERT INTO ventas
            (numero_factura,idempotency_key,cliente_id,cliente_nombre,cliente_email,cliente_telefono,
             fecha,forma_pago,subtotal,total,ganancia,estado,notas,usuario_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
            (
                numero_factura, idempotency_key, data.get("cliente_id"), data.get("cliente_nombre", ""),
                data.get("cliente_email", ""), data.get("cliente_telefono", ""),
                data.get("fecha", datetime.now().isoformat()), data.get("forma_pago", "Contado"),
                subtotal, subtotal, profit, data.get("estado", "Pendiente"), data.get("notas", ""), user_id,
            ),
        ).fetchone()
        sale_id = int(row["id"])
        for product, quantity, sale_price, purchase_price in normalized:
            conn.execute(
                """INSERT INTO venta_items
                (venta_id,producto_id,referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (sale_id, product["id"], product["referencia"], product["nombre"], quantity,
                 purchase_price, sale_price, quantity * sale_price,
                 quantity * (sale_price - purchase_price)),
            )
        audit(conn, actor_id=user_id, action="sale.created", entity="venta", entity_id=sale_id,
              details={"invoice": numero_factura, "total": subtotal, "items": len(normalized)})
        return sale_id
    except InventoryError as exc:
        raise SaleError(str(exc)) from exc
    except SaleError:
        raise
    except Exception as exc:
        if idempotency_key and "unique" in str(exc).lower():
            existing = conn.execute("SELECT id FROM ventas WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                return int(existing["id"])
        raise SaleError("No fue posible crear la venta") from exc
