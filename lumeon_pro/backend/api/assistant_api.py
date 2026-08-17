from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db, transaction
from services.assistant_workflow import AssistantSession, is_cancellation, is_confirmation
from services.assistant_session_service import get_session, save_session
from services.audit_service import record
from services.customer_service import search_customers, create_customer, CustomerError

assistant_api = Blueprint("assistant_api", __name__, url_prefix="/api/v2/assistant")


def _session_id() -> str:
    return request.headers.get("X-Assistant-Session", "default")[:100]


def _load_session(conn, session_id: str) -> AssistantSession:
    state = get_session(conn, session_id)
    session = AssistantSession()
    session.pending_intent = state["pending_intent"]
    session.pending_payload = state["pending_payload"]
    return session


def _save_session(conn, session_id: str, session: AssistantSession) -> None:
    save_session(conn, session_id, session.pending_intent, session.pending_payload)


@assistant_api.post("/message")
def message():
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "Mensaje vacío"}), 400

    session_id = _session_id()
    conn = get_db()
    try:
        session = _load_session(conn, session_id)

        if is_confirmation(text):
            pending = session.confirm()
            if not pending:
                return jsonify({"ok": True, "status": "idle", "message": "No hay ninguna operación pendiente."})
            intent, payload = pending
            if intent == "create_customer":
                try:
                    with transaction() as tx:
                        customer_id = create_customer(tx, payload)
                        record(tx, action="assistant.create_customer", entity="cliente", entity_id=customer_id, details={"session_id": session_id})
                        save_session(tx, session_id, None, {})
                    return jsonify({"ok": True, "status": "executed", "intent": intent, "id": customer_id})
                except CustomerError as exc:
                    _save_session(conn, session_id, session)
                    conn.commit()
                    return jsonify({"ok": False, "status": "error", "error": str(exc)}), 400
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": False, "status": "unsupported", "error": f"Intent aún no implementado: {intent}"}), 400

        if is_cancellation(text):
            cancelled = session.cancel()
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, "status": "cancelled" if cancelled else "idle"})

        lowered = text.lower()
        if lowered.startswith("buscar cliente"):
            term = text[len("buscar cliente"):].strip()
            results = search_customers(conn, term)
            return jsonify({"ok": True, "status": "ready", "intent": "search_customers", "results": results})

        if lowered.startswith("registrar cliente"):
            payload = body.get("customer") or {}
            response = session.propose("create_customer", payload)
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, **response})

        return jsonify({
            "ok": True,
            "status": "unknown",
            "message": "No reconocí la operación. Prueba: buscar cliente <nombre> o registrar cliente.",
        })
    finally:
        conn.close()
