from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import CustomerError, create_customer, search_customers

customer_api = Blueprint("customer_api", __name__, url_prefix="/api/v2/clientes")


@customer_api.get("")
def list_customers():
    try:
        actor = current_actor()
        require(actor, "read_customer")
        q = (request.args.get("q") or "").strip()
        conn = get_db()
        try:
            return jsonify({"ok": True, "results": search_customers(conn, q)})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@customer_api.post("")
def add_customer():
    try:
        actor = current_actor()
        require(actor, "create_customer")
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
