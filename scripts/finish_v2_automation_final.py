from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print("SKIP:", label)
        return
    if old not in text:
        raise SystemExit(f"No encontré el bloque esperado: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("PATCH OK:", label)


# Automatic invoice/WhatsApp completion is shared by web and AI-created sales.
completion = ROOT / "lumeon_pro/backend/services/sale_completion_service.py"
if not completion.exists():
    completion.write_text('''from __future__ import annotations\n\nfrom services.invoice_delivery_service import deliver_invoice\n\ndef deliver_sale_invoice(conn, sale_id: int, *, force_retry: bool = False) -> dict:\n    sale = conn.execute(\n        "SELECT id, numero_factura, cliente_nombre, cliente_telefono, total FROM ventas WHERE id=? LIMIT 1",\n        (sale_id,),\n    ).fetchone()\n    if not sale:\n        return {"status": "NOT_FOUND", "error": "Venta no encontrada"}\n    items = [dict(row) for row in conn.execute(\n        "SELECT referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia FROM venta_items WHERE venta_id=? ORDER BY id",\n        (sale_id,),\n    ).fetchall()]\n    result = deliver_invoice(\n        conn, sale_id=int(sale["id"]), invoice_number=sale["numero_factura"],\n        customer_name=sale["cliente_nombre"] or "Cliente", phone=sale["cliente_telefono"] or "",\n        items=items, total=float(sale["total"] or 0), force_retry=force_retry,\n    )\n    delivery = result.get("whatsapp")\n    return {"status": getattr(delivery, "status", None), "error": getattr(delivery, "error", None)}\n''', encoding="utf-8")
    print("PATCH OK: sale completion service")

app_v2 = ROOT / "lumeon_pro/backend/app_v2.py"
replace_once(
    app_v2,
    'from services.return_service import ReturnError, return_sale\n',
    'from services.return_service import ReturnError, return_sale\nfrom services.sale_completion_service import deliver_sale_invoice\n',
    "app_v2 sale completion import",
)
replace_once(
    app_v2,
    '''            sale_id = create_sale(conn, data=data, user_id=actor.id)\n            conn.commit()\n            return jsonify({"ok": True, "venta_id": sale_id}), 201\n''',
    '''            sale_id = create_sale(conn, data=data, user_id=actor.id)\n            conn.commit()\n            whatsapp = deliver_sale_invoice(conn, sale_id)\n            conn.commit()\n            return jsonify({"ok": True, "venta_id": sale_id, "whatsapp": whatsapp}), 201\n''',
    "app_v2 automatic WhatsApp",
)

compat = ROOT / "lumeon_pro/backend/api/legacy_compat_api.py"
replace_once(
    compat,
    'from services.return_service import ReturnError, return_sale\n',
    'from services.return_service import ReturnError, return_sale\nfrom services.sale_completion_service import deliver_sale_invoice\n',
    "compat sale completion import",
)
replace_once(
    compat,
    '''            sale_id = create_sale(conn, data=data, user_id=int(a.id))\n            conn.commit()\n            return jsonify({"ok": True, "id": sale_id}), 201\n''',
    '''            sale_id = create_sale(conn, data=data, user_id=int(a.id))\n            conn.commit()\n            whatsapp = deliver_sale_invoice(conn, sale_id)\n            conn.commit()\n            return jsonify({"ok": True, "id": sale_id, "whatsapp": whatsapp}), 201\n''',
    "compat automatic WhatsApp",
)

wa = ROOT / "lumeon_pro/backend/services/whatsapp_provider.py"
replace_once(
    wa,
    'self.api_key = os.getenv("CALLMEBOT_API_KEY", "").strip()',
    'self.api_key = (os.getenv("CALLMEBOT_API_KEY", "") or os.getenv("CALLMEBOT_KEY", "")).strip()\n        self.country_code = os.getenv("CALLMEBOT_COUNTRY_CODE", "57").strip() or "57"',
    "CallMeBot aliases/config",
)
replace_once(
    wa,
    '''        phone = phone.strip()\n        if not phone.startswith("+"):\n            raise WhatsAppError("El teléfono debe incluir código internacional")\n''',
    '''        phone = phone.strip().replace(" ", "").replace("-", "")\n        if phone.startswith("00"):\n            phone = "+" + phone[2:]\n        elif not phone.startswith("+"):\n            if len(phone) == 10 and phone.startswith("3"):\n                phone = f"+{self.country_code}{phone}"\n            else:\n                raise WhatsAppError("El teléfono debe incluir código internacional")\n''',
    "CallMeBot phone normalization",
)

# The natural-language assistant uses the AI endpoint and its launcher must remain usable.
assistant = ROOT / "lumeon_pro/frontend/assistant.js"
a = assistant.read_text(encoding="utf-8")
a2 = a.replace("const API = '/api/v2/assistant/message';", "const API = '/api/v2/assistant/ai';", 1)
a2 = a2.replace("fab.onclick = () => { panel.classList.add('open'); fab.classList.add('hidden'); input.focus(); };", "fab.onclick = () => { panel.classList.add('open'); panel.style.display='flex'; input.focus(); };", 1)
a2 = a2.replace("panel.querySelector('.la-close').onclick = () => { panel.classList.remove('open'); fab.classList.remove('hidden'); };", "panel.querySelector('.la-close').onclick = () => { panel.classList.remove('open'); panel.style.display='none'; };", 1)
if a2 != a:
    assistant.write_text(a2, encoding="utf-8")
    print("PATCH OK: assistant launcher + AI endpoint")
else:
    print("SKIP: assistant launcher + AI endpoint")

# Frontend feedback after automatic WhatsApp.
index = ROOT / "lumeon_pro/frontend/index.html"
i = index.read_text(encoding="utf-8")
i2 = i.replace(
    "if(r.ok){toast(r.email_enviado?'Venta registrada y recibo enviado':'Venta registrada',r.email_enviado?'success':'warning');closeModal('modal-venta');loadVentas();loadDashboard();loadCiclos();}",
    "if(r.ok){const ws=r.whatsapp?.status; toast(ws==='SENT'?'Venta registrada y WhatsApp enviado':ws==='FAILED'?'Venta registrada; WhatsApp falló':'Venta registrada',ws==='FAILED'?'warning':'success');closeModal('modal-venta');loadVentas();loadDashboard();loadCiclos();}",
    1,
)
if i2 != i:
    index.write_text(i2, encoding="utf-8")
    print("PATCH OK: frontend WhatsApp result")

# Free/local fallback. OpenRouter remains optional for richer language; core commands do not depend on it.
ai = ROOT / "lumeon_pro/backend/services/ai_orchestrator.py"
local_parser = r'''\n\ndef _local_command_plan(text: str) -> dict | None:\n    t = " ".join(str(text or "").strip().split())\n    low = t.lower()\n    if low in {"stock bajo", "inventario bajo", "productos con stock bajo"}:\n        return {"action": "low_stock"}\n    if low.startswith("buscar cliente "):\n        return {"action": "search_customer", "query": t[16:].strip()}\n    if low.startswith("buscar producto "):\n        return {"action": "search_product", "query": t[17:].strip()}\n    m = re.search(r"(?:cambia|actualiza)\s+(?:el\s+)?precio(?:\s+del\s+producto)?\s+([\w.-]+)\s+(?:a|por)\s*\$?([0-9]+(?:[.,][0-9]+)?)", low)\n    if m:\n        return {"action":"update_product_price","product_ref":m.group(1),"price":float(m.group(2).replace('.','').replace(',','.')),"confirmation_message":f"Voy a cambiar el precio del producto {m.group(1)} a {m.group(2)}. ¿Confirmas?"}\n    m = re.search(r"(?:elimina|borra)\s+(?:el\s+)?producto\s+([\w.-]+)", low)\n    if m:\n        return {"action":"delete_product","product_ref":m.group(1),"confirmation_message":f"Voy a eliminar el producto {m.group(1)}. ¿Confirmas?"}\n    m = re.search(r"(?:envia|manda)\s+(?:la\s+)?factura\s+([\w.-]+)", low)\n    if m:\n        ref=m.group(1)\n        return {"action":"send_invoice","sale_id":int(ref) if ref.isdigit() else None,"invoice_number":None if ref.isdigit() else ref}\n    m = re.search(r"(?:devuelve|anula)\s+(?:la\s+)?venta\s+([0-9]+)", low)\n    if m:\n        sid=int(m.group(1))\n        return {"action":"refund_sale","sale_id":sid,"confirmation_message":f"Voy a devolver la venta {sid} y reponer inventario. ¿Confirmas?"}\n    if low.startswith(("venta ", "registrar venta", "crear venta", "registra venta")):\n        name_match=re.search(r"(?:para|cliente)\s+(.+?)(?=\s+(?:telefono|tel|productos?|items?)\b|$)", t, re.I)\n        phone_match=re.search(r"(?:telefono|tel)\s*[:=]?\s*(\+?[0-9 -]{10,15})", t, re.I)\n        items_match=re.search(r"(?:productos?|items?)\s*[:=]?\s*(.+)$", t, re.I)\n        items=[]\n        if items_match:\n            for token in re.split(r"[,;]\s*", items_match.group(1)):\n                mm=re.fullmatch(r"([\w.-]+)\s*(?:x|\*)\s*(\d+)", token.strip(), re.I) or re.fullmatch(r"([\w.-]+)\s*:\s*(\d+)", token.strip())\n                if mm: items.append({"referencia":mm.group(1),"cantidad":int(mm.group(2))})\n        if items:\n            return {"action":"create_sale","customer_name":name_match.group(1).strip() if name_match else "","phone":phone_match.group(1).strip() if phone_match else "","items":items}\n    return None\n'''
replace_once(ai, 'import os\nfrom urllib.error import HTTPError, URLError\n', 'import os\nimport re\nfrom urllib.error import HTTPError, URLError\n', 'AI regex import')
replace_once(ai, '\n\ndef plan(text: str, db_context: dict) -> dict:\n', local_parser+'\n\ndef plan(text: str, db_context: dict) -> dict:\n', 'AI local parser')
replace_once(ai, '''    local = _local_plan(text)\n    if local:\n        return local\n    key = os.getenv("OPENROUTER_API_KEY", "").strip()\n''', '''    local = _local_plan(text)\n    if local:\n        return local\n    local = _local_command_plan(text)\n    if local:\n        return local\n    key = os.getenv("OPENROUTER_API_KEY", "").strip()\n''', 'AI local-first fallback')
replace_once(ai, '''    if name == "search_product":\n        term = str(action.get("query") or action.get("product_ref") or action.get("product_name") or "").strip()\n        return {"ok": True, "status": "ready", "intent": name, "results": search_products(conn, term, 100)}, session_state\n\n    if name == "create_customer":\n''', '''    if name == "search_product":\n        term = str(action.get("query") or action.get("product_ref") or action.get("product_name") or "").strip()\n        return {"ok": True, "status": "ready", "intent": name, "results": search_products(conn, term, 100)}, session_state\n\n    if name == "low_stock":\n        rows = conn.execute("SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos WHERE stock <= stock_minimo ORDER BY stock ASC LIMIT 100").fetchall()\n        return {"ok": True, "status": "ready", "intent": name, "results": [dict(r) for r in rows]}, session_state\n\n    if name == "create_customer":\n''', 'AI low-stock action')

print("FINISH V2 AUTOMATION FINAL: OK")
print("No database was touched by this script.")
