from __future__ import annotations

import os
from pathlib import Path

import dotenv
from flask import Flask, jsonify, request

from api import register_blueprints
from core.config import load_settings
from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.migration_service import apply_pending
from services.product_service import ProductError, create_product
from services.customer_service import CustomerError, create_customer
from services.sale_service import SaleError, create_sale
from services.return_service import ReturnError, return_sale
from services.sale_completion_service import deliver_sale_invoice

dotenv.load_dotenv()
settings = load_settings()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = settings.secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=settings.session_cookie_secure,
    SESSION_COOKIE_SAMESITE="Lax",
)
register_blueprints(app)


def initialize_database() -> None:
    conn = get_db()
    try:
        apply_pending(conn)
    finally:
        conn.close()


if os.getenv("LUMEON_AUTO_MIGRATE", "false").lower() in {"1", "true", "yes"}:
    initialize_database()


@app.after_request
def security_headers(response):
    origin = request.headers.get("Origin")
    if origin in settings.allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,X-CSRF-Token,X-Assistant-Session"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.route("/", methods=["GET"])
def index():
    path = Path(app.static_folder) / "index.html"
    html = path.read_text(encoding="utf-8")
    if 'href="/assistant.css"' not in html:
        html = html.replace("</head>", '<link rel="stylesheet" href="/assistant.css"></head>', 1)
    if 'src="/assistant.js"' not in html:
        html = html.replace("</body>", '<script src="/assistant.js" defer></script></body>', 1)
    return html


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"ok": True, "service": "lumeon", "version": "2"})
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify({"ok": False, "service": "lumeon", "version": "2"}), 503


@app.post("/api/v2/ventas")
def create_venta_v2():
    try:
        actor = current_actor()
        require(actor, "create_sale")
        data = request.get_json(silent=True) or {}
        conn = get_db()
        try:
            sale_id = create_sale(conn, data=data, user_id=actor.id)
            conn.commit()
            whatsapp = deliver_sale_invoice(conn, sale_id)
            conn.commit()
            return jsonify({"ok": True, "venta_id": sale_id, "whatsapp": whatsapp}), 201
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except SaleError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/v2/ventas/<int:sale_id>/devolucion")
def return_venta_v2(sale_id: int):
    try:
        actor = current_actor()
        require(actor, "refund_sale")
        data = request.get_json(silent=True) or {}
        idempotency_key = str(data.get("idempotency_key") or request.headers.get("Idempotency-Key") or "").strip()
        if not idempotency_key:
            return jsonify({"ok": False, "error": "Idempotency-Key es obligatorio"}), 400

        conn = get_db()
        try:
            result = return_sale(
                conn,
                sale_id=sale_id,
                user_id=int(actor.id),
                idempotency_key=idempotency_key,
                reason=str(data.get("motivo") or ""),
            )
            conn.commit()
            return jsonify({"ok": True, **result}), 200
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ReturnError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/v2/clientes")
def create_cliente_v2():
    try:
        actor = current_actor()
        require(actor, "create_customer")
        conn = get_db()
        try:
            customer_id = create_customer(conn, request.get_json(silent=True) or {})
            conn.commit()
            return jsonify({"ok": True, "cliente_id": customer_id}), 201
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except CustomerError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/v2/productos")
def create_producto_v2():
    try:
        actor = current_actor()
        require(actor, "create_product")
        conn = get_db()
        try:
            product_id = create_product(conn, request.get_json(silent=True) or {})
            conn.commit()
            return jsonify({"ok": True, "producto_id": product_id}), 201
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ProductError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"ok": False, "error": "Solicitud inválida"}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"ok": False, "error": "Recurso no encontrado"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"ok": False, "error": "Método no permitido"}), 405
