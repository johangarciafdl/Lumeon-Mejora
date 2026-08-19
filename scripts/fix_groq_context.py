from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "lumeon_pro/backend/services/ai_orchestrator.py"

text = AI.read_text(encoding="utf-8")

# Ensure Groq planner import exists.
anchor = "from services.invoice_delivery_service import deliver_invoice\n"
import_line = "from services.groq_planner import plan_with_groq\n"
if import_line not in text:
    if anchor not in text:
        raise SystemExit("No encontre el bloque de imports esperado")
    text = text.replace(anchor, anchor + import_line, 1)

start = text.find("def plan(text: str, db_context: dict) -> dict:")
end = text.find("\ndef _product(conn, ref):", start)
if start == -1 or end == -1:
    raise SystemExit("No encontre los limites de plan()")

new_plan = '''def plan(text: str, db_context: dict) -> dict:
    local = _local_plan(text)
    if local:
        return local

    deterministic = _local_command_plan(text)
    if deterministic:
        return deterministic

    # Groq interprets the user's natural language. Do NOT send the full
    # database context here: the free plan has an 8K TPM limit and the
    # database context can exceed it. Lumeon queries SQLite only after the
    # model returns a structured action.
    groq_context = {
        "role": "lumeon_operation_planner",
        "allowed_actions": [
            "search_customer", "search_product", "low_stock", "create_customer",
            "create_product", "update_product_price", "delete_product", "create_sale",
            "send_invoice", "refund_sale", "unknown",
        ],
    }

    groq = plan_with_groq(text, groq_context)
    if groq and str(groq.get("action") or "unknown") != "unknown":
        return groq
    if groq and str(groq.get("action") or "unknown") == "unknown":
        message = str(groq.get("message") or "").strip()
        if message:
            return groq

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return {
            "action": "unknown",
            "message": "Puedo ayudarte con clientes, productos, inventario, ventas, facturas y devoluciones. Dime qué necesitas hacer.",
        }

    prompt = (
        "Eres el planificador de LUMEON PRO. Responde SOLO JSON válido. "
        "Nunca escribas SQL ni inventes datos. Acciones: search_customer, search_product, "
        "low_stock, create_customer, create_product, update_product_price, delete_product, "
        "create_sale, send_invoice, refund_sale, unknown. Para create_sale usa items=[{referencia,cantidad}], "
        "customer_name/customer_id, phone y email cuando existan. Para update_product_price usa "
        "product_ref y price. Para delete_product usa product_ref. Para send_invoice/refund_sale usa "
        "sale_id o invoice_number. Si faltan datos, devuelve unknown con message.\\n\\n"
        + json.dumps({"request": text}, ensure_ascii=False)
    )
    payload = {
        "model": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
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
            "message": "La IA externa gratuita no respondió. Los comandos Lumeon locales siguen funcionando.",
            "detail": str(exc)[:160],
        }
'''

text = text[:start] + new_plan + text[end:]
AI.write_text(text, encoding="utf-8")
print("GROQ CONTEXT FIXED")
print("Groq now receives only a tiny planner context; SQLite remains the source of truth.")
print("No database was touched.")
