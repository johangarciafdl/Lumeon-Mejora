from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.invoice_delivery_service import deliver_invoice

invoice_delivery_api = Blueprint("invoice_delivery_api", __name__, url_prefix="/api/v2/invoices")


@invoice_delivery_api.post("/<invoice_number>/whatsapp")
def send_whatsapp(invoice_number: str):
    try:
        actor = current_actor()
        require(actor, "send_invoice")
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    conn = get_db()
    try:
        sale = conn.execute(
            "SELECT id,numero_factura,cliente_nombre,cliente_telefono,total FROM ventas WHERE numero_factura=? LIMIT 1",
            (invoice_number,),
        ).fetchone()
        if not sale:
            return jsonify({"ok": False, "error": "Factura no encontrada"}), 404
        items = [dict(row) for row in conn.execute(
            "SELECT referencia,nombre,cantidad,precio_compra,precio_venta FROM venta_items WHERE venta_id=? ORDER BY id",
            (sale["id"],),
        ).fetchall()]
        force_retry = bool((request.get_json(silent=True) or {}).get("retry"))
        result = deliver_invoice(
            conn, sale_id=sale["id"], invoice_number=sale["numero_factura"],
            customer_name=sale["cliente_nombre"] or "Cliente",
            phone=sale["cliente_telefono"] or "", items=items,
            total=float(sale["total"] or 0), force_retry=force_retry,
        )
        conn.commit()
        delivery = result["whatsapp"]
        status = getattr(delivery, "status", None)
        code = 200 if status in {"SENT", "ALREADY_SENT"} else 409 if status in {"RETRY_NOT_ALLOWED", "BLOCKED"} else 200
        return jsonify({"ok": status in {"SENT", "ALREADY_SENT"}, "delivery": status,
                        "error": getattr(delivery, "error", None)}), code
    finally:
        conn.close()
