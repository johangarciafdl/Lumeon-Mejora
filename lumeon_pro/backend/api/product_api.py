from __future__ import annotations

from flask import Blueprint, jsonify, request
from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.product_service import ProductError, create_product, search_products

product_api = Blueprint("product_api", __name__, url_prefix="/api/v2/productos")


@product_api.get("")
def list_products():
    try:
        actor = current_actor()
        require(actor, "read_product")
        q = (request.args.get("q") or "").strip()
        try:
            limit = max(1, min(int(request.args.get("limit", 100)), 100))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "limit inválido"}), 400
        conn = get_db()
        try:
            return jsonify({"ok": True, "results": search_products(conn, q, limit)})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@product_api.post("")
def add_product():
    try:
        actor = current_actor()
        require(actor, "create_product")
        data = request.get_json(silent=True) or {}
        conn = get_db()
        try:
            product_id = create_product(conn, data)
            conn.commit()
            return jsonify({"ok": True, "producto_id": product_id}), 201
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ProductError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
