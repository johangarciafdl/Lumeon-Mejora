from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require

sale_api = Blueprint("sale_api", __name__, url_prefix="/api/v2/ventas")


def _actor(permission):
    actor = current_actor()
    require(actor, permission)
    return actor


@sale_api.get("")
def list_sales():
    try:
        _actor("read_sale")
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
        q = (request.args.get("q") or "").strip()
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT id, numero_factura, cliente_id, cliente_nombre, fecha,
                       forma_pago, subtotal, total, ganancia, estado, usuario_id
                FROM ventas
                WHERE (? = '' OR numero_factura LIKE ? OR cliente_nombre LIKE ?)
                ORDER BY id DESC LIMIT ?
            """, (q, f"%{q}%", f"%{q}%", limit)).fetchall()
            return jsonify({"ok": True, "results": [dict(r) for r in rows]})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ValueError:
        return jsonify({"ok": False, "error": "limit inválido"}), 400


@sale_api.get("/<int:sale_id>")
def get_sale(sale_id: int):
    try:
        _actor("read_sale")
        conn = get_db()
        try:
            sale = conn.execute("SELECT * FROM ventas WHERE id=?", (sale_id,)).fetchone()
            if not sale:
                return jsonify({"ok": False, "error": "Venta no encontrada"}), 404
            items = conn.execute("SELECT * FROM venta_items WHERE venta_id=? ORDER BY id", (sale_id,)).fetchall()
            return jsonify({"ok": True, "venta": dict(sale), "items": [dict(r) for r in items]})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
