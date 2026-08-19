from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.5-flash-lite"

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "search_customer", "search_product", "low_stock",
                "create_customer", "create_product", "update_product_price",
                "delete_product", "create_sale", "send_invoice", "refund_sale", "unknown",
            ],
        },
        "query": {"type": "string"},
        "customer_id": {"type": "integer"},
        "customer_name": {"type": "string"},
        "phone": {"type": "string"},
        "email": {"type": "string"},
        "product_ref": {"type": "string"},
        "product_name": {"type": "string"},
        "price": {"type": "number"},
        "sale_id": {"type": "integer"},
        "invoice_number": {"type": "string"},
        "reason": {"type": "string"},
        "confirmation_message": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "referencia": {"type": "string"},
                    "cantidad": {"type": "integer"},
                },
                "required": ["referencia", "cantidad"],
            },
        },
        "message": {"type": "string"},
    },
    "required": [
        "action", "query", "customer_id", "customer_name", "phone", "email",
        "product_ref", "product_name", "price", "sale_id", "invoice_number", "reason",
        "confirmation_message", "items", "message",
    ],
    "propertyOrdering": [
        "action", "query", "customer_id", "customer_name", "phone", "email",
        "product_ref", "product_name", "price", "sale_id", "invoice_number", "reason",
        "confirmation_message", "items", "message",
    ],
}

SYSTEM_INSTRUCTION = """
Eres el cerebro operativo de LUMEON PRO, una aplicación de ventas e inventario en Colombia.
Tu trabajo es interpretar lenguaje natural y convertirlo en UNA sola operación estructurada.

Reglas:
- No escribas SQL.
- No inventes clientes, productos, precios, stock, IDs o facturas.
- Usa los datos del contexto para resolver nombres, referencias e IDs.
- Para consultas simples usa search_customer, search_product o low_stock.
- Para crear una venta usa create_sale con items [{referencia,cantidad}] y, cuando exista,
  customer_id. Usa también phone/email si el usuario los proporciona explícitamente.
- Para cambiar precios, borrar productos o devolver ventas, prepara la acción pero deja
  confirmation_message claro y breve.
- Si falta información esencial, usa unknown y explica qué falta en message.
- No ejecutes acciones: solo prepara la intención para que LUMEON la valide.
- Responde siempre en español.
""".strip()


def _clean(value, default=""):
    if value is None:
        return default
    return value


def plan_with_gemini(text: str, db_context: dict) -> dict | None:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None

    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = (
        SYSTEM_INSTRUCTION
        + "\n\nCONTEXTO ACTUAL DE LUMEON:\n"
        + json.dumps(db_context, ensure_ascii=False, separators=(",", ":"))
        + "\n\nSOLICITUD DEL USUARIO:\n"
        + text
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": ACTION_SCHEMA,
            "thinkingConfig": {"thinkingLevel": os.getenv("GEMINI_THINKING_LEVEL", "medium").upper()},
        },
    }

    req = Request(
        GEMINI_URL.format(model=model),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=float(os.getenv("GEMINI_TIMEOUT", "25"))) as resp:
            raw = resp.read().decode("utf-8")
        response = json.loads(raw)
        parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text_out = "".join(str(p.get("text", "")) for p in parts if p.get("text"))
        if not text_out.strip():
            return {"action": "unknown", "message": "Gemini no devolvió una intención válida."}
        result = json.loads(text_out)
        if not isinstance(result, dict):
            return {"action": "unknown", "message": "Gemini devolvió una estructura inválida."}
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return {
            "action": "unknown",
            "message": "Gemini no respondió correctamente; usaré el modo de respaldo.",
            "detail": str(exc)[:160],
        }
