from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.audit_service import record as audit
from services.customer_service import create_customer, search_customers
from services.product_service import create_product, search_products, low_stock
from services.return_service import return_sale
from services.sale_service import SaleError, create_sale
from services.invoice_delivery_service import deliver_invoice

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
CONFIRM_ACTIONS = {"update_product_price", "delete_product", "refund_sale"}


def _local_plan(text: str) -> dict | None:
    t = " ".join(str(text or "").strip().split())
    low = t.lower()

    if low in {"sí", "si", "confirmar", "confirmado", "hazlo"}:
        return {"action": "confirm_pending"}
    if low in {"no", "cancelar", "cancela", "cancelado"}:
        return {"action": "cancel_pending"}
    return None


def _local_command_plan(text: str) -> dict | None:
    t = " ".join(str(text or "").strip().split())
    low = t.lower()

    if low in {"stock bajo", "inventario bajo", "productos con stock bajo", "que productos tienen stock bajo"}:
        return {"action": "low_stock"}

    for prefix in ("buscar cliente ", "busca cliente ", "cliente "):
        if low.startswith(prefix):
            query = t[len(prefix):].strip()
            if query:
                return {"action": "search_customer", "query": query}

    for prefix in ("buscar producto ", "busca producto ", "producto "):
        if low.startswith(prefix):
            query = t[len(prefix):].strip()
            if query:
                return {"action": "search_product", "query": query}

    price_match = re.search(
        r"(?:cambia|cambiar|actualiza|actualizar)\s+(?:el\s+)?precio(?:\s+del\s+producto)?\s+([\w.-]+)\s+(?:a|por)\s*\$?([0-9]+(?:[.,][0-9]+)?)",
        low,
    )
    if price_match:
        raw_price = price_match.group(2).replace(".", "").replace(",", ".")
        price = float(raw_price)
        ref = price_match.group(1)
        return {
            "action": "update_product_price",
            "product_ref": ref,
            "price": price,
            "confirmation_message": f"Voy a cambiar el precio del producto {ref} a ${price:,.0f}. ¿Confirmas?",
        }

    delete_match = re.search(
        r"(?:elimina|eliminar|borra|borrar)\s+(?:el\s+)?producto\s+([\w.-]+)",
        low,
    )
    if delete_match:
        ref = delete_match.group(1)
        return {
            "action": "delete_product",
            "product_ref": ref,
            "confirmation_message": f"Voy a eliminar el producto {ref}. ¿Confirmas?",
        }

    invoice_match = re.search(
        r"(?:envia|enviar|manda|mandar)\s+(?:la\s+)?factura\s+([\w.-]+)",
        low,
    )
    if invoice_match:
        ref = invoice_match.group(1)
        if ref.isdigit():
            return {"action": "send_invoice", "sale_id": int(ref)}
        return {"action": "send_invoice", "invoice_number": ref}

    refund_match = re.search(
        r"(?:devuelve|devolver|anula|anular)\s+(?:la\s+)?venta\s+([0-9]+)",
        low,
    )
    if refund_match:
        sale_id = int(refund_match.group(1))
        return {
            "action": "refund_sale",
            "sale_id": sale_id,
            "confirmation_message": f"Voy a devolver la venta {sale_id} y reponer inventario. ¿Confirmas?",
        }

    if low.startswith(("venta ", "registrar venta", "registra venta", "crear venta", "crea venta")):
        customer_name = ""
        customer_id = None
        phone = ""
        email = ""

        customer_id_match = re.search(r"(?:cliente|comprador)\s+(?:id\s*)?(\d+)\b", t, re.I)
        if customer_id_match:
            customer_id = int(customer_id_match.group(1))

        name_match = re.search(
            r"(?:para|cliente|comprador)\s+(.+?)(?=\s+(?:telefono|tel|correo|email|productos?|items?)\b|$)",
            t,
            re.I,
        )
        if name_match and not customer_id:
            candidate = name_match.group(1).strip()
            if not candidate.lower().startswith("id "):
                customer_name = candidate

        phone_match = re.search(r"(?:telefono|tel|whatsapp)\s*[:=]?\s*([+0-9][0-9\s-]{8,16})", t, re.I)
        if phone_match:
            phone = phone_match.group(1).strip()

        email_match = re.search(r"(?:correo|email)\s*[:=]?\s*([^\s,;]+@[^\s,;]+)", t, re.I)
        if email_match:
            email = email_match.group(1).strip()

        items_match = re.search(r"(?:productos?|items?)\s*[:=]?\s*(.+)$", t, re.I)
        items = []
        if items_match:
            raw_items = items_match.group(1)
            for token in re.split(r"[,;]+\s*", raw_items):
                token = token.strip()
                if not token:
                    continue
                m = (
                    re.fullmatch(r"(?:id\s*)?([\w.-]+)\s*(?:x|\*)\s*(\d+)", token, re.I)
                    or re.fullmatch(r"(?:id\s*)?([\w.-]+)\s*:\s*(\d+)", token, re.I)
                )
                if m:
                    items.append({"referencia": m.group(1), "cantidad": int(m.group(2))})

        if items:
            return {
                "action": "create_sale",
                "customer_id": customer_id,
                "customer_name": customer_name,
                "phone": phone,
                "email": email,
                "items": items,
            }

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

    deterministic = _local_command_plan(text)
    if deterministic:
        return deterministic

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {
            "action": "unknown",
            "message": "No necesito una suscripción para operar. Puedo ejecutar comandos Lumeon directos como buscar, stock bajo, cambiar precios, registrar ventas, enviar facturas y devolver ventas.",
        }

    prompt = (
        "Eres el planificador de LUMEON PRO. Responde SOLO JSON válido. "
        "Nunca escribas SQL ni inventes datos. Acciones: search_customer, search_product, "
        "low_stock, create_customer, create_product, update_product_price, delete_product, "
        "create_sale, send_invoice, refund_sale, unknown. Para create_sale usa items=[{referencia,cantidad}], "
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
            "message": "La IA externa gratuita no respondió o alcanzó su límite. Los comandos Lumeon locales siguen funcionando.",
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

    if name == "low_stock":
        return {"ok": True, "status": "ready", "intent": name, "results": low_stock(conn, 100), "message": "Productos con stock bajo."}, session_state

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

        customer = None
        if action.get("customer_id"):
            customer = conn.execute(
                "SELECT id,nombre,telefono,email FROM clientes WHERE id=? LIMIT 1",
                (int(action["customer_id"]),),
            ).fetchone()
        elif action.get("customer_name"):
            matches = conn.execute(
                "SELECT id,nombre,telefono,email FROM clientes WHERE LOWER(nombre)=LOWER(?) ORDER BY id DESC LIMIT 2",
                (str(action["customer_name"]).strip(),),
            ).fetchall()
            if len(matches) == 1:
                customer = matches[0]

        customer_id = int(customer["id"]) if customer else action.get("customer_id")
        customer_name = str(action.get("customer_name") or (customer["nombre"] if customer else "")).strip()
        phone = str(action.get("phone") or (customer["telefono"] if customer else "")).strip()
        email = str(action.get("email") or (customer["email"] if customer else "")).strip()

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
            "cliente_id": customer_id,
            "cliente_nombre": customer_name,
            "cliente_email": email,
            "cliente_telefono": phone,
            "items": normalized,
            "forma_pago": str(action.get("forma_pago") or "Contado"),
            "estado": str(action.get("estado") or "Pendiente"),
            "notas": str(action.get("notas") or ""),
        }, user_id=actor_id)
        conn.commit()
        delivery = send_invoice_for_sale(conn, sale_id)
        conn.commit()
        return {
            "ok": True,
            "status": "executed",
            "intent": name,
            "id": sale_id,
            "invoice_delivery": {"whatsapp": delivery},
            "message": f"Venta {sale_id} creada y procesada. WhatsApp: {delivery.get('status') or 'NO_ENVIADO'}.",
        }, session_state

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

    return {"ok": True, "status": "unknown", "message": action.get("message") or "No entendí la operación. Puedo buscar, consultar stock, actualizar precios, registrar ventas, enviar facturas y gestionar devoluciones."}, session_state
