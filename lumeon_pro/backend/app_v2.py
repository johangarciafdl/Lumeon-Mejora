from __future__ import annotations

import os
from pathlib import Path

import dotenv
from flask import Flask, jsonify, request

from api.assistant_api import assistant_api
from api.delivery_api import delivery_api
from api.invoice_api import invoice_api
from core.config import load_settings
from core.db import get_db, transaction
from services.assistant_action_store import consume_pending, create_pending
from services.assistant_sales_service import AssistantSaleService
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import CustomerError, create_customer
from services.product_service import ProductError, create_product
from services.sale_service import SaleError, create_sale
from services.migration_service import apply_pending


dotenv.load_dotenv()
settings = load_settings()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = settings.secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=settings.session_cookie_secure,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.register_blueprint(assistant_api)
app.register_blueprint(invoice_api)
app.register_blueprint(delivery_api)


def initialize_database() -> None:
    """Apply additive migrations when the application starts.

    Startup is deliberately fail-fast in production: serving requests against a
    partially migrated schema is more dangerous than refusing to start.
    """
    conn = get_db()
    try:
        apply_pending(conn)
    finally:
        conn.close()


# Migrations are opt-in during tests to avoid mutating a test database merely by
# importing the module. Production/development can enable them with the flag.
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
    if "/assistant.css" not in html:
        html = html.replace("</head>", '<link rel="stylesheet" href="/assistant.css"></head>', 1)
    if "/assistant.js" not in html:
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


@app.route("/api/v2/ventas", methods=["POST"])
def create_venta_v2():
    try:
        actor = current_actor()
        require(actor, "create_sale")
        data = request.get_json(silent=True) or {}
        conn = get_db()
        try:
            sale_id = create_sale(conn, data=data, user_id=actor.user_id)
            conn.commit()
            return jsonify({"ok": True, "venta_id": sale_id}), 201
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except SaleError as exc:
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
