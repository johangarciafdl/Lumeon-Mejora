(() => {
  'use strict';

  const API = '/api/v2';
  const ASSISTANT_API = `${API}/assistant/message`;
  const AI_API = `${API}/assistant/ai`;
  const SESSION_KEY = 'lumeon_assistant_session';

  function ensureAssistantStyles() {
    if (document.getElementById('lumeon-assistant-inline-style')) return;
    const style = document.createElement('style');
    style.id = 'lumeon-assistant-inline-style';
    style.textContent = `
      #lumeon-assistant-fab{position:fixed!important;right:24px!important;bottom:24px!important;width:54px!important;height:54px!important;border:0!important;border-radius:50%!important;background:#1C2B3A!important;color:#fff!important;box-shadow:0 8px 24px rgba(26,24,20,.22)!important;cursor:pointer!important;z-index:3001!important;font-size:21px!important;display:flex!important;align-items:center!important;justify-content:center!important}
      #lumeon-assistant-fab.hidden{display:none!important}
      #lumeon-assistant{position:fixed!important;right:24px!important;bottom:24px!important;width:min(390px,calc(100vw - 32px))!important;height:min(620px,calc(100vh - 48px))!important;background:#fff!important;border:1px solid #E8E4DC!important;box-shadow:0 12px 40px rgba(26,24,20,.18)!important;z-index:3002!important;display:none!important;flex-direction:column!important}
      #lumeon-assistant.open{display:flex!important}
      .la-header{background:#1C2B3A;color:#fff;padding:16px 18px;display:flex;align-items:center;justify-content:space-between}
      .la-title{font-weight:600}.la-subtitle{font-size:10px;color:#8AACC0;margin-top:3px}.la-close{background:transparent;border:0;color:#fff;cursor:pointer;font-size:18px}
      .la-messages{flex:1;overflow:auto;padding:16px;background:#F7F6F3}.la-msg{max-width:86%;padding:10px 12px;margin-bottom:10px;border-radius:8px;font-size:12px;line-height:1.45;white-space:pre-wrap}.la-msg.bot{background:#fff;border:1px solid #E8E4DC}.la-msg.user{margin-left:auto;background:#1C2B3A;color:#fff}.la-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.la-action{border:1px solid #D4CFC5;background:#fff;padding:6px 9px;border-radius:4px;cursor:pointer;font-size:11px}.la-action.confirm{background:#2D5016;color:#fff;border-color:#2D5016}.la-action.cancel{background:#8B3A1C;color:#fff;border-color:#8B3A1C}.la-composer{display:flex;gap:8px;padding:12px;border-top:1px solid #E8E4DC;background:#fff}.la-input{flex:1;border:1px solid #D4CFC5;padding:10px 12px;border-radius:4px;outline:none}.la-send{background:#C9962A;color:#fff;border:0;border-radius:4px;padding:0 14px;cursor:pointer}
    `;
    document.head.appendChild(style);
  }

  function getAssistantSession() {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = (crypto.randomUUID ? crypto.randomUUID() : `web-${Date.now()}-${Math.random()}`);
      localStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }

  async function apiGet(path) {
    const response = await fetch(`${API}${path}`, { credentials: 'same-origin' });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
  }

  async function dashboardV2() {
    try {
      const [customers, products, sales] = await Promise.all([
        apiGet('/clientes?limit=100'),
        apiGet('/productos?q='),
        apiGet('/ventas?limit=100&q='),
      ]);
      const clients = customers.results || [];
      const prods = products.results || [];
      const saleRows = sales.results || [];
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, '0');
      const d = String(now.getDate()).padStart(2, '0');
      const today = `${y}-${m}-${d}`;
      const month = `${y}-${m}`;
      const ventasHoy = saleRows.filter(v => String(v.fecha || '').startsWith(today));
      const ventasMes = saleRows.filter(v => String(v.fecha || '').startsWith(month));
      const fmt = n => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0}).format(Number(n||0));
      const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
      const byMonth = {};
      saleRows.forEach(v => { const key = String(v.fecha||'').slice(5,7); if(key) byMonth[key]=(byMonth[key]||0)+Number(v.total||0); });

      const set = (id, value, sub) => {
        const el = document.getElementById(id); if (!el) return;
        el.innerHTML = value + (sub ? `<div class="kpi-sub">${sub}</div>` : '');
      };
      set('kpi-grid', '', '');
      const grid = document.getElementById('kpi-grid');
      if (grid) {
        const pending = saleRows.filter(v => String(v.estado).toLowerCase()==='pendiente').length;
        const paid = saleRows.filter(v => String(v.estado).toLowerCase()==='pagado').length;
        const noStock = prods.filter(p => Number(p.stock||0)<=0).length;
        const low = prods.filter(p => Number(p.stock||0)>0 && Number(p.stock||0)<=Number(p.stock_minimo||0)).length;
        const html = [
          ['gold','Ventas Hoy',fmt(ventasHoy.reduce((s,v)=>s+Number(v.total||0),0)),'Ingresos del día'],
          ['sage','Ventas del Mes',fmt(ventasMes.reduce((s,v)=>s+Number(v.total||0),0)),'Acumulado mensual'],
          ['terra','Ganancia del Mes',fmt(ventasMes.reduce((s,v)=>s+Number(v.ganancia||0),0)),'Margen estimado'],
          ['amber','Pendientes',pending,`${paid} pagadas`],
          ['slate','Sin Stock',noStock,`${low} con stock bajo`],
          ['blue','Clientes',clients.length,`${prods.length} productos`],
        ].map(([cls,label,value,sub])=>`<div class="kpi-card ${cls}"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-sub">${sub}</div></div>`).join('');
        grid.innerHTML = html;
      }
      const alertBox = document.getElementById('alertas-stock');
      if (alertBox) {
        const alerts = prods.filter(p=>Number(p.stock||0)<=Number(p.stock_minimo||0)).slice(0,20);
        alertBox.innerHTML = alerts.length ? alerts.map(a=>`<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:13px"><div><div style="font-weight:500">${a.nombre}</div><div style="color:var(--ink3);font-size:11px">${a.referencia}</div></div><div class="badge ${Number(a.stock||0)===0?'badge-red':'badge-amber'}">${Number(a.stock||0)===0?'Agotado':`${a.stock} un.`}</div></div>`).join('') : '<div style="color:var(--sage);padding:12px;font-size:13px;font-weight:500">Todo el inventario en orden</div>';
      }
      const bars = document.getElementById('chart-bars');
      if (bars) {
        const max = Math.max(...Object.values(byMonth),1);
        bars.innerHTML = Object.entries(byMonth).length ? Object.entries(byMonth).sort().map(([key,total])=>`<div class="bar-wrap"><div class="bar-val">${fmt(total)}</div><div class="bar" style="height:${Math.max(4,(total/max)*140)}px"></div><div class="bar-label">${meses[Number(key)-1]||key}</div></div>`).join('') : '<div style="color:var(--ink3);font-size:13px;padding:20px">Sin datos aún</div>';
      }
      const recent = document.querySelector('#tbl-recientes tbody');
      if (recent) recent.innerHTML = saleRows.slice(0,10).map(v=>`<tr><td class="td-mono">${v.numero_factura}</td><td>${v.cliente_nombre||'—'}</td><td class="td-mono">${fmt(v.total)}</td><td>${typeof window.badgeEstado==='function'?window.badgeEstado(v.estado):v.estado}</td><td style="color:var(--ink3)">${String(v.fecha||'').split('T')[0].split('-').reverse().join('/')}</td></tr>`).join('') || '<tr><td colspan="5" class="empty"><div class="empty-title">Sin transacciones</div></td></tr>';
    } catch (e) {
      console.error('LUMEON dashboard v2', e);
      if (typeof window.toast === 'function') window.toast(`No se pudo cargar el dashboard: ${e.message}`, 'error');
    }
  }

  async function loadClientesV2() {
    const q = (document.getElementById('cli-search')?.value || '').trim();
    try {
      const body = await apiGet(`/clientes?q=${encodeURIComponent(q)}&limit=100`);
      const data = body.results || [];
      const tbody = document.querySelector('#tbl-clientes tbody');
      if (!tbody) return;
      tbody.innerHTML = data.map(c => `<tr><td style="font-weight:500">${c.nombre||''}</td><td class="td-mono">${c.documento||'—'}</td><td>${c.telefono||'—'}</td><td>${c.ciudad||'—'}</td><td style="color:var(--ink3)">${c.email||'—'}</td><td style="display:flex;gap:4px"><button class="btn btn-ghost btn-sm btn-icon" onclick='window.editCliente(${JSON.stringify(c)})'>✎</button><button class="btn btn-danger btn-sm btn-icon" onclick='window.eliminarCliente(${Number(c.id)}, ${JSON.stringify(c.nombre||'Cliente')})'>✕</button></td></tr>`).join('') || '<tr><td colspan="6" class="empty"><div class="empty-title">Sin clientes</div></td></tr>';
    } catch (e) {
      if (typeof window.toast === 'function') window.toast(`Error clientes: ${e.message}`, 'error');
    }
  }

  async function loadInventarioV2() {
    const q = (document.getElementById('inv-search')?.value || '').trim();
    try {
      const body = await apiGet(`/productos?q=${encodeURIComponent(q)}&limit=100`);
      const data = body.results || [];
      const tbody = document.querySelector('#tbl-inventario tbody');
      if (!tbody) return;
      const fmt = window.fmt || (n=>n);
      tbody.innerHTML = data.map(p=>{
        const mg=Number(p.precio_venta||0)-Number(p.precio_compra||0);
        const mgp=Number(p.precio_compra||0)>0?(mg/Number(p.precio_compra)*100).toFixed(1)+'%':'—';
        const est=Number(p.stock||0)===0?'<span class="badge badge-red">Agotado</span>':Number(p.stock||0)<=Number(p.stock_minimo||0)?'<span class="badge badge-amber">Bajo</span>':'<span class="badge badge-green">OK</span>';
        return `<tr><td class="td-mono">${p.referencia||''}</td><td><div style="font-weight:500">${p.nombre||''}</div><div style="font-size:11px;color:var(--ink3)">${p.descripcion||''}</div></td><td><span class="badge badge-gray">${p.categoria||'General'}</span></td><td class="td-mono">${fmt(p.precio_compra)}</td><td class="td-mono">${fmt(p.precio_venta)}</td><td class="td-mono" style="color:var(--sage)">${fmt(mg)} <span style="color:var(--ink3)">${mgp}</span></td><td><strong>${p.stock}</strong></td><td>${est}</td><td><button class="btn btn-ghost btn-sm btn-icon" onclick='window.editProducto(${Number(p.id)})'>✎</button></td></tr>`;
      }).join('') || '<tr><td colspan="9" class="empty"><div class="empty-title">Sin productos</div></td></tr>';
    } catch (e) {
      if (typeof window.toast === 'function') window.toast(`Error inventario: ${e.message}`, 'error');
    }
  }

  async function loadVentasV2() {
    const q=(document.getElementById('venta-search')?.value||'').trim();
    try {
      const body=await apiGet(`/ventas?q=${encodeURIComponent(q)}&limit=100`);
      const data=body.results||[];
      const tbody=document.querySelector('#tbl-ventas tbody');
      if(!tbody)return;
      const fmt=window.fmt || (n=>n);
      tbody.innerHTML=data.map(v=>`<tr><td class="td-mono">${v.numero_factura}</td><td style="font-weight:500">${v.cliente_nombre||'—'}</td><td><span class="badge badge-blue">${v.ciclo||'—'}</span></td><td style="color:var(--ink3)">${String(v.fecha||'').split('T')[0].split('-').reverse().join('/')}</td><td>${v.forma_pago||'Contado'}</td><td class="td-mono" style="font-weight:600">${fmt(v.total)}</td><td class="td-mono" style="color:var(--sage)">${fmt(v.ganancia)}</td><td>${typeof window.badgeEstado==='function'?window.badgeEstado(v.estado):v.estado}</td><td><button class="btn btn-ghost btn-sm" onclick='window.editarVenta(${Number(v.id)})'>Ver</button></td></tr>`).join('') || '<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div></td></tr>';
    } catch(e) {
      if (typeof window.toast === 'function') window.toast(`Error ventas: ${e.message}`, 'error');
    }
  }

  async function saveVentaV2() {
    const items = Array.isArray(window.ventaItems) ? window.ventaItems : [];
    if (!items.length) { window.toast?.('Agrega al menos un producto','error'); return; }
    const cl=document.getElementById('vf-cliente');
    const selected=cl?.options?.[cl.selectedIndex];
    const clienteId=cl?.value || null;
    let nombre=selected?.text || '';
    if (nombre.startsWith('--')) nombre='';
    const payload={
      numero_factura:document.getElementById('vf-num').value.trim(),
      cliente_id:clienteId,
      cliente_nombre:nombre,
      cliente_email:document.getElementById('vf-email').value.trim(),
      cliente_telefono:document.getElementById('vf-tel').value.trim(),
      fecha:document.getElementById('vf-fecha').value || undefined,
      forma_pago:document.getElementById('vf-pago').value,
      estado:document.getElementById('vf-estado').value,
      notas:document.getElementById('vf-notas').value,
      items:items.map(i=>({referencia:i.referencia,cantidad:Number(i.cantidad)})),
    };
    if(!payload.numero_factura){window.toast?.('Ingresa el número de factura','error');return;}
    try {
      const r=await fetch(`${API}/ventas`,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)});
      const body=await r.json();
      if(!r.ok){window.toast?.(body.error||'No se pudo registrar la venta','error');return;}
      const saleId=body.venta_id;
      let whatsappText='Venta registrada';
      if(payload.cliente_telefono && saleId){
        const detail=await apiGet(`/ventas/${saleId}`);
        const invoice=detail.venta?.numero_factura || payload.numero_factura;
        const wr=await fetch(`${API}/invoices/${encodeURIComponent(invoice)}/whatsapp`,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:'{}'});
        const wb=await wr.json().catch(()=>({}));
        whatsappText += wr.ok ? ' · WhatsApp enviado' : ` · WhatsApp: ${wb.error||wb.delivery||'falló'}`;
      }
      window.toast?.(whatsappText, payload.cliente_telefono ? 'success' : 'warning');
      window.ventaItems=[];
      if(typeof window.closeModal==='function') window.closeModal('modal-venta');
      window.loadVentas?.(); window.loadDashboard?.(); window.loadInventario?.();
    } catch(e){ window.toast?.(`Error: ${e.message}`,'error'); }
  }

  async function assistantCall(url, text) {
    const headers={'Content-Type':'application/json','X-Assistant-Session':getAssistantSession()};
    const response=await fetch(url,{method:'POST',headers,credentials:'same-origin',body:JSON.stringify({text})});
    const body=await response.json().catch(()=>({}));
    if(!response.ok) throw new Error(body.error||`HTTP ${response.status}`);
    return body;
  }

  function mountAssistant() {
    ensureAssistantStyles();
    if(document.getElementById('lumeon-assistant')) return;
    const fab=document.createElement('button'); fab.id='lumeon-assistant-fab'; fab.title='Abrir asistente'; fab.textContent='✦';
    const panel=document.createElement('section'); panel.id='lumeon-assistant';
    panel.innerHTML=`<header class="la-header"><div><div class="la-title">Asistente Lumeon</div><div class="la-subtitle">IA + operaciones · ventas · inventario · facturas</div></div><button class="la-close" type="button">×</button></header><div class="la-messages" id="la-messages"></div><form class="la-composer"><input class="la-input" autocomplete="off" maxlength="1000" placeholder="Ej: registra una venta para Carlos con 2 de 70983"><button class="la-send" type="submit">Enviar</button></form>`;
    document.body.append(fab,panel);
    const input=panel.querySelector('.la-input');
    const messages=panel.querySelector('#la-messages');
    const add=(text,who='bot',actions=[])=>{ const div=document.createElement('div'); div.className=`la-msg ${who}`; div.textContent=text; if(actions.length){const box=document.createElement('div');box.className='la-actions';actions.forEach(a=>{const b=document.createElement('button');b.type='button';b.className=`la-action ${a.kind||''}`;b.textContent=a.label;b.onclick=a.onClick;box.appendChild(b)});div.appendChild(box)} messages.appendChild(div);messages.scrollTop=messages.scrollHeight; };
    const render=result=>{let text=result.message||result.error||'Operación procesada.'; if(Array.isArray(result.results)&&result.results.length) text+='\n'+result.results.slice(0,20).map((r,i)=>`${i+1}. ${Object.entries(r).map(([k,v])=>`${k}: ${v??''}`).join(' · ')}`).join('\n'); else if(Array.isArray(result.results)) text+='\nSin resultados.'; const wa=result.invoice_delivery?.whatsapp; if(wa?.status) text+=`\nWhatsApp: ${wa.status}${wa.error?` — ${wa.error}`:''}`; add(text,'bot',result.status==='confirmation_required'?[{label:'Confirmar',kind:'confirm',onClick:()=>handle('sí')},{label:'Cancelar',kind:'cancel',onClick:()=>handle('cancelar')}]:[]); };
    const handle=async text=>{ add(text,'user'); input.disabled=true; try{ let result=await assistantCall(ASSISTANT_API,text); if(result.status==='unknown'){ result=await assistantCall(AI_API,text); } render(result); }catch(e){add(`No pude completar la acción: ${e.message}`,'bot')}finally{input.disabled=false;input.focus();} };
    fab.onclick=()=>{ panel.classList.add('open'); fab.classList.add('hidden'); input.focus(); };
    panel.querySelector('.la-close').onclick=()=>{ panel.classList.remove('open'); fab.classList.remove('hidden'); };
    panel.querySelector('form').onsubmit=e=>{e.preventDefault();const text=input.value.trim();if(text){input.value='';handle(text)}};
    add('Hola. Puedo consultar o ejecutar operaciones. Las acciones destructivas piden confirmación. Una venta con teléfono puede generar y enviar su factura por WhatsApp automáticamente.','bot');
  }

  function patchUiFunctions() {
    window.loadDashboard = dashboardV2;
    window.loadClientes = loadClientesV2;
    window.loadInventario = loadInventarioV2;
    window.loadVentas = loadVentasV2;
    window.saveVenta = saveVentaV2;
    const oldClienteChange = window.onVentaClienteChange;
    window.onVentaClienteChange = async function(){
      const cid=document.getElementById('vf-cliente')?.value;
      if(!cid){document.getElementById('vf-email').value='';document.getElementById('vf-tel').value='';return;}
      try{
        const body=await apiGet('/clientes?q=');
        const c=(body.results||[]).find(x=>String(x.id)===String(cid));
        document.getElementById('vf-email').value=c?.email||'';
        document.getElementById('vf-tel').value=c?.telefono||'';
      }catch(e){ if(oldClienteChange) oldClienteChange(); }
    };
  }

  function start() {
    patchUiFunctions();
    mountAssistant();
    setTimeout(()=>window.loadDashboard?.(),150);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start); else start();
})();
