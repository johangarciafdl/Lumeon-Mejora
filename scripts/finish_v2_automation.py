from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"No encontré el bloque esperado: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("PATCH OK:", label)


# 1) Empty searches should list all records for the authenticated admin UI.
customer = ROOT / "lumeon_pro/backend/services/customer_service.py"
replace_once(
    customer,
    '''def search_customers(conn, term: str, limit: int = 20) -> list[dict]:\n    term = str(term or "").strip()\n    if not term:\n        return []\n    limit = max(1, min(int(limit), 100))\n    like = f"%{term}%"\n    rows = conn.execute(\n        "SELECT id,nombre,documento,telefono,direccion,email,ciudad FROM clientes "\n        "WHERE LOWER(nombre) LIKE LOWER(?) OR LOWER(documento) LIKE LOWER(?) "\n        "OR LOWER(telefono) LIKE LOWER(?) OR LOWER(email) LIKE LOWER(?) "\n        "ORDER BY nombre LIMIT ?",\n        (like, like, like, like, limit),\n    ).fetchall()\n    return [dict(row) for row in rows]\n''',
    '''def search_customers(conn, term: str, limit: int = 20) -> list[dict]:\n    term = str(term or "").strip()\n    limit = max(1, min(int(limit), 100))\n    if term:\n        like = f"%{term}%"\n        rows = conn.execute(\n            "SELECT id,nombre,documento,telefono,direccion,email,ciudad FROM clientes "\n            "WHERE LOWER(nombre) LIKE LOWER(?) OR LOWER(documento) LIKE LOWER(?) "\n            "OR LOWER(telefono) LIKE LOWER(?) OR LOWER(email) LIKE LOWER(?) "\n            "ORDER BY nombre LIMIT ?",\n            (like, like, like, like, limit),\n        ).fetchall()\n    else:\n        rows = conn.execute(\n            "SELECT id,nombre,documento,telefono,direccion,email,ciudad FROM clientes "\n            "ORDER BY nombre LIMIT ?",\n            (limit,),\n        ).fetchall()\n    return [dict(row) for row in rows]\n''',
    "customer empty search",
)

product = ROOT / "lumeon_pro/backend/services/product_service.py"
replace_once(
    product,
    '''def search_products(conn, term: str, limit: int = 20) -> list[dict]:\n    term = str(term or "").strip()\n    if not term:\n        return []\n    limit = max(1, min(int(limit), 100))\n    like = f"%{term}%"\n    rows = conn.execute(\n        "SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos "\n        "WHERE LOWER(nombre) LIKE LOWER(?) OR LOWER(referencia) LIKE LOWER(?) "\n        "ORDER BY nombre LIMIT ?",\n        (like, like, limit),\n    ).fetchall()\n    return [dict(row) for row in rows]\n''',
    '''def search_products(conn, term: str, limit: int = 20) -> list[dict]:\n    term = str(term or "").strip()\n    limit = max(1, min(int(limit), 100))\n    if term:\n        like = f"%{term}%"\n        rows = conn.execute(\n            "SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos "\n            "WHERE LOWER(nombre) LIKE LOWER(?) OR LOWER(referencia) LIKE LOWER(?) "\n            "ORDER BY nombre LIMIT ?",\n            (like, like, limit),\n        ).fetchall()\n    else:\n        rows = conn.execute(\n            "SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos "\n            "ORDER BY nombre LIMIT ?",\n            (limit,),\n        ).fetchall()\n    return [dict(row) for row in rows]\n''',
    "product empty search",
)

# 2) Store NULL for blank documents instead of an empty string.
replace_once(
    customer,
    '"documento": str(data.get("documento", "")).strip()[:50],',
    '"documento": (str(data.get("documento", "")).strip()[:50] or None),',
    "customer blank document -> NULL",
)

# 3) Normalize Colombian-style local numbers for CallMeBot, but keep configurable country code.
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

# 4) Reuse one completion service from web and AI sale flows.
completion = ROOT / "lumeon_pro/backend/services/sale_completion_service.py"
if not completion.exists():
    completion.write_text('''from __future__ import annotations\n\nfrom services.invoice_delivery_service import deliver_invoice\n\ndef deliver_sale_invoice(conn, sale_id: int, *, force_retry: bool = False) -> dict:\n    sale = conn.execute(\n        "SELECT id, numero_factura, cliente_nombre, cliente_telefono, total FROM ventas WHERE id=? LIMIT 1",\n        (sale_id,),\n    ).fetchone()\n    if not sale:\n        return {"status": "NOT_FOUND", "error": "Venta no encontrada"}\n    items = [dict(row) for row in conn.execute(\n        "SELECT referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia FROM venta_items WHERE venta_id=? ORDER BY id",\n        (sale_id,),\n    ).fetchall()]\n    result = deliver_invoice(\n        conn, sale_id=int(sale["id"]), invoice_number=sale["numero_factura"],\n        customer_name=sale["cliente_nombre"] or "Cliente", phone=sale["cliente_telefono"] or "",\n        items=items, total=float(sale["total"] or 0), force_retry=force_retry,\n    )\n    delivery = result.get("whatsapp")\n    return {"status": getattr(delivery, "status", None), "error": getattr(delivery, "error", None)}\n''', encoding="utf-8")

# 5) Automatically deliver invoice after a successful sale through V2.
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

# 6) Automatically deliver invoice after the legacy-compatible UI saves a sale.
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

# 7) Frontend should display WhatsApp result after a sale and load all records by default.
index = ROOT / "lumeon_pro/frontend/index.html"
text = index.read_text(encoding="utf-8")
text2 = text.replace(
    "const data=await fetch(`${API}/productos?q=${q}&categoria=${cat}`).then(r=>r.json());",
    "const data=await fetch(`${API}/productos?q=${encodeURIComponent(q)}&categoria=${encodeURIComponent(cat)}`).then(r=>r.json());",
    1,
)
text2 = text2.replace(
    "if(r.ok){toast(r.email_enviado?'Venta registrada y recibo enviado':'Venta registrada',r.email_enviado?'success':'warning');closeModal('modal-venta');loadVentas();loadDashboard();loadCiclos();}",
    "if(r.ok){const ws=r.whatsapp?.status; toast(ws==='SENT'?'Venta registrada y WhatsApp enviado':ws==='FAILED'?'Venta registrada; WhatsApp falló':'Venta registrada',ws==='FAILED'?'warning':'success');closeModal('modal-venta');loadVentas();loadDashboard();loadCiclos();}",
    1,
)
index.write_text(text2, encoding="utf-8")
print("PATCH OK: frontend sale feedback")

# 8) Keep the assistant launcher visible and point natural-language AI to the orchestrator endpoint.
assistant = ROOT / "lumeon_pro/frontend/assistant.js"
a = assistant.read_text(encoding="utf-8")
a = a.replace("const API = '/api/v2/assistant/message';", "const API = '/api/v2/assistant/ai';", 1)
a = a.replace("fab.onclick = () => { panel.classList.add('open'); fab.classList.add('hidden'); input.focus(); };", "fab.onclick = () => { panel.classList.add('open'); panel.style.display='flex'; input.focus(); };", 1)
a = a.replace("panel.querySelector('.la-close').onclick = () => { panel.classList.remove('open'); fab.classList.remove('hidden'); };", "panel.querySelector('.la-close').onclick = () => { panel.classList.remove('open'); panel.style.display='none'; };", 1)
assistant.write_text(a, encoding="utf-8")
print("PATCH OK: assistant launcher + AI endpoint")

# 9) Free/local AI fallback: common Spanish commands work even when OpenRouter's free model is unavailable.
ai = ROOT / "lumeon_pro/backend/services/ai_orchestrator.py"
local_parser = '''\n\ndef _local_command_plan(text: str) -> dict | None:\n    t = " ".join(str(text or "").strip().split())\n    low = t.lower()\n\n    if low in {"stock bajo", "inventario bajo", "productos con stock bajo"}:\n        return {"action": "low_stock"}\n    if low.startswith("buscar cliente "):\n        return {"action": "search_customer", "query": t[16:].strip()}\n    if low.startswith("buscar producto "):\n        return {"action": "search_product", "query": t[17:].strip()}\n\n    m = re.search(r"(?:cambia|cambiar|actualiza|actualizar)\\s+(?:el\\s+)?precio(?:\\s+del\\s+producto)?\\s+([\\w.-]+)\\s+(?:a|por)\\s*\\$?([0-9]+(?:[.,][0-9]+)?)", low)\n    if m:\n        return {\n            "action": "update_product_price",\n            "product_ref": m.group(1),\n            "price": float(m.group(2).replace('.', '').replace(',', '.')),\n            "confirmation_message": f"Voy a cambiar el precio del producto {m.group(1)} a {m.group(2)}. ¿Confirmas?",\n        }\n\n    m = re.search(r"(?:elimina|eliminar|borra|borrar)\\s+(?:el\\s+)?producto\\s+([\\w.-]+)", low)\n    if m:\n        return {\n            "action": "delete_product",\n            "product_ref": m.group(1),\n            "confirmation_message": f"Voy a eliminar el producto {m.group(1)}. ¿Confirmas?",\n        }\n\n    m = re.search(r"(?:envia|enviar|manda|mandar)\\s+(?:la\\s+)?factura\\s+([\\w.-]+)", low)\n    if m:\n        ref = m.group(1)\n        return {"action": "send_invoice", "sale_id": int(ref) if ref.isdigit() else None, "invoice_number": None if ref.isdigit() else ref}\n\n    m = re.search(r"(?:devuelve|devolver|anula|anular)\\s+(?:la\\s+)?venta\\s+([0-9]+)", low)\n    if m:\n        sale_id = int(m.group(1))\n        return {\n            "action": "refund_sale",\n            "sale_id": sale_id,\n            "confirmation_message": f"Voy a devolver la venta {sale_id} y reponer inventario. ¿Confirmas?",\n        }\n\n    # Structured but natural enough: "venta para Juan telefono 304... productos 123x2,456:1"\n    if low.startswith(("venta ", "registrar venta", "crear venta", "registra venta")):\n        customer_name = ""\n        phone = ""\n        name_match = re.search(r"(?:para|cliente)\\s+(.+?)(?=\\s+(?:telefono|tel|productos?|items?)\\b|$)", t, re.I)\n        if name_match:\n            customer_name = name_match.group(1).strip()\n        phone_match = re.search(r"(?:telefono|tel)\\s*[:=]?\\s*(\\+?[0-9 -]{10,15})", t, re.I)\n        if phone_match:\n            phone = phone_match.group(1).strip()\n        items_match = re.search(r"(?:productos?|items?)\\s*[:=]?\\s*(.+)$", t, re.I)\n        items = []\n        if items_match:\n            for token in re.split(r"[,;]\\s*", items_match.group(1)):\n                mm = re.fullmatch(r"([\\w.-]+)\\s*(?:x|\\*)\\s*(\\d+)", token.strip(), re.I) or re.fullmatch(r"([\\w.-]+)\\s*:\\s*(\\d+)", token.strip())\n                if mm:\n                    items.append({"referencia": mm.group(1), "cantidad": int(mm.group(2))})\n        if items:\n            return {"action": "create_sale", "customer_name": customer_name, "phone": phone, "items": items}\n\n    return None\n'''

replace_once(
    ai,
    'import os\nfrom urllib.error import HTTPError, URLError\n',
    'import os\nimport re\nfrom urllib.error import HTTPError, URLError\n',
    "AI regex import",
)
replace_once(
    ai,
    '\n\ndef plan(text: str, db_context: dict) -> dict:\n',
    local_parser + '\n\ndef plan(text: str, db_context: dict) -> dict:\n',
    "local AI parser",
)
replace_once(
    ai,
    '''    local = _local_plan(text)\n    if local:\n        return local\n    key = os.getenv("OPENROUTER_API_KEY", "").strip()\n''',
    '''    local = _local_plan(text)\n    if local:\n        return local\n    local = _local_command_plan(text)\n    if local:\n        return local\n    key = os.getenv("OPENROUTER_API_KEY", "").strip()\n''',
    "AI local-first fallback",
)
replace_once(
    ai,
    '''    if name == "search_product":\n        term = str(action.get("query") or action.get("product_ref") or action.get("product_name") or "").strip()\n        return {"ok": True, "status": "ready", "intent": name, "results": search_products(conn, term, 100)}, session_state\n\n    if name == "create_customer":\n''',
    '''    if name == "search_product":\n        term = str(action.get("query") or action.get("product_ref") or action.get("product_name") or "").strip()\n        return {"ok": True, "status": "ready", "intent": name, "results": search_products(conn, term, 100)}, session_state\n\n    if name == "low_stock":\n        rows = conn.execute("SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos WHERE stock <= stock_minimo ORDER BY stock ASC LIMIT 100").fetchall()\n        return {"ok": True, "status": "ready", "intent": name, "results": [dict(r) for r in rows]}, session_state\n\n    if name == "create_customer":\n''',
    "AI low stock action",
)
replace_once(
    ai,
    '''        sale_id = create_sale(conn, data={\n            "cliente_id": action.get("customer_id"),\n            "cliente_nombre": str(action.get("customer_name") or "").strip(),\n''',
    '''        customer_id = action.get("customer_id")\n        customer_name = str(action.get("customer_name") or "").strip()\n        customer_query = str(action.get("customer_query") or "").strip()\n        phone = str(action.get("phone") or "").strip()\n        email = str(action.get("email") or "").strip()\n        if not customer_id and customer_query:\n            matches = search_customers(conn, customer_query, 5)\n            if len(matches) == 1:\n                match = matches[0]\n                customer_id = int(match["id"])\n                customer_name = match["nombre"]\n                phone = phone or str(match.get("telefono") or "")\n                email = email or str(match.get("email") or "")\n        sale_id = create_sale(conn, data={\n            "cliente_id": customer_id,\n            "cliente_nombre": customer_name,\n''',
    "AI customer resolution",
)
replace_once(
    ai,
    '            "cliente_email": str(action.get("email") or "").strip(),\n            "cliente_telefono": str(action.get("phone") or "").strip(),\n',
    '            "cliente_email": email,\n            "cliente_telefono": phone,\n',
    "AI customer contact reuse",
)

print("\nFINISH V2 AUTOMATION: OK")
print("No database was touched by this script.")
