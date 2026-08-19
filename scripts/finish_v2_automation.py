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
a = a.replace("const response=await fetch(API,{method:'POST',headers,credentials:'same-origin',body:JSON.stringify({text})});", "const response=await fetch(API,{method:'POST',headers,credentials:'same-origin',body:JSON.stringify({text})});", 1)
assistant.write_text(a, encoding="utf-8")
print("PATCH OK: assistant launcher + AI endpoint")

print("\nFINISH V2 AUTOMATION: OK")
print("No database was touched by this script.")
