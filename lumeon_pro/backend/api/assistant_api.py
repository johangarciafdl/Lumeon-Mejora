from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db, transaction
from services.assistant_workflow import AssistantSession, is_cancellation, is_confirmation
from services.customer_service import search_customers, create_customer, CustomerError

assistant_api = Blueprint("assistant_api", __name__, url_prefix="/api/v2/assistant")

# Session-local state is intentionally isolated. Production deployments can replace this
# with a server-side session/Redis implementation without changing the API contract.
_sessions: dict[str, AssistantSession] = {}


def _session_id() -> str:
    return request.headers.get("X-Assistant-Session", "default")[:100]


@assistant_api.post("/message")
def message():
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "Mensaje vacío"}), 400

    session = _sessions.setdefault(_session_id(), AssistantSession())

    if is_confirmation(text):
        pending = session.confirm()
        if not pending:
            return jsonify({"ok": True, "status": "idle", "message": "No hay ninguna operación pendiente."})
        intent, payload = pending
        if intent == "create_customer":
            try:
                with transaction() as conn:
                    customer_id = create_customer(conn, payload)
                return jsonify({"ok": True, "status": "executed", "intent": intent, "id": customer_id})
            except CustomerError as exc:
                return jsonify({"ok": False, "status": "error", "error": str(exc)}), 400
        return jsonify({"ok": False, "status": "unsupported", "error": f"Intent aún no implementado: {intent}"}), 400

    if is_cancellation(text):
        cancelled = session.cancel()
        return jsonify({"ok": True, "status": "cancelled" if cancelled else "idle"})

    lowered = text.lower()
    if lowered.startswith("buscar cliente"):
        term = text[len("buscar cliente"):].strip()
        conn = get_db()
        try:
            return jsonify({"ok": True, "status": "ready", "intent": "search_customers", "results": search_customers(conn, term)})
        finally:
            conn.close()

    if lowered.startswith("registrar cliente"):
        payload = body.get("customer") or {}
        return jsonify({"ok": True, **session.propose("create_customer", payload)})

    return jsonify({
        "ok": True,
        "status": "unknown",
        "message": "No reconocí la operación. Prueba: buscar cliente <nombre> o registrar cliente.",
    })
