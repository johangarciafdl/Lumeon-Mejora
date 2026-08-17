from __future__ import annotations

from datetime import datetime

from services.inventory_service import reserve_items


class SaleError(ValueError):
    pass


def create_sale(conn, *, data: dict, user_id: int) -> int:
    items = data.get("items") or []
    if not str(data.get("numero_factura", "")).strip():
        raise SaleError("El número de factura es obligatorio")
    if not items:
        raise SaleError("Sin productos")

    subtotal = 0.0
    profit = 0.0
    normalized = []
    for item in items:
        try:
            quantity = int(item.get("cantidad", 0))
            sale_price = float(item.get("precio_venta", 0))
            purchase_price = float(item.get("precio_compra", 0))
        except (TypeError, ValueError) as exc:
            raise SaleError("Cantidad y precios deben ser válidos") from exc
        if quantity <= 0 or sale_price < 0 or purchase_price < 0:
            raise SaleError("Cantidad y precios deben ser válidos")
        subtotal += quantity * sale_price
        profit += quantity * (sale_price - purchase_price)
        normalized.append((item, quantity, sale_price, purchase_price))

    reserve_items(conn, items)

    row = conn.execute(
        """INSERT INTO ventas
        (numero_factura,cliente_id,cliente_nombre,cliente_email,cliente_telefono,
         fecha,forma_pago,subtotal,total,ganancia,estado,notas,usuario_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
        (
            data["numero_factura"], data.get("cliente_id"), data.get("cliente_nombre", ""),
            data.get("cliente_email", ""), data.get("cliente_telefono", ""),
            data.get("fecha", datetime.now().isoformat()), data.get("forma_pago", "Contado"),
            subtotal, subtotal, profit, data.get("estado", "Pendiente"),
            data.get("notas", ""), user_id,
        ),
    ).fetchone()
    sale_id = int(row["id"])

    for item, quantity, sale_price, purchase_price in normalized:
        conn.execute(
            """INSERT INTO venta_items
            (venta_id,producto_id,referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                sale_id, item.get("producto_id"), item.get("referencia", ""), item.get("nombre", ""),
                quantity, purchase_price, sale_price, quantity * sale_price,
                quantity * (sale_price - purchase_price),
            ),
        )

    return sale_id
