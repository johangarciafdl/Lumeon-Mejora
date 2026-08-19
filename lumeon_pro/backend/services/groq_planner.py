from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# GPT-OSS 20B is confirmed reachable on the current free-plan API key and
# supports reasoning plus structured outputs/tool use.
DEFAULT_MODEL = "openai/gpt-oss-20b"

SYSTEM_INSTRUCTION = """
Eres el cerebro operativo de LUMEON PRO, una aplicación de ventas e inventario en Colombia.
Interpreta lenguaje natural y conviértelo en UNA sola operación estructurada para Lumeon.

Nunca escribas SQL y nunca inventes datos. Usa únicamente el contexto entregado.

Acciones permitidas:
search_customer, search_product, low_stock, create_customer, create_product,
update_product_price, delete_product, create_sale, send_invoice, refund_sale, unknown.

Para create_sale usa items=[{referencia,cantidad}] y customer_id cuando exista.
Para cambios destructivos prepara la acción y deja confirmation_message claro.
Si falta información esencial, usa unknown y explica qué falta en message.

Para una conversación normal (por ejemplo, "hola") devuelve action=unknown y una respuesta natural,
breve y útil en message. No hables de APIs, modelos, suscripciones ni detalles técnicos.

Responde SOLO JSON válido.
""".strip()


def plan_with_groq(text: str, db_context: dict) -> dict | None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    prompt = (
        SYSTEM_INSTRUCTION
        + "\n\nCONTEXTO ACTUAL:\n"
        + json.dumps(db_context, ensure_ascii=False, separators=(",", ":"))
        + "\n\nSOLICITUD:\n"
        + text
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_completion_tokens": int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "2048")),
        "response_format": {"type": "json_object"},
        "reasoning_effort": os.getenv("GROQ_REASONING_EFFORT", "medium"),
        "include_reasoning": False,
    }

    req = Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=float(os.getenv("GROQ_TIMEOUT", "30"))) as resp:
            raw = resp.read().decode("utf-8")
        response = json.loads(raw)
        choice = response["choices"][0]
        message = choice.get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            return {
                "action": "unknown",
                "message": "No pude interpretar la solicitud en este momento. Puedes intentarlo de nuevo.",
                "detail": f"finish_reason={choice.get('finish_reason')}; reasoning_hidden={message.get('reasoning') is not None}",
            }
        result = json.loads(content)
        if not isinstance(result, dict):
            return {"action": "unknown", "message": "No pude interpretar la solicitud."}
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return {
            "action": "unknown",
            "message": "No pude interpretar la solicitud en este momento. Puedes intentarlo de nuevo.",
            "detail": str(exc)[:160],
        }
