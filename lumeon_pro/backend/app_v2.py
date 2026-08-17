from __future__ import annotations

from flask import Flask, jsonify, request
from flask_login import LoginManager
import dotenv

from core.config import load_settings
from core.db import get_db, transaction
from services.sale_service import SaleError, create_sale


dotenv.load_dotenv()
settings = load_settings()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = settings.secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=settings.session_cookie_secure,
    SESSION_COOKIE_SAMESITE="Lax",
)

login_manager = LoginManager(app)


@app.after_request
def security_headers(response):
    origin = request.headers.get("Origin")
    if origin in settings.allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,X-CSRF-Token"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"ok": True, "service": "lumeon", "version": "2"})
    except Exception:
        return jsonify({"ok": False, "service": "lumeon", "version": "2"}), 503


@app.route("/api/v2/ventas", methods=["POST"])
def create_venta_v2():
    # This endpoint is intentionally a clean seam for migrating the legacy route.
    # Authentication is added when the shared User loader is moved into core/auth.py.
    data = request.get_json(silent=True) or {}
    try:
        with transaction() as conn:
            sale_id = create_sale(conn, data=data, user_id=0)
        return jsonify({"ok": True, "id": sale_id}), 201
    except (SaleError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        app.logger.exception("Error creando venta V2")
        return jsonify({"ok": False, "error": "Error interno"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").getenv("PORT", "5000")), debug=False)
