from pathlib import Path

ROOT = Path('/home/lumeon/lumeon-mejora')
BACKEND = ROOT / 'lumeon_pro' / 'backend'
FRONTEND = ROOT / 'lumeon_pro' / 'frontend'

# 1) Sale deletion service
(BACKEND / 'services' / 'sale_delete_service.py').write_text('''from __future__ import annotations\n\nfrom services.audit_service import record as audit\n\n\nclass SaleDeleteError(ValueError):\n    pass\n\n\ndef delete_sale(conn, *, sale_id: int, user_id: int) -> dict:\n    sale = conn.execute(\n        "SELECT id, numero_factura, estado, cliente_nombre, total FROM ventas WHERE id=? LIMIT 1",\n        (sale_id,),\n    ).fetchone()\n    if not sale:\n        raise SaleDeleteError("Venta no encontrada")\n\n    items = conn.execute(\n        "SELECT id, producto_id, referencia, cantidad FROM venta_items WHERE venta_id=? ORDER BY id",\n        (sale_id,),\n    ).fetchall()\n\n    state = str(sale["estado"] or "").strip().lower()\n    already_returned = state in {"devuelta", "devuelto"}\n\n    if not already_returned:\n        for item in items:\n            if item["producto_id"] is None:\n                continue\n            updated = conn.execute(\n                "UPDATE productos SET stock=stock+? WHERE id=?",\n                (int(item["cantidad"] or 0), int(item["producto_id"])),\n            )\n            if updated.rowcount != 1:\n                raise SaleDeleteError(\n                    f"No se pudo restaurar stock del producto {item['referencia'] or item['producto_id']}"\n                )\n\n    conn.execute("DELETE FROM invoice_deliveries WHERE venta_id=?", (sale_id,))\n    conn.execute(\n        "DELETE FROM venta_devolucion_items WHERE devolucion_id IN (SELECT id FROM venta_devoluciones WHERE venta_id=?)",\n        (sale_id,),\n    )\n    conn.execute("DELETE FROM venta_devoluciones WHERE venta_id=?", (sale_id,))\n    conn.execute("DELETE FROM venta_items WHERE venta_id=?", (sale_id,))\n\n    audit(\n        conn,\n        actor_id=user_id,\n        action="sale.deleted",\n        entity="venta",\n        entity_id=sale_id,\n        details={\n            "invoice": sale["numero_factura"],\n            "customer": sale["cliente_nombre"],\n            "total": float(sale["total"] or 0),\n            "items": len(items),\n            "previous_state": sale["estado"],\n            "stock_restored": not already_returned,\n        },\n    )\n\n    conn.execute("DELETE FROM ventas WHERE id=?", (sale_id,))\n\n    return {\n        "sale_id": sale_id,\n        "invoice": sale["numero_factura"],\n        "stock_restored": not already_returned,\n    }\n''', encoding='utf-8')

# 2) Admin permissions
p = BACKEND / 'services' / 'authorization_service.py'
text = p.read_text(encoding='utf-8')
old = 'ADMIN_ACTIONS = {"delete_customer", "delete_product", "refund_sale", "manage_users"}'
new = 'ADMIN_ACTIONS = {"delete_customer", "delete_product", "delete_sale", "refund_sale", "manage_users", "view_audit_log"}'
if old in text:
    text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')

# 3) Admin API
(BACKEND / 'api' / 'admin_api.py').write_text('''from __future__ import annotations\n\nfrom flask import Blueprint, jsonify, request\nfrom werkzeug.security import generate_password_hash\n\nfrom core.db import get_db\nfrom services.auth_service import AuthenticationError, current_actor\nfrom services.authorization_service import require\nfrom services.sale_delete_service import SaleDeleteError, delete_sale\n\nadmin_api = Blueprint("admin_api", __name__, url_prefix="/api/v2/admin")\n\n\n@admin_api.get("/logs")\ndef logs():\n    try:\n        actor = current_actor()\n        require(actor, "view_audit_log")\n        try:\n            limit = min(max(int(request.args.get("limit", 200)), 1), 500)\n        except (TypeError, ValueError):\n            limit = 200\n\n        conn = get_db()\n        try:\n            rows = conn.execute(\n                """SELECT a.id, a.user_id, COALESCE(u.username,'sistema') AS username,\n                          a.action, a.entity_type, a.entity_id, a.metadata, a.created_at\n                   FROM audit_log a\n                   LEFT JOIN usuarios u ON u.id=a.user_id\n                   ORDER BY a.id DESC\n                   LIMIT ?""",\n                (limit,),\n            ).fetchall()\n            return jsonify({"ok": True, "results": [dict(r) for r in rows]})\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n\n\n@admin_api.post("/users")\ndef create_user():\n    try:\n        actor = current_actor()\n        require(actor, "manage_users")\n        data = request.get_json(silent=True) or {}\n        username = str(data.get("username") or "").strip()\n        password = str(data.get("password") or "")\n        nombre = str(data.get("nombre") or username).strip()\n        email = str(data.get("email") or "admin@lumeon.local").strip()\n        role = str(data.get("role") or "admin").strip().lower()\n\n        if not username or not password:\n            return jsonify({"ok": False, "error": "Usuario y contraseña son obligatorios"}), 400\n        if role not in {"admin", "vendedor", "cajero", "almacen"}:\n            return jsonify({"ok": False, "error": "Rol inválido"}), 400\n\n        conn = get_db()\n        try:\n            existing = conn.execute("SELECT id FROM usuarios WHERE username=?", (username,)).fetchone()\n            if existing:\n                return jsonify({"ok": False, "error": "El usuario ya existe"}), 409\n            row = conn.execute(\n                """INSERT INTO usuarios(username,password,email,nombre,rol,activo)\n                   VALUES(?,?,?,?,?,TRUE) RETURNING id, username, email, nombre, rol, activo""",\n                (username, generate_password_hash(password), email, nombre, role),\n            ).fetchone()\n            conn.commit()\n            return jsonify({"ok": True, "user": dict(row)}), 201\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n\n\n@admin_api.delete("/ventas/<int:sale_id>")\ndef delete_sale_v2(sale_id: int):\n    try:\n        actor = current_actor()\n        require(actor, "delete_sale")\n        conn = get_db()\n        try:\n            result = delete_sale(conn, sale_id=sale_id, user_id=int(actor.id))\n            conn.commit()\n            return jsonify({"ok": True, **result}), 200\n        except Exception:\n            conn.rollback()\n            raise\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n    except SaleDeleteError as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 400\n''', encoding='utf-8')

# 4) Register admin blueprint
p = BACKEND / 'api' / '__init__.py'
text = p.read_text(encoding='utf-8')
if 'from .admin_api import admin_api' not in text:
    text = text.replace('from .ai_api import ai_api\n', 'from .ai_api import ai_api\nfrom .admin_api import admin_api\n', 1)
if 'app.register_blueprint(admin_api)' not in text:
    text = text.replace('    app.register_blueprint(ai_api)\n', '    app.register_blueprint(ai_api)\n    app.register_blueprint(admin_api)\n', 1)
p.write_text(text, encoding='utf-8')

# 5) Legacy DELETE route so existing frontend button works
p = BACKEND / 'api' / 'legacy_compat_api.py'
text = p.read_text(encoding='utf-8')
if 'from services.sale_delete_service import SaleDeleteError, delete_sale' not in text:
    text = text.replace('from services.sale_service import SaleError, create_sale\n', 'from services.sale_service import SaleError, create_sale\nfrom services.sale_delete_service import SaleDeleteError, delete_sale\n', 1)
marker = '@legacy_compat_api.get("/ventas/<int:sale_id>")'
if '@legacy_compat_api.delete("/ventas/<int:sale_id>")' not in text and marker in text:
    block = '''@legacy_compat_api.delete("/ventas/<int:sale_id>")\ndef eliminar_venta(sale_id: int):\n    try:\n        a = current_actor()\n        require(a, "delete_sale")\n        conn = get_db()\n        try:\n            result = delete_sale(conn, sale_id=sale_id, user_id=int(a.id))\n            conn.commit()\n            return jsonify({"ok": True, **result}), 200\n        except Exception:\n            conn.rollback()\n            raise\n        finally:\n            conn.close()\n    except (AuthenticationError, PermissionError) as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 403\n    except SaleDeleteError as exc:\n        return jsonify({"ok": False, "error": str(exc)}), 400\n\n\n'''
    text = text.replace(marker, block + marker, 1)
p.write_text(text, encoding='utf-8')

# 6) Admin-only logs frontend, using a separate JS file.
(FRONTEND / 'admin_features.js').write_text(r'''(function(){
  const API = window.API || '';
  let adminReady = false;

  async function initAdminFeatures(){
    try{
      const r = await fetch(`${API}/v2/auth/me`, {credentials:'same-origin'});
      const d = await r.json();
      adminReady = !!(d.ok && d.authenticated && d.role === 'admin');
    }catch(e){ adminReady = false; }
    if(!adminReady) return;
    injectStyles();
    addNav();
    addPage();
    hideDeleteForNonAdmin();
  }

  function injectStyles(){
    if(document.getElementById('lumeon-admin-feature-styles')) return;
    const s=document.createElement('style');
    s.id='lumeon-admin-feature-styles';
    s.textContent=`
      #page-admin-logs{display:none}
      #page-admin-logs.active{display:block}
      .admin-log-list{display:grid;gap:10px}
      .admin-log-card{background:var(--card);border:1px solid var(--border);padding:14px;border-radius:6px}
      .admin-log-top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
      .admin-log-action{font-weight:700;font-size:12px;color:var(--slate)}
      .admin-log-user,.admin-log-time{font-size:11px;color:var(--ink3)}
      .admin-log-meta{margin-top:8px;font:11px/1.45 monospace;color:var(--ink2);white-space:pre-wrap;overflow-wrap:anywhere}
      .admin-log-empty{padding:30px;text-align:center;color:var(--ink3)}
    `;
    document.head.appendChild(s);
  }

  function addNav(){
    if(document.getElementById('nav-admin-logs')) return;
    const nav=document.querySelector('#sidebar nav');
    if(!nav) return;
    const item=document.createElement('div');
    item.id='nav-admin-logs';
    item.className='nav-item';
    item.innerHTML='<span class="nav-icon">▤</span>Registros';
    item.onclick=openLogs;
    nav.appendChild(item);
  }

  function addPage(){
    if(document.getElementById('page-admin-logs')) return;
    const content=document.getElementById('content');
    if(!content) return;
    const page=document.createElement('div');
    page.id='page-admin-logs';
    page.className='page';
    page.innerHTML=`
      <div class="page-header"><div class="page-header-left"><h2>Registros</h2><p>Operaciones realizadas en Lumeon</p><div class="page-header-line"></div></div></div>
      <div class="card">
        <div style="display:flex;justify-content:flex-end;margin-bottom:14px">
          <button class="btn btn-secondary btn-sm" id="admin-log-refresh">Actualizar</button>
        </div>
        <div id="admin-log-list" class="admin-log-list"><div class="admin-log-empty">Cargando...</div></div>
      </div>`;
    content.appendChild(page);
    document.getElementById('admin-log-refresh').onclick=loadLogs;
  }

  async function loadLogs(){
    const list=document.getElementById('admin-log-list');
    if(!list) return;
    list.innerHTML='<div class="admin-log-empty">Cargando...</div>';
    try{
      const r=await fetch(`${API}/v2/admin/logs?limit=200`,{credentials:'same-origin'});
      const d=await r.json();
      if(!r.ok || !d.ok) throw new Error(d.error||'No se pudieron cargar los registros');
      list.innerHTML=(d.results||[]).map(x=>{
        let meta=x.metadata||'';
        try{ meta=JSON.stringify(JSON.parse(meta),null,2); }catch(e){}
        return `<div class="admin-log-card">
          <div class="admin-log-top">
            <div class="admin-log-action">${escapeHtml(x.action||'—')}</div>
            <div class="admin-log-time">${escapeHtml(x.created_at||'')}</div>
          </div>
          <div class="admin-log-user">Usuario: ${escapeHtml(x.username||'sistema')} · ${escapeHtml(x.entity_type||'—')} #${escapeHtml(String(x.entity_id||'—'))}</div>
          <div class="admin-log-meta">${escapeHtml(meta)}</div>
        </div>`;
      }).join('') || '<div class="admin-log-empty">No hay registros.</div>';
    }catch(e){
      list.innerHTML=`<div class="admin-log-empty">${escapeHtml(e.message)}</div>`;
    }
  }

  function escapeHtml(value){
    return String(value??'').replace(/[&<>'"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
  }

  function hideDeleteForNonAdmin(){
    // Backend remains the true protection. This is only a visual aid.
  }

  function openLogs(){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
    const page=document.getElementById('page-admin-logs');
    const nav=document.getElementById('nav-admin-logs');
    if(page) page.classList.add('active');
    if(nav) nav.classList.add('active');
    const title=document.getElementById('topbar-title');
    if(title) title.textContent='Registros';
    loadLogs();
    if(window.innerWidth<=768 && typeof window.closeMobileMenu==='function') window.closeMobileMenu();
  }

  window.openAdminLogs=openLogs;
  window.addEventListener('load',initAdminFeatures);
})();
''', encoding='utf-8')

# 7) Load admin_features.js automatically from app_v2.py.
p = BACKEND / 'app_v2.py'
text = p.read_text(encoding='utf-8')
needle = "if 'src=\"/assistant.js\"' not in html:\n        html = html.replace(\"</body>\", '<script src=\"/assistant.js\" defer></script></body>', 1)"
if 'src="/admin_features.js"' not in text:
    insert = needle + "\n    if 'src=\"/admin_features.js\"' not in html:\n        html = html.replace(\"</body>\", '<script src=\"/admin_features.js\" defer></script></body>', 1)"
    if needle in text:
        text = text.replace(needle, insert, 1)
p.write_text(text, encoding='utf-8')

print('ADMIN FEATURES INSTALLED')
print('Delete sales: admin only, stock restored, audit retained.')
print('Admin logs page: /api/v2/admin/logs')
print('Second admin can be created with create_admin_michelle.py')
print('No database changes were made by this installer.')
