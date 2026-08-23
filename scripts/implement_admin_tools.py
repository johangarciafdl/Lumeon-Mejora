from __future__ import annotations

from getpass import getpass
from pathlib import Path
import re

ROOT = Path('/home/lumeon/lumeon-mejora')
BACKEND = ROOT / 'lumeon_pro' / 'backend'
FRONTEND = ROOT / 'lumeon_pro' / 'frontend'


def patch_text(path: Path, transform, label: str) -> None:
    text = path.read_text(encoding='utf-8')
    new = transform(text)
    if new == text:
        print(f'{label}: sin cambios (ya aplicado)')
        return
    path.write_text(new, encoding='utf-8')
    print(f'{label}: OK')


def add_once(text: str, marker: str, block: str, where: str = 'end') -> str:
    if marker in text:
        return text
    if where == 'before_end':
        return text.replace('\n', block + '\n', 1) if False else text
    return text + block


# ---------------------------------------------------------------------------
# 1) Sale deletion service: restore stock, remove sale-side dependent records,
#    keep an audit entry. Only the API authorization can call this service.
# ---------------------------------------------------------------------------
(S_BACKEND / 'services' / 'sale_delete_service.py').write_text('''from __future__ import annotations\n\nfrom services.audit_service import record as audit\n\n\nclass SaleDeleteError(ValueError):\n    pass\n\n\ndef delete_sale(conn, *, sale_id: int, user_id: int) -> dict:\n    sale = conn.execute(\n        "SELECT id, numero_factura, estado, cliente_nombre, total FROM ventas WHERE id=? LIMIT 1",\n        (sale_id,),\n    ).fetchone()\n    if not sale:\n        raise SaleDeleteError("Venta no encontrada")\n\n    items = conn.execute(\n        "SELECT id, producto_id, referencia, cantidad FROM venta_items WHERE venta_id=? ORDER BY id",\n        (sale_id,),\n    ).fetchall()\n\n    state = str(sale["estado"] or "").strip().lower()\n    # A returned sale already put its inventory back. Do not double-restock it.\n    if state not in {"devuelta", "devuelto"}:\n        for item in items:\n            if item["producto_id"] is None:\n                continue\n            updated = conn.execute(\n                "UPDATE productos SET stock=stock+? WHERE id=?",\n                (int(item["cantidad"] or 0), int(item["producto_id"])),\n            )\n            if updated.rowcount != 1:\n                raise SaleDeleteError(\n                    f"No se pudo restaurar stock del producto {item['referencia'] or item['producto_id']}"\n                )\n\n    # Remove delivery records and return records tied to the sale.\n    conn.execute("DELETE FROM invoice_deliveries WHERE venta_id=?", (sale_id,))\n    conn.execute(\n        "DELETE FROM venta_devolucion_items WHERE devolucion_id IN (SELECT id FROM venta_devoluciones WHERE venta_id=?)",\n        (sale_id,),\n    )\n    conn.execute("DELETE FROM venta_devoluciones WHERE venta_id=?", (sale_id,))\n    conn.execute("DELETE FROM venta_items WHERE venta_id=?", (sale_id,))\n\n    # Keep the audit trail, but remove the operational sale itself.\n    audit(\n        conn,\n        actor_id=user_id,\n        action="sale.deleted",\n        entity="venta",\n        entity_id=sale_id,\n        details={\n            "invoice": sale["numero_factura"],\n            "customer": sale["cliente_nombre"],\n            "total": float(sale["total"] or 0),\n            "items": len(items),\n            "previous_state": sale["estado"],\n            "stock_restored": state not in {"devuelta", "devuelto"},\n        },\n    )\n    conn.execute("DELETE FROM ventas WHERE id=?", (sale_id,))\n\n    return {\n        "sale_id": sale_id,\n        "invoice": sale["numero_factura"],\n        "stock_restored": state not in {"devuelta", "devuelto"},\n    }\n''', encoding='utf-8')
print('sale_delete_service.py: OK')


# ---------------------------------------------------------------------------
# 2) Permissions: admin-only delete sales and read audit log.
# ---------------------------------------------------------------------------
authz = BACKEND / 'services' / 'authorization_service.py'

def patch_authz(text: str) -> str:
    text = text.replace(
        'ADMIN_ACTIONS = {"delete_customer", "delete_product", "refund_sale", "manage_users"}',
        'ADMIN_ACTIONS = {"delete_customer", "delete_product", "delete_sale", "refund_sale", "manage_users", "view_audit_log"}',
    )
    return text
patch_text(authz, patch_authz, 'authorization_service.py')


# ---------------------------------------------------------------------------
# 3) Admin API: logs + admin user creation + sale deletion endpoint.
# ---------------------------------------------------------------------------
admin_api = BACKEND / 'api' / 'admin_api.py'
admin_api.write_text('''from __future__ import annotations\n\nfrom flask import Blueprint, jsonify, request\nfrom werkzeug.security import generate_password_hash\n\nfrom core.db import get_db\nfrom services.auth_service import AuthenticationError, current_actor\nfrom services.authorization_service import require\nfrom services.sale_delete_service import SaleDeleteError, delete_sale\n\nadmin_api = Blueprint("admin_api", __name__, url_prefix="/api/v2/admin")\n\n\n@admin_api.get("/logs")\ndef logs():\n    try:\n        actor = current_actor()\n        require(actor, "view_audit_log")\n        try:\n            limit = min(max(int(request.args.get("limit", 100)), 1), 500)\n        except (TypeError, ValueError):\n            limit = 100\n\n        conn = get_db()\n        try:\n            rows = conn.execute(\n                """SELECT a.id, a.user_id, COALESCE(u.username,'sistema') AS username,\n                          a.action, a.entity_type, a.entity_id, a.metadata, a.created_at\n                   FROM audit_log a\n                   LEFT JOIN usuarios u ON u.id=a.user_id\n                   ORDER BY a.id DESC\n                   LIMIT ?""",\n                (limit,),\n            ).fetchall()\n            return jsonify({"ok": True, "results": [dict(r) for r in rows]})\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n\n\n@admin_api.post("/users")\ndef create_user():\n    try:\n        actor = current_actor()\n        require(actor, "manage_users")\n        data = request.get_json(silent=True) or {}\n        username = str(data.get("username") or "").strip()\n        password = str(data.get("password") or "")\n        nombre = str(data.get("nombre") or username).strip()\n        email = str(data.get("email") or "admin@lumeon.local").strip()\n        role = str(data.get("role") or "admin").strip().lower()\n\n        if not username or not password:\n            return jsonify({"ok": False, "error": "Usuario y contraseña son obligatorios"}), 400\n        if role not in {"admin", "vendedor", "cajero", "almacen"}:\n            return jsonify({"ok": False, "error": "Rol inválido"}), 400\n\n        conn = get_db()\n        try:\n            existing = conn.execute("SELECT id FROM usuarios WHERE username=?", (username,)).fetchone()\n            if existing:\n                return jsonify({"ok": False, "error": "El usuario ya existe"}), 409\n            row = conn.execute(\n                """INSERT INTO usuarios(username,password,email,nombre,rol,activo)\n                   VALUES(?,?,?,?,?,TRUE) RETURNING id, username, email, nombre, rol, activo""",\n                (username, generate_password_hash(password), email, nombre, role),\n            ).fetchone()\n            conn.commit()\n            return jsonify({"ok": True, "user": dict(row)}), 201\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n\n\n@admin_api.delete("/ventas/<int:sale_id>")\ndef delete_sale_v2(sale_id: int):\n    try:\n        actor = current_actor()\n        require(actor, "delete_sale")\n        conn = get_db()\n        try:\n            result = delete_sale(conn, sale_id=sale_id, user_id=int(actor.id))\n            conn.commit()\n            return jsonify({"ok": True, **result}), 200\n        except Exception:\n            conn.rollback()\n            raise\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n    except SaleDeleteError as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 400\n''', encoding='utf-8')
print('admin_api.py: OK')


# Register admin blueprint.
api_init = BACKEND / 'api' / '__init__.py'
def patch_api_init(text: str) -> str:
    if 'from .admin_api import admin_api' not in text:
        text = text.replace('from .ai_api import ai_api\n', 'from .ai_api import ai_api\nfrom .admin_api import admin_api\n')
    if 'app.register_blueprint(admin_api)' not in text:
        text = text.replace('    app.register_blueprint(ai_api)\n', '    app.register_blueprint(ai_api)\n    app.register_blueprint(admin_api)\n')
    return text
patch_text(api_init, patch_api_init, 'api/__init__.py')


# Make legacy UI delete button call the admin endpoint. Existing frontend already
# renders the trash button and asks for confirmation.
legacy = BACKEND / 'api' / 'legacy_compat_api.py'
def patch_legacy(text: str) -> str:
    marker = '@legacy_compat_api.get("/ventas/<int:sale_id>")'
    if '@legacy_compat_api.delete("/ventas/<int:sale_id>")' in text:
        return text
    block = '''\n\n@legacy_compat_api.delete("/ventas/<int:sale_id>")\ndef eliminar_venta(sale_id: int):\n    try:\n        actor = current_actor()\n        require(actor, "delete_sale")\n        conn = get_db()\n        try:\n            result = delete_sale(conn, sale_id=sale_id, user_id=int(actor.id))\n            conn.commit()\n            return jsonify({"ok": True, **result}), 200\n        except Exception:\n            conn.rollback()\n            raise\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n    except SaleDeleteError as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 400\n'''
    text = text.replace('from services.sale_service import SaleError, create_sale\n', 'from services.sale_service import SaleError, create_sale\nfrom services.sale_delete_service import SaleDeleteError, delete_sale\n')
    return text.replace(marker, block + '\n\n' + marker, 1)
patch_text(legacy, patch_legacy, 'legacy_compat_api.py')


# ---------------------------------------------------------------------------
# 4) Admin frontend space: load a separate JS so index.html needs only one
#    tiny script tag. It adds Logs page, hides delete buttons for non-admins,
#    and works with the existing mobile menu wrapper.
# ---------------------------------------------------------------------------
js = FRONTEND / 'admin_features.js'
js.write_text('''(function(){\n  const API = window.API || '';\n  let isAdmin = false;\n\n  async function getAdmin(){\n    try{\n      const r = await fetch(`${API}/v2/auth/me`, {credentials:'same-origin'});\n      const d = await r.json();\n      isAdmin = !!(d.ok && d.authenticated && d.role === 'admin');\n    }catch(e){ isAdmin = false; }\n    return isAdmin;\n  }\n\n  function injectStyles(){\n    if(document.getElementById('lumeon-admin-feature-styles')) return;\n    const style = document.createElement('style');\n    style.id='lumeon-admin-feature-styles';\n    style.textContent = `\n      #page-admin-logs{display:none}\n      #page-admin-logs.active{display:block}\n      .admin-log-toolbar{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:16px}\n      .admin-log-list{display:grid;gap:10px}\n      .admin-log-card{background:var(--card,#fff);border:1px solid var(--border,#e8e4dc);padding:14px;border-radius:6px}\n      .admin-log-top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}\n      .admin-log-action{font-weight:700;font-size:12px;color:var(--slate,#1c2b3a)}\n      .admin-log-user,.admin-log-time{font-size:11px;color:var(--ink3,#9a948c)}\n      .admin-log-meta{margin-top:8px;font-family:monospace;font-size:11px;color:var(--ink2,#4a4640);white-space:pre-wrap;overflow-wrap:anywhere}\n      .admin-log-empty{padding:30px;text-align:center;color:var(--ink3,#9a948c)}\n      @media(max-width:768px){\n        #page-admin-logs .card{padding:12px}\n        .admin-log-card{padding:12px}\n      }\n    `;\n    document.head.appendChild(style);\n  }\n\n  function addNav(){\n    if(!isAdmin || document.getElementById('nav-admin-logs')) return;\n    const nav = document.querySelector('#sidebar nav');\n    if(!nav) return;\n    const item=document.createElement('div');\n    item.id='nav-admin-logs';\n    item.className='nav-item';\n    item.innerHTML='<span class="nav-icon" style="display:flex;align-items:center;justify-content:center">≡</span>Registros';\n    item.onclick=openLogs;\n    const sections=nav.querySelectorAll('.nav-section');\n    const last=sections[sections.length-1];\n    if(last) last.insertAdjacentElement('afterend',item); else nav.appendChild(item);\n  }\n\n  function addLogsPage(){\n    if(!isAdmin || document.getElementById('page-admin-logs')) return;\n    const content=document.getElementById('content');\n    if(!content) return;\n    const page=document.createElement('div');\n    page.id='page-admin-logs';\n    page.className='page';\n    page.innerHTML=`\n      <div class="page-header"><div class="page-header-left"><h2>Registros</h2><p>Operaciones realizadas en Lumeon</p><div class="page-header-line"></div></div></div>\n      <div class="card">\n        <div class="admin-log-toolbar">\n          <div style="font-size:12px;color:var(--ink2)">Auditoría del sistema</div>\n          <button class="btn btn-secondary btn-sm" id="admin-log-refresh">Actualizar</button>\n        </div>\n        <div id="admin-log-list" class="admin-log-list"><div class="admin-log-empty">Cargando registros...</div></div>\n      </div>`;\n    content.appendChild(page);\n    document.getElementById('admin-log-refresh').onclick=loadLogs;\n  }\n\n  function hideNonAdminDeleteButtons(){\n    if(isAdmin) return;\n    document.querySelectorAll('#tbl-ventas tbody button').forEach(btn=>{\n      if((btn.textContent||'').includes('🗑')) btn.style.display='none';\n    });\n  }\n\n  async function loadLogs(){\n    const list=document.getElementById('admin-log-list');\n    if(!list) return;\n    list.innerHTML='<div class="admin-log-empty">Cargando registros...</div>';\n    try{\n      const r=await fetch(`${API}/v2/admin/logs?limit=200`,{credentials:'same-origin'});\n      const d=await r.json();\n      if(!r.ok || !d.ok) throw new Error(d.error||'No se pudieron cargar los registros');\n      if(!d.results.length){\n        list.innerHTML='<div class="admin-log-empty">No hay operaciones registradas.</div>';\n        return;\n      }\n      list.innerHTML=d.results.map(x=>{\n        let meta=x.metadata||'';\n        try{ meta=JSON.stringify(JSON.parse(meta),null,2); }catch(e){}\n        return `<div class="admin-log-card">\n          <div class="admin-log-top"><span class="admin-log-action">${x.action||'—'}</span><span class="admin-log-time">${x.created_at||'—'}</span></div>\n          <div class="admin-log-user">Usuario: ${x.username||'sistema'} · ${x.entity_type||'—'} #${x.entity_id||'—'}</div>\n          <div class="admin-log-meta">${meta}</div>\n        </div>`;\n      }).join('');\n    }catch(e){\n      list.innerHTML=`<div class="admin-log-empty">${e.message}</div>`;\n    }\n  }\n\n  function openLogs(){\n    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));\n    const page=document.getElementById('page-admin-logs');\n    if(page) page.classList.add('active');\n    const title=document.getElementById('topbar-title');\n    if(title) title.textContent='Registros';\n    document.querySelectorAll('#sidebar .nav-item').forEach(n=>n.classList.remove('active'));\n    document.getElementById('nav-admin-logs')?.classList.add('active');\n    document.getElementById('topbar-action')?.setAttribute('style','display:none');\n    window.closeMobileMenu?.();\n    loadLogs();\n  }\n\n  async function init(){\n    injectStyles();\n    await getAdmin();\n    addNav();\n    addLogsPage();\n    hideNonAdminDeleteButtons();\n    const obs=new MutationObserver(hideNonAdminDeleteButtons);\n    const tbody=document.querySelector('#tbl-ventas tbody');\n    if(tbody) obs.observe(tbody,{childList:true,subtree:true});\n  }\n\n  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);\n  else init();\n\n  window.openAdminLogs=openLogs;\n})();\n''', encoding='utf-8')
print('admin_features.js: OK')


# Ensure index loads admin_features.js.
index = FRONTEND / 'index.html'
def patch_index(text: str) -> str:
    marker = '/admin_features.js'
    if marker in text:
        return text
    return text.replace('</body>', '<script src="/admin_features.js" defer></script></body>', 1)
patch_text(index, patch_index, 'frontend/index.html')


# ---------------------------------------------------------------------------
# 5) Console helper to create AdminMichelle with an interactive password.
# ---------------------------------------------------------------------------
create_admin = ROOT / 'scripts' / 'create_admin.py'
create_admin.write_text('''from __future__ import annotations\n\nfrom getpass import getpass\nimport os\n\nfrom dotenv import load_dotenv\nfrom werkzeug.security import generate_password_hash\n\nload_dotenv('/home/lumeon/lumeon-mejora/lumeon_pro/backend/.env')\n\nfrom core.db import get_db  # noqa: E402\n\nUSERNAME = 'AdminMichelle'\n\npassword = getpass(f'Contraseña para {USERNAME}: ').strip()\nconfirm = getpass('Repite la contraseña: ').strip()\n\nif not password:\n    raise SystemExit('La contraseña no puede estar vacía.')\nif password != confirm:\n    raise SystemExit('Las contraseñas no coinciden.')\n\nconn = get_db()\ntry:\n    existing = conn.execute(\n        'SELECT id, username FROM usuarios WHERE username=?',\n        (USERNAME,),\n    ).fetchone()\n\n    hashed = generate_password_hash(password)\n\n    if existing:\n        conn.execute(\n            "UPDATE usuarios SET password=?, nombre=?, rol='admin', activo=TRUE WHERE id=?",\n            (hashed, USERNAME, existing['id']),\n        )\n        user_id = int(existing['id'])\n        action = 'UPDATED'\n    else:\n        row = conn.execute(\n            """INSERT INTO usuarios(username,password,email,nombre,rol,activo)\n               VALUES(?,?,?,?,?,TRUE) RETURNING id""",\n            (USERNAME, hashed, f'{USERNAME.lower()}@lumeon.local', USERNAME, 'admin'),\n        ).fetchone()\n        user_id = int(row['id'])\n        action = 'CREATED'\n\n    conn.commit()\n    print(f'{action}: {USERNAME} (id={user_id}, rol=admin)')\n    print('GUARDA LA CONTRASEÑA EN UN LUGAR SEGURO; NO SE MOSTRARÁ NUEVAMENTE.')\nfinally:\n    conn.close()\n''', encoding='utf-8')
print('scripts/create_admin.py: OK')

print('\nIMPLEMENTATION READY')
print('1) Admin-only sale deletion + stock synchronization')
print('2) Admin audit/log page')
print('3) Console helper for AdminMichelle')
print('No database was modified by this script.')
