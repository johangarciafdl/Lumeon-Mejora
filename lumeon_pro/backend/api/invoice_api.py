from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file
from io import BytesIO

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.invoice_service import build_invoice

invoice_api = Blueprint("invoice_api", __name__, url_prefix="/api/v2/invoices")


def _actor():
    try:
        return current_actor()
    except AuthenticationError as exc:
        raise PermissionError(str(exc)) from exc


def _invoice(conn, invoice_number):
    row = conn.execute("""SELECT id, numero_factura, cliente_nombre, cliente_telefono, total
                         FROM ventas WHERE numero_factura=? LIMIT 1""", (invoice_number,)).fetchone()
    if not row:
        return None, None
    items = conn.execute("""SELECT referencia,nombre,cantidad,precio_compra,precio_venta
                           FROM venta_items WHERE venta_id=? ORDER BY id""", (row["id"],)).fetchall()
    return row, [dict(x) for x in items]


@invoice_api.get("/<invoice_number>/pdf")
def pdf(invoice_number: str):
    try:
        actor = _actor()
        require(actor, "view_invoice")
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    conn = get_db()
    try:
        row, items = _invoice(conn, invoice_number)
        if not row:
            return jsonify({"ok": False, "error": "Factura no encontrada"}), 404
        doc = build_invoice(invoice_number=row["numero_factura"], customer_name=row["cliente_nombre"] or "Consumidor final", items=items, total=float(row["total"] or 0))
        return send_file(BytesIO(doc.data), mimetype=doc.content_type, as_attachment=True, download_name=doc.filename)
    finally:
        conn.close()
