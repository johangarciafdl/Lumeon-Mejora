from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "lumeon_pro/backend/services/ai_orchestrator.py"

text = AI.read_text(encoding="utf-8")

# Add Groq planner import.
anchor = "from services.invoice_delivery_service import deliver_invoice\n"
new_import = anchor + "from services.groq_planner import plan_with_groq\n"
if "from services.groq_planner import plan_with_groq" not in text:
    if anchor not in text:
        raise SystemExit("No encontre el bloque de imports esperado")
    text = text.replace(anchor, new_import, 1)

# Insert Groq before Gemini/OpenRouter fallbacks, and collapse duplicate Gemini calls
# created during the previous integration attempt.
start = text.find("    gemini = plan_with_gemini(text, db_context)")
if start != -1:
    fallback = text.find('    key = os.getenv("OPENROUTER_API_KEY", "").strip()', start)
    if fallback == -1:
        raise SystemExit("No encontre el fallback OPENROUTER")
    replacement = '''    groq = plan_with_groq(text, db_context)\n    if groq:\n        return groq\n\n    gemini = plan_with_gemini(text, db_context)\n    if gemini and str(gemini.get("action") or "unknown") != "unknown":\n        return gemini\n\n'''
    text = text[:start] + replacement + text[fallback:]
else:
    marker = "    deterministic = _local_command_plan(text)\n    if deterministic:\n        return deterministic\n\n"
    if marker not in text:
        raise SystemExit("No encontre el bloque plan() esperado")
    text = text.replace(
        marker,
        marker + "    groq = plan_with_groq(text, db_context)\n    if groq:\n        return groq\n\n",
        1,
    )

# Make the no-provider fallback user-friendly rather than talking about subscriptions.
old = '            "message": "No necesito una suscripción para operar. Puedo ejecutar comandos Lumeon directos como buscar, stock bajo, cambiar precios, registrar ventas, enviar facturas y devolver ventas.",\n'
new = '            "message": "Puedo ayudarte con clientes, productos, inventario, ventas, facturas y devoluciones. Dime qué necesitas hacer.",\n'
text = text.replace(old, new, 1)

AI.write_text(text, encoding="utf-8")
print("GROQ PLANNER ENABLED")
print("Gemini queda como fallback opcional.")
print("No database was touched.")
