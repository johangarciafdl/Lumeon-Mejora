from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.inventory_service import InventoryError, receive_items
from services.product_service import low_stock

inventory_api = Blueprint("inventory_api", __name__, url_prefix="/api/v2/inventario")


@inventory_api.get("/bajo")
def low_stock_list():
    try:
        actor = current_actor()
        require(actor, "read_product")
        try:
            limit = max(1, min(int(request.args.get("limit", 100)), 100))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "limit inválido"}), 400
        conn = get_db()
        try:
            return jsonify({"ok": True, "results": low_stock(conn, limit)})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@inventory_api.post("/entrada")
def receive_stock():
    try:
        actor = current_actor()
        require(actor, "update_inventory")
        data = request.get_json(silent=True) or {}
        items = data.get("items") or []
        conn = get_db()
        try:
            receive_items(conn, items)
            conn.commit()
            return jsonify({"ok": True, "updated": len(items)}), 200
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except InventoryError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
