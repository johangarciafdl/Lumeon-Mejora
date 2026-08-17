from __future__ import annotations

import os
from pathlib import Path

import dotenv
from flask import Flask, jsonify, request

from core.config import load_settings
from core.db import get_db, transaction
from services.assistant_action_store import consume_pending, create_pending
from services.assistant_sales_service import AssistantSaleService
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import CustomerError, create_customer
from services.product_service import ProductError, create_product
from services.sale_service import SaleError, create_sale


dotenv.load_dotenv()
settings = load_settings()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = settings.secret_key
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=settings.session_cookie_secure, SESSION_COOKIE_SAMESITE="Lax")


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
        with transaction() as conn:
            sale_id = create_sale(conn, data=data, user_id=int(actor.id or 0))
        return jsonify({"ok": True, "id": sale_id}), 201
    except AuthenticationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except (SaleError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        app.logger.exception("Error creando venta V2")
        return jsonify({"ok": False, "error": "Error interno"}), 500


@app.route("/api/v2/assistant/action", methods=["POST"])
def assistant_action():
    try:
        actor = current_actor()
        body = request.get_json(silent=True) or {}
        mode = str(body.get("mode", "propose")).strip().lower()

        if mode == "propose":
            intent = str(body.get("intent", "")).strip()
            payload = body.get("payload") or {}
            require(actor, intent)
            supported = {"create_sale", "create_customer", "create_product"}
            if intent not in supported:
                return jsonify({"ok": False, "error": "Acción aún no conectada al ejecutor V2"}), 400
            with transaction() as conn:
                action_id = create_pending(conn, user_id=int(actor.id), intent=intent, payload=payload)
            messages = {
                "create_sale": "Voy a crear la venta, generar la factura y avisar por WhatsApp si hay teléfono. ¿Confirmas?",
                "create_customer": "Voy a registrar este cliente. ¿Confirmas?",
                "create_product": "Voy a registrar este producto. ¿Confirmas?",
            }
            return jsonify({"ok": True, "status": "confirmation_required", "action_id": action_id, "message": messages[intent]}), 200

        if mode == "cancel":
            action_id = str(body.get("action_id", "")).strip()
            with transaction() as conn:
                row = consume_pending(conn, user_id=int(actor.id), action_id=action_id)
            return jsonify({"ok": True, "cancelled": row is not None})

        if mode == "confirm":
            action_id = str(body.get("action_id", "")).strip()
            with transaction() as conn:
                pending = consume_pending(conn, user_id=int(actor.id), action_id=action_id)
                if not pending:
                    return jsonify({"ok": False, "error": "La confirmación no existe o expiró"}), 409
                intent, payload = pending
                require(actor, intent)
                if intent == "create_sale":
                    result = AssistantSaleService(settings).execute(conn, actor_id=int(actor.id), data=payload)
                    return jsonify({"ok": True, "status": "completed", "sale_id": result.sale_id, "invoice": result.invoice_number, "invoice_file": result.invoice_filename, "whatsapp": result.whatsapp_status, "whatsapp_error": result.whatsapp_error}), 201
                if intent == "create_customer":
                    entity_id = create_customer(conn, payload)
                    return jsonify({"ok": True, "status": "completed", "entity": "cliente", "id": entity_id}), 201
                if intent == "create_product":
                    entity_id = create_product(conn, payload)
                    return jsonify({"ok": True, "status": "completed", "entity": "producto", "id": entity_id}), 201

        return jsonify({"ok": False, "error": "Modo inválido"}), 400
    except AuthenticationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 401
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except (CustomerError, ProductError, SaleError, ValueError) as exc:
        return jsonify({"ok": False, "status": "validation_error", "error": str(exc)}), 400
    except Exception:
        app.logger.exception("Error en acción del asistente")
        return jsonify({"ok": False, "error": "Error interno"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
