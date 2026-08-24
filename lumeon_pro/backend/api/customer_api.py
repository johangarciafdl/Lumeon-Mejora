from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import CustomerError, create_customer, normalize_customer, search_customers

customer_api = Blueprint("customer_api", __name__, url_prefix="/api/v2/clientes")


def _authorized(permission: str):
    actor = current_actor()
    require(actor, permission)
    return actor


@customer_api.get("")
def list_customers():
    try:
        _authorized("read_customer")
        q = (request.args.get("q") or "").strip()
        try:
            limit = max(1, min(int(request.args.get("limit", 100)), 100))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "limit inválido"}), 400
        conn = get_db()
        try:
            return jsonify({"ok": True, "results": search_customers(conn, q, limit)})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@customer_api.post("")
def add_customer():
    try:
        _authorized("create_customer")
        data = request.get_json(silent=True) or {}
        conn = get_db()
        try:
            customer_id = create_customer(conn, data)
            conn.commit()
            return jsonify({"ok": True, "cliente_id": customer_id}), 201
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except CustomerError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@customer_api.put("/<int:customer_id>")
def update_customer(customer_id: int):
    try:
        _authorized("update_customer")
        data = normalize_customer(request.get_json(silent=True) or {})
        conn = get_db()
        try:
            current = conn.execute("SELECT id FROM clientes WHERE id=? LIMIT 1", (customer_id,)).fetchone()
            if not current:
                return jsonify({"ok": False, "error": "Cliente no encontrado"}), 404
            document = data["documento"]
            if document:
                duplicate = conn.execute(
                    "SELECT id FROM clientes WHERE documento=? AND id<>? LIMIT 1",
                    (document, customer_id),
                ).fetchone()
                if duplicate:
                    return jsonify({"ok": False, "error": "Ya existe un cliente con ese documento"}), 400
            conn.execute(
                """UPDATE clientes SET nombre=?,documento=?,telefono=?,direccion=?,email=?,ciudad=? WHERE id=?""",
                (data["nombre"], data["documento"], data["telefono"], data["direccion"], data["email"], data["ciudad"], customer_id),
            )
            conn.commit()
            return jsonify({"ok": True, "id": customer_id})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except CustomerError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@customer_api.delete("/<int:customer_id>")
def delete_customer(customer_id: int):
    try:
        _authorized("delete_customer")
        conn = get_db()
        try:
            current = conn.execute("SELECT id FROM clientes WHERE id=? LIMIT 1", (customer_id,)).fetchone()
            if not current:
                return jsonify({"ok": False, "error": "Cliente no encontrado"}), 404
            linked = conn.execute("SELECT COUNT(*) AS total FROM ventas WHERE cliente_id=?", (customer_id,)).fetchone()["total"]
            if int(linked or 0) > 0:
                return jsonify({"ok": False, "error": "No se puede eliminar un cliente con ventas asociadas"}), 400
            conn.execute("DELETE FROM clientes WHERE id=?", (customer_id,))
            conn.commit()
            return jsonify({"ok": True, "id": customer_id})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
