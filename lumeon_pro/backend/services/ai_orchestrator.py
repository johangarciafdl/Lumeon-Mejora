from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.audit_service import record as audit
from services.customer_service import create_customer, search_customers
from services.product_service import create_product, search_products
from services.return_service import return_sale
from services.sale_service import SaleError, create_sale
from services.invoice_delivery_service import deliver_invoice

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
CONFIRM_ACTIONS = {"update_product_price", "delete_product", "refund_sale"}


def _local_plan(text: str) -> dict | None:
    t = text.lower().strip()
    if t in {"sí", "si", "confirmar", "confirmado", "hazlo"}:
        return {"action": "confirm_pending"}
    if t in {"no", "cancelar", "cancela", "cancelado"}:
        return {"action": "cancel_pending"}
    return None


def context(conn) -> dict:
    return {
        "customers": [dict(r) for r in conn.execute(
            "SELECT id,nombre,documento,telefono,email,ciudad FROM clientes ORDER BY id DESC LIMIT 100"
        ).fetchall()],
        "products": [dict(r) for r in conn.execute(
            "SELECT id,nombre,referencia,precio_venta,stock,stock_minimo,categoria FROM productos ORDER BY id DESC LIMIT 100"
        ).fetchall()],
        "sales": [dict(r) for r in conn.execute(
            "SELECT id,numero_factura,cliente_nombre,cliente_telefono,total,estado FROM ventas ORDER BY id DESC LIMIT 50"
        ).fetchall()],
    }


def plan(text: str, db_context: dict) -> dict:
    local = _local_plan(text)
    if local:
        return local
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {"action": "unknown", "message": "La IA gratuita no está configurada. Puedo usar los comandos directos del asistente."}

    prompt = (
        "Eres el planificador de LUMEON PRO. Responde SOLO JSON válido. "
        "Nunca escribas SQL ni inventes datos. Acciones: search_customer, search_product, "
        "create_customer, create_product, update_product_price, delete_product, create_sale, "
        "send_invoice, refund_sale, unknown. Para create_sale usa items=[{referencia,cantidad}], "
        "customer_name/customer_id, phone y email cuando existan. Para update_product_price usa "
        "product_ref y price. Para delete_product usa product_ref. Para send_invoice/refund_sale usa "
        "sale_id o invoice_number. Si faltan datos, devuelve unknown con message.\n\n"
        + json.dumps({"request": text, "context": db_context}, ensure_ascii=False)
    )
    payload = {
        "model": os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_tokens": 700,
    }
    req = Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://lumeon.pythonanywhere.com"),
            "X-Title": "LUMEON PRO",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=float(os.getenv("OPENROUTER_TIMEOUT", "25"))) as resp:
            raw = resp.read().decode("utf-8")
        content = json.loads(raw)["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content[4:] if content.startswith("json") else content
        result = json.loads(content)
        return result if isinstance(result, dict) else {"action": "unknown", "message": "Respuesta IA inválida"}
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return {
            "action": "unknown",
            "message": "La IA gratuita no respondió o alcanzó su límite. Los comandos directos siguen disponibles.",
            "detail": str(exc)[:160],
        }


def _product(conn, ref):
    ref = str(ref or "").strip()
    return conn.execute(
        "SELECT * FROM productos WHERE referencia=? OR CAST(id AS TEXT)=? LIMIT 1",
        (ref, ref),
    ).fetchone() if ref else None


def _sale(conn, sale_id=None, invoice_number=None):
    if sale_id:
        return conn.execute("SELECT * FROM ventas WHERE id=?", (int(sale_id),)).fetchone()
    return conn.execute("SELECT * FROM ventas WHERE numero_factura=?", (str(invoice_number or "").strip(),)).fetchone()


def send_invoice_for_sale(conn, sale_id: int, retry: bool = False) -> dict:
    sale = conn.execute("SELECT * FROM ventas WHERE id=?", (sale_id,)).fetchone()
    if not sale:
        return {"status": "NOT_FOUND", "error": "Venta no encontrada"}
    items = [dict(r) for r in conn.execute(
        "SELECT referencia,nombre,cantidad,precio_compra,precio_venta FROM venta_items WHERE venta_id=? ORDER BY id",
        (sale_id,),
    ).fetchall()]
    result = deliver_invoice(
        conn,
        sale_id=sale_id,
        invoice_number=sale["numero_factura"],
        customer_name=sale["cliente_nombre"] or "Cliente",
        phone=sale["cliente_telefono"] or "",
        items=items,
        total=float(sale["total"] or 0),
        force_retry=retry,
    )
    delivery = result.get("whatsapp")
    return {"status": getattr(delivery, "status", None), "error": getattr(delivery, "error", None)}


def execute(conn, actor_id: int, action: dict, session_state: dict) -> tuple[dict, dict]:
    name = str(action.get("action") or "unknown")

    if name == "confirm_pending":
        action = session_state.pop("pending_ai_action", None)
        if not action:
            return {"ok": True, "status": "idle", "message": "No hay ninguna operación pendiente."}, session_state
        name = str(action.get("action") or "unknown")
    elif name == "cancel_pending":
        session_state.pop("pending_ai_action", None)
        return {"ok": True, "status": "cancelled", "message": "Operación cancelada."}, session_state

    if name in CONFIRM_ACTIONS:
        session_state["pending_ai_action"] = action
        return {
            "ok": True,
            "status": "confirmation_required",
            "intent": name,
            "message": action.get("confirmation_message") or f"Voy a ejecutar {name}. ¿Confirmas?",
        }, session_state

    if name == "search_customer":
        term = str(action.get("query") or action.get("customer_query") or action.get("customer_name") or "").strip()
        return {"ok": True, "status": "ready", "intent": name, "results": search_customers(conn, term, 100)}, session_state

    if name == "search_product":
        term = str(action.get("query") or action.get("product_ref") or action.get("product_name") or "").strip()
        return {"ok": True, "status": "ready", "intent": name, "results": search_products(conn, term, 100)}, session_state

    if name == "create_customer":
        customer_id = create_customer(conn, action)
        conn.commit()
        audit(conn, actor_id=actor_id, action="assistant.create_customer", entity="cliente", entity_id=customer_id, details={"source": "ai"})
        conn.commit()
        return {"ok": True, "status": "executed", "intent": name, "id": customer_id, "message": f"Cliente creado con ID {customer_id}."}, session_state

    if name == "create_product":
        product_id = create_product(conn, action)
        conn.commit()
        audit(conn, actor_id=actor_id, action="assistant.create_product", entity="producto", entity_id=product_id, details={"source": "ai"})
        conn.commit()
        return {"ok": True, "status": "executed", "intent": name, "id": product_id, "message": f"Producto creado con ID {product_id}."}, session_state

    if name == "create_sale":
        items = action.get("items") or []
        if not items:
            raise SaleError("Indica productos y cantidades")
        normalized = []
        for item in items:
            product = _product(conn, item.get("referencia") or item.get("product_ref") or item.get("id"))
            if not product:
                raise SaleError(f"Producto no encontrado: {item.get('referencia') or item.get('id')}")
            qty = int(item.get("cantidad") or item.get("quantity") or 0)
            if qty <= 0:
                raise SaleError("La cantidad debe ser mayor que cero")
            normalized.append({"referencia": product["referencia"], "cantidad": qty})
        sale_id = create_sale(conn, data={
            "cliente_id": action.get("customer_id"),
            "cliente_nombre": str(action.get("customer_name") or "").strip(),
            "cliente_email": str(action.get("email") or "").strip(),
            "cliente_telefono": str(action.get("phone") or "").strip(),
            "items": normalized,
            "forma_pago": str(action.get("forma_pago") or "Contado"),
            "estado": str(action.get("estado") or "Pendiente"),
            "notas": str(action.get("notas") or ""),
        }, user_id=actor_id)
        conn.commit()
        delivery = send_invoice_for_sale(conn, sale_id)
        conn.commit()
        return {"ok": True, "status": "executed", "intent": name, "id": sale_id, "invoice_delivery": {"whatsapp": delivery}, "message": f"Venta {sale_id} creada y procesada."}, session_state

    if name == "send_invoice":
        sale = _sale(conn, action.get("sale_id"), action.get("invoice_number"))
        if not sale:
            return {"ok": False, "status": "validation_error", "error": "Venta/factura no encontrada"}, session_state
        delivery = send_invoice_for_sale(conn, int(sale["id"]), bool(action.get("retry")))
        conn.commit()
        return {"ok": delivery["status"] in {"SENT", "ALREADY_SENT"}, "status": "executed", "intent": name, "id": int(sale["id"]), "invoice_delivery": {"whatsapp": delivery}, "message": f"Factura {sale['numero_factura']}: {delivery['status']}"}, session_state

    if name == "update_product_price":
        product = _product(conn, action.get("product_ref"))
        if not product:
            return {"ok": False, "status": "validation_error", "error": "Producto no encontrado"}, session_state
        price = float(action.get("price"))
        if price < 0:
            return {"ok": False, "status": "validation_error", "error": "Precio inválido"}, session_state
        conn.execute("UPDATE productos SET precio_venta=? WHERE id=?", (price, product["id"]))
        audit(conn, actor_id=actor_id, action="product.price_updated", entity="producto", entity_id=product["id"], details={"old_price": product["precio_venta"], "new_price": price, "source": "ai"})
        conn.commit()
        return {"ok": True, "status": "executed", "intent": name, "id": int(product["id"]), "message": f"Precio actualizado a {price}."}, session_state

    if name == "delete_product":
        product = _product(conn, action.get("product_ref"))
        if not product:
            return {"ok": False, "status": "validation_error", "error": "Producto no encontrado"}, session_state
        used = conn.execute("SELECT COUNT(*) FROM venta_items WHERE producto_id=?", (product["id"],)).fetchone()[0]
        if used:
            return {"ok": False, "status": "validation_error", "error": "Tiene ventas históricas; déjalo con stock 0 en lugar de eliminarlo."}, session_state
        conn.execute("DELETE FROM productos WHERE id=?", (product["id"],))
        audit(conn, actor_id=actor_id, action="product.deleted", entity="producto", entity_id=product["id"], details={"source": "ai"})
        conn.commit()
        return {"ok": True, "status": "executed", "intent": name, "id": int(product["id"]), "message": "Producto eliminado."}, session_state

    if name == "refund_sale":
        sale = _sale(conn, action.get("sale_id"), action.get("invoice_number"))
        if not sale:
            return {"ok": False, "status": "validation_error", "error": "Venta no encontrada"}, session_state
        result = return_sale(conn, sale_id=int(sale["id"]), user_id=actor_id, idempotency_key=str(action.get("idempotency_key") or f"ai-refund:{actor_id}:{sale['id']}"), reason=str(action.get("reason") or ""))
        conn.commit()
        return {"ok": True, "status": "executed", "intent": name, "id": int(sale["id"]), "return": result, "message": "Devolución procesada."}, session_state

    return {"ok": True, "status": "unknown", "message": action.get("message") or "No entendí la operación. Puedo buscar, crear, actualizar precios, registrar ventas, enviar facturas y gestionar devoluciones."}, session_state
