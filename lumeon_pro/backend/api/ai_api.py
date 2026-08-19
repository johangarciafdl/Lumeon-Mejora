from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from core.db import get_db
from services.ai_orchestrator import context, execute, plan
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require

ai_api = Blueprint("ai_api", __name__, url_prefix="/api/v2/assistant")


def _session_state() -> dict:
    state = session.get("ai_pending_action")
    return {"pending_ai_action": state} if state else {}


def _permission_for_action(action: str) -> str:
    return {
        "create_customer": "create_customer",
        "create_product": "create_product",
        "create_sale": "create_sale",
        "send_invoice": "send_invoice",
        "search_customer": "read_customer",
        "search_product": "read_product",
        "update_product_price": "create_product",
        "delete_product": "delete_product",
        "refund_sale": "refund_sale",
    }.get(action, "read_sale")


@ai_api.post("/ai")
def ai_message():
    try:
        actor = current_actor()
    except AuthenticationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or "").strip()
    if not text or len(text) > 1000:
        return jsonify({"ok": False, "error": "Mensaje vacío o demasiado largo"}), 400

    conn = get_db()
    try:
        state = _session_state()
        normalized = text.lower().strip()
        is_confirm = normalized in {"sí", "si", "confirmar", "confirmado", "hazlo"}
        is_cancel = normalized in {"no", "cancelar", "cancela", "cancelado"}

        if is_confirm and state.get("pending_ai_action"):
            planned = state["pending_ai_action"]
            require(actor, _permission_for_action(str(planned.get("action") or "read_sale")))
            planned = {"action": "confirm_pending"}
        elif is_cancel:
            planned = {"action": "cancel_pending"}
        else:
            planned = plan(text, context(conn))
            require(actor, _permission_for_action(str(planned.get("action") or "read_sale")))

        result, state = execute(conn, int(actor.id), planned, state)
        pending = state.get("pending_ai_action")
        if pending:
            session["ai_pending_action"] = pending
        else:
            session.pop("ai_pending_action", None)
        return jsonify(result), 200 if result.get("ok", True) else 400
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    finally:
        conn.close()
