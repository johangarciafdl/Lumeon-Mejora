from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db, transaction
from services.assistant_workflow import AssistantSession, is_cancellation, is_confirmation
from services.assistant_session_service import get_session, save_session
from services.audit_service import record
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import search_customers, create_customer, CustomerError
from services.product_service import search_products, low_stock

assistant_api = Blueprint("assistant_api", __name__, url_prefix="/api/v2/assistant")


def _session_id(actor_id: int) -> str:
    supplied = request.headers.get("X-Assistant-Session", "default")[:100]
    return f"user:{actor_id}:{supplied}"


def _load_session(conn, session_id: str) -> AssistantSession:
    state = get_session(conn, session_id)
    assistant_session = AssistantSession()
    assistant_session.pending_intent = state["pending_intent"]
    assistant_session.pending_payload = state["pending_payload"]
    return assistant_session


def _save_session(conn, session_id: str, assistant_session: AssistantSession) -> None:
    save_session(conn, session_id, assistant_session.pending_intent, assistant_session.pending_payload)


@assistant_api.post("/message")
def message():
    try:
        actor = current_actor()
    except AuthenticationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 401

    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "Mensaje vacío"}), 400

    session_id = _session_id(actor.id)
    conn = get_db()
    try:
        assistant_session = _load_session(conn, session_id)

        if is_confirmation(text):
            pending = assistant_session.confirm()
            if not pending:
                return jsonify({"ok": True, "status": "idle", "message": "No hay ninguna operación pendiente."})
            intent, payload = pending
            try:
                require(actor, intent)
            except PermissionError as exc:
                _save_session(conn, session_id, assistant_session)
                conn.commit()
                return jsonify({"ok": False, "status": "forbidden", "error": str(exc)}), 403

            if intent == "create_customer":
                try:
                    with transaction() as tx:
                        customer_id = create_customer(tx, payload)
                        record(tx, actor_id=actor.id, action="assistant.create_customer", entity="cliente", entity_id=customer_id, details={"session_id": session_id})
                        save_session(tx, session_id, None, {})
                    return jsonify({"ok": True, "status": "executed", "intent": intent, "id": customer_id})
                except CustomerError as exc:
                    _save_session(conn, session_id, assistant_session)
                    conn.commit()
                    return jsonify({"ok": False, "status": "error", "error": str(exc)}), 400
            _save_session(conn, session_id, assistant_session)
            conn.commit()
            return jsonify({"ok": False, "status": "unsupported", "error": f"Intent aún no implementado: {intent}"}), 400

        if is_cancellation(text):
            cancelled = assistant_session.cancel()
            _save_session(conn, session_id, assistant_session)
            conn.commit()
            return jsonify({"ok": True, "status": "cancelled" if cancelled else "idle"})

        lowered = text.lower()
        if lowered.startswith("buscar cliente"):
            require(actor, "search_customer")
            term = text[len("buscar cliente"):].strip()
            return jsonify({"ok": True, "status": "ready", "intent": "search_customers", "results": search_customers(conn, term)})

        if lowered.startswith("buscar producto"):
            require(actor, "search_product")
            term = text[len("buscar producto"):].strip()
            return jsonify({"ok": True, "status": "ready", "intent": "search_products", "results": search_products(conn, term)})

        if "stock bajo" in lowered:
            require(actor, "view_inventory")
            return jsonify({"ok": True, "status": "ready", "intent": "low_stock", "results": low_stock(conn)})

        if lowered.startswith("registrar cliente"):
            require(actor, "create_customer")
            payload = body.get("customer") or {}
            response = assistant_session.propose("create_customer", payload)
            _save_session(conn, session_id, assistant_session)
            conn.commit()
            return jsonify({"ok": True, **response})

        return jsonify({"ok": True, "status": "unknown", "message": "No reconocí la operación. Prueba: buscar cliente, buscar producto, stock bajo o registrar cliente."})
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception:
        assistant_api.logger.exception("assistant message failed")
        return jsonify({"ok": False, "error": "No se pudo procesar la solicitud"}), 500
    finally:
        conn.close()
