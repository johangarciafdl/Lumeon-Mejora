from __future__ import annotations

import json
import os

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"

SYSTEM_INSTRUCTION = """
Eres el cerebro operativo de LUMEON PRO, una aplicación de ventas e inventario en Colombia.
Tu trabajo NO es inventar datos ni responder con datos de productos/clientes.
Tu trabajo es interpretar la solicitud del usuario y convertirla en UNA operación estructurada.

REGLAS OBLIGATORIAS:
1. Nunca inventes nombres, precios, stock, teléfonos, IDs, facturas ni ningún dato del negocio.
2. Nunca escribas SQL.
3. Para búsquedas, devuelve SOLO la acción y el término de búsqueda. Lumeon consultará la base real.
4. Para una pregunta sobre un producto o cliente, NO respondas con datos del ejemplo del prompt.
   Devuelve la acción correspondiente para que Lumeon consulte la base.
5. Para una conversación normal como "hola", devuelve action="unknown" y una respuesta natural breve en message.
6. Si falta información para ejecutar una operación, devuelve action="unknown" y explica qué falta en message.
7. Para operaciones destructivas, prepara la acción y un confirmation_message claro.
8. Devuelve exclusivamente JSON válido y nada fuera del JSON.

ACCIONES PERMITIDAS:
search_customer, search_product, low_stock, create_customer, create_product,
update_product_price, delete_product, create_sale, send_invoice, refund_sale, unknown.

FORMATO DE ACCIONES:
- search_customer: query
- search_product: query
- low_stock: sin campos extra
- create_customer: customer_name, document, phone, email, address, city
- create_product: name, reference/product_ref, description, category, purchase_price, sale_price, stock, min_stock
- update_product_price: product_ref, price, confirmation_message
- delete_product: product_ref, confirmation_message
- create_sale: customer_id o customer_name, phone/email si fueron dados, items=[{referencia,cantidad}], forma_pago, notas
- send_invoice: sale_id o invoice_number, retry opcional
- refund_sale: sale_id o invoice_number, reason, confirmation_message

IMPORTANTE PARA create_sale:
Puedes entender lenguaje libre como "dos unidades", "2", "dos de la crema", etc.
No necesitas una frase exacta. Si identificas un producto por nombre, referencia o ID,
colócalo en items como referencia textual; Lumeon lo resolverá contra la base real.
""".strip()


def plan_with_groq(text: str, db_context: dict) -> dict | None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = (
        SYSTEM_INSTRUCTION
        + "\n\nCONTEXTO DISPONIBLE PARA DESAMBIGUAR NOMBRES Y REFERENCIAS (NO COPIES DATOS COMO SI LOS HUBIERAS CONSULTADO):\n"
        + json.dumps(db_context, ensure_ascii=False, separators=(",", ":"))
        + "\n\nSOLICITUD DEL USUARIO:\n"
        + text
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_completion_tokens": int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "4096")),
        "response_format": {"type": "json_object"},
        "reasoning_effort": os.getenv("GROQ_REASONING_EFFORT", "low"),
        "include_reasoning": False,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "LUMEON-PRO/2",
    }

    try:
        response = requests.post(
            GROQ_URL,
            headers=headers,
            json=payload,
            timeout=float(os.getenv("GROQ_TIMEOUT", "30")),
        )
        response.raise_for_status()
        raw = response.json()
        choice = raw["choices"][0]
        message = choice.get("message") or {}
        content = (message.get("content") or "").strip()

        if not content:
            return {
                "action": "unknown",
                "message": "No pude interpretar la solicitud en este momento. Puedes intentarlo de nuevo.",
                "detail": f"finish_reason={choice.get('finish_reason')}",
            }

        result = json.loads(content)
        if not isinstance(result, dict):
            return {"action": "unknown", "message": "No pude interpretar la solicitud."}

        allowed = {
            "search_customer", "search_product", "low_stock", "create_customer",
            "create_product", "update_product_price", "delete_product", "create_sale",
            "send_invoice", "refund_sale", "unknown",
        }
        action = str(result.get("action") or "unknown")
        if action not in allowed:
            result["action"] = "unknown"
            result.setdefault("message", "No pude interpretar la operación solicitada.")
        return result

    except requests.HTTPError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        return {
            "action": "unknown",
            "message": "No pude comunicarme con el motor de IA en este momento.",
            "detail": f"HTTP {exc.response.status_code if exc.response is not None else 'error'}: {detail}",
        }
    except (requests.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return {
            "action": "unknown",
            "message": "No pude interpretar la solicitud en este momento. Puedes intentarlo de nuevo.",
            "detail": str(exc)[:300],
        }
