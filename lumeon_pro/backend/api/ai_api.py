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


@ai_api.post("/ai")
def ai_message():
    try:
        actor = current_actor()
        require(actor, "read_sale")
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or "").strip()
    if not text or len(text) > 1000:
        return jsonify({"ok": False, "error": "Mensaje vacío o demasiado largo"}), 400

    conn = get_db()
    try:
        state = _session_state()
        if text.lower().strip() not in {"sí", "si", "no", "cancelar", "cancela", "confirmar", "confirmado", "hazlo"}:
            planned = plan(text, context(conn))
        else:
            planned = {"action": "confirm_pending" if text.lower().strip() in {"sí", "si", "confirmar", "confirmado", "hazlo"} else "cancel_pending"}
            if planned["action"] == "confirm_pending" and not state.get("pending_ai_action"):
                return jsonify({"ok": True, "status": "idle", "message": "No hay ninguna operación pendiente."})

        result, state = execute(conn, int(actor.id), planned, state)
        pending = state.get("pending_ai_action")
        if pending:
            session["ai_pending_action"] = pending
        else:
            session.pop("ai_pending_action", None)
        return jsonify(result), 200 if result.get("ok", True) else 400
    finally:
        conn.close()
