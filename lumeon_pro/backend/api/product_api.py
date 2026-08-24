from __future__ import annotations

from flask import Blueprint, jsonify, request
from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.product_service import ProductError, create_product, search_products

product_api = Blueprint("product_api", __name__, url_prefix="/api/v2/productos")


def _authorized(permission: str):
    actor = current_actor()
    require(actor, permission)
    return actor


def _normalize_product(data: dict) -> dict:
    name = str(data.get("nombre", "")).strip()
    reference = str(data.get("referencia", "")).strip()
    if len(name) < 2:
        raise ProductError("El nombre del producto es obligatorio")
    if not reference:
        raise ProductError("La referencia es obligatoria")
    try:
        stock = int(data.get("stock", 0))
        minimum = int(data.get("stock_minimo", 0))
        purchase = float(data.get("precio_compra", 0))
        price = float(data.get("precio_venta", 0))
    except (TypeError, ValueError) as exc:
        raise ProductError("Stock y precio deben ser numéricos") from exc
    if stock < 0 or minimum < 0 or purchase < 0 or price < 0:
        raise ProductError("Stock y precio no pueden ser negativos")
    return {
        "nombre": name,
        "referencia": reference,
        "descripcion": str(data.get("descripcion", "")).strip(),
        "categoria": str(data.get("categoria", "General")).strip() or "General",
        "precio_compra": purchase,
        "precio_venta": price,
        "stock": stock,
        "stock_minimo": minimum,
    }


@product_api.get("")
def list_products():
    try:
        _authorized("read_product")
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
        _authorized("create_product")
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


@product_api.put("/<int:product_id>")
def update_product(product_id: int):
    try:
        _authorized("update_product")
        data = _normalize_product(request.get_json(silent=True) or {})
        conn = get_db()
        try:
            current = conn.execute("SELECT id FROM productos WHERE id=? LIMIT 1", (product_id,)).fetchone()
            if not current:
                return jsonify({"ok": False, "error": "Producto no encontrado"}), 404
            duplicate = conn.execute(
                "SELECT id FROM productos WHERE referencia=? AND id<>? LIMIT 1",
                (data["referencia"], product_id),
            ).fetchone()
            if duplicate:
                return jsonify({"ok": False, "error": "Ya existe un producto con esa referencia"}), 400
            conn.execute(
                """UPDATE productos SET nombre=?,referencia=?,descripcion=?,categoria=?,precio_compra=?,precio_venta=?,stock=?,stock_minimo=? WHERE id=?""",
                (data["nombre"], data["referencia"], data["descripcion"], data["categoria"], data["precio_compra"], data["precio_venta"], data["stock"], data["stock_minimo"], product_id),
            )
            conn.commit()
            return jsonify({"ok": True, "id": product_id})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ProductError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@product_api.delete("/<int:product_id>")
def delete_product(product_id: int):
    try:
        _authorized("delete_product")
        conn = get_db()
        try:
            current = conn.execute("SELECT id FROM productos WHERE id=? LIMIT 1", (product_id,)).fetchone()
            if not current:
                return jsonify({"ok": False, "error": "Producto no encontrado"}), 404
            linked = conn.execute("SELECT COUNT(*) AS total FROM venta_items WHERE producto_id=?", (product_id,)).fetchone()["total"]
            if int(linked or 0) > 0:
                return jsonify({"ok": False, "error": "No se puede eliminar un producto que tiene ventas asociadas"}), 400
            conn.execute("DELETE FROM productos WHERE id=?", (product_id,))
            conn.commit()
            return jsonify({"ok": True, "id": product_id})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
