from __future__ import annotations

import os

from flask import Blueprint, jsonify

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.delivery_retry_service import retry_allowed, retry_limit
from services.invoice_delivery_service import deliver_invoice


delivery_api = Blueprint("delivery_api", __name__, url_prefix="/api/v2/deliveries")


@delivery_api.post("/<int:delivery_id>/retry")
def retry(delivery_id: int):
    try:
        actor = current_actor()
        require(actor, "send_invoice")
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM message_deliveries WHERE id=? LIMIT 1", (delivery_id,)
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Entrega no encontrada"}), 404
        if row["channel"] != "whatsapp":
            return jsonify({"ok": False, "error": "Solo WhatsApp admite reintento automático"}), 400
        if not retry_allowed(row, retry_limit()):
            return jsonify({"ok": False, "error": "Límite de reintentos alcanzado o entrega no reintentable"}), 409

        sale = conn.execute(
            "SELECT id,numero_factura,cliente_nombre,cliente_telefono,total FROM ventas WHERE id=? LIMIT 1",
            (row["venta_id"],),
        ).fetchone()
        if not sale:
            return jsonify({"ok": False, "error": "Venta asociada no encontrada"}), 404
        items = [dict(item) for item in conn.execute(
            "SELECT referencia,nombre,cantidad,precio_compra,precio_venta FROM venta_items WHERE venta_id=? ORDER BY id",
            (sale["id"],),
        ).fetchall()]
        result = deliver_invoice(
            conn,
            sale_id=sale["id"],
            invoice_number=sale["numero_factura"],
            customer_name=sale["cliente_nombre"] or "Cliente",
            phone=sale["cliente_telefono"] or row["recipient"],
            items=items,
            total=float(sale["total"] or 0),
        )
        conn.commit()
        return jsonify({"ok": True, "delivery": result.get("whatsapp")}), 200
    finally:
        conn.close()
