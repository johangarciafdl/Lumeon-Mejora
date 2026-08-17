from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db, transaction
from services.assistant_workflow import AssistantSession, is_cancellation, is_confirmation
from services.assistant_session_service import get_session, save_session
from services.audit_service import record
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.customer_service import CustomerError, create_customer, search_customers
from services.product_service import ProductError, create_product, low_stock, search_products
from services.assistant_parser import parse_create_customer, parse_create_product

assistant_api = Blueprint("assistant_api", __name__, url_prefix="/api/v2/assistant")


def _session_id(actor_id: int) -> str:
    supplied = request.headers.get("X-Assistant-Session", "default")[:100]
    return f"user:{actor_id}:{supplied}"


def _load_session(conn, session_id: str) -> AssistantSession:
    state = get_session(conn, session_id)
    session = AssistantSession()
    session.pending_intent = state["pending_intent"]
    session.pending_payload = state["pending_payload"]
    draft = session.pending_payload.pop("__sale_draft", None)
    if draft:
        from services.assistant_sale_builder import SaleDraft
        session.sale_draft = SaleDraft(
            customer_id=draft.get("customer_id"),
            customer_name=draft.get("customer_name", ""),
            items=draft.get("items", []),
        )
    return session


def _save_session(conn, session_id: str, session: AssistantSession) -> None:
    payload = dict(session.pending_payload)
    if session.sale_draft is not None:
        payload["__sale_draft"] = session.sale_draft.summary()
    save_session(conn, session_id, session.pending_intent, payload)


def _json_customer(body: dict):
    customer = body.get("customer") or {}
    if not customer.get("id"):
        raise ValueError("Debes proporcionar customer.id")
    return customer


def _json_product(body: dict):
    product = body.get("product") or {}
    if not product.get("id"):
        raise ValueError("Debes proporcionar product.id")
    return product


@assistant_api.post("/message")
def message():
    try:
        actor = current_actor()
    except AuthenticationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 401

    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()
    if not text or len(text) > 500:
        return jsonify({"ok": False, "error": "Mensaje vacío o demasiado largo"}), 400

    session_id = _session_id(actor.id)
    conn = get_db()
    try:
        session = _load_session(conn, session_id)
        lowered = text.lower()

        if is_confirmation(text):
            pending = session.confirm()
            if not pending:
                return jsonify({"ok": True, "status": "idle", "message": "No hay ninguna operación pendiente."})
            intent, payload = pending
            require(actor, intent)
            try:
                with transaction() as tx:
                    if intent == "create_customer":
                        entity_id = create_customer(tx, payload)
                        entity = "cliente"
                    elif intent == "create_product":
                        entity_id = create_product(tx, payload)
                        entity = "producto"
                    elif intent == "create_sale":
                        from services.sale_service import create_sale
                        entity_id = create_sale(tx, data=payload, user_id=actor.id)
                        entity = "venta"
                    else:
                        raise ValueError(f"Intent no soportado: {intent}")
                    record(tx, actor_id=actor.id, action=f"assistant.{intent}", entity=entity, entity_id=entity_id, details={"session_id": session_id})
                    save_session(tx, session_id, None, {})
                return jsonify({"ok": True, "status": "executed", "intent": intent, "entity": entity, "id": entity_id})
            except (CustomerError, ProductError, ValueError) as exc:
                _save_session(conn, session_id, session)
                conn.commit()
                return jsonify({"ok": False, "status": "validation_error", "error": str(exc)}), 400

        if is_cancellation(text):
            cancelled = session.cancel()
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, "status": "cancelled" if cancelled else "idle"})

        if lowered.startswith("iniciar venta"):
            require(actor, "create_sale")
            try:
                response = session.start_sale(_json_customer(body))
            except ValueError as exc:
                return jsonify({"ok": False, "status": "needs_input", "error": str(exc)}), 400
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, **response, "message": "Cliente seleccionado. Agrega productos y cantidades."})

        if lowered.startswith("agregar producto"):
            require(actor, "create_sale")
            try:
                product = _json_product(body)
                quantity = int(body.get("quantity", 0))
                response = session.add_sale_item(product, quantity)
            except (ValueError, TypeError) as exc:
                return jsonify({"ok": False, "status": "needs_input", "error": str(exc)}), 400
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, **response})

        if lowered in {"resumen venta", "resumen de venta", "total venta"}:
            return jsonify({"ok": True, **session.sale_summary()})

        if lowered in {"confirmar venta", "crear venta"}:
            require(actor, "create_sale")
            try:
                response = session.propose_sale()
            except ValueError as exc:
                return jsonify({"ok": False, "status": "needs_input", "error": str(exc)}), 400
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, **response})

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
            payload = body.get("customer") or parse_create_customer(text)
            if not payload.get("nombre"):
                return jsonify({"ok": True, "status": "needs_input", "message": "Indica al menos el nombre."})
            response = session.propose("create_customer", payload)
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, **response})

        if lowered.startswith("registrar producto"):
            require(actor, "create_product")
            payload = body.get("product") or parse_create_product(text)
            if not payload.get("nombre") or not payload.get("referencia"):
                return jsonify({"ok": True, "status": "needs_input", "message": "Indica nombre y referencia."})
            response = session.propose("create_product", payload)
            _save_session(conn, session_id, session)
            conn.commit()
            return jsonify({"ok": True, **response})

        return jsonify({"ok": True, "status": "unknown", "message": "Puedo buscar clientes/productos, consultar stock, registrar datos o construir una venta."})
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except Exception:
        assistant_api.logger.exception("assistant message failed")
        return jsonify({"ok": False, "error": "No se pudo procesar la solicitud"}), 500
    finally:
        conn.close()
