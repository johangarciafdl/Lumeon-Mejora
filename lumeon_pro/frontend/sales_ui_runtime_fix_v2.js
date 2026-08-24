(() => {
  'use strict';

  const SALES_API = '/api/v2/sales';
  const CLIENTS_API = '/api/v2/clientes';
  const LEGACY_API = '/api';
  let sales = [];
  let filter = '';
  let editingId = null;
  let ready = false;

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const safe = (v) => String(v ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  const money = (v) => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0}).format(Number(v||0));
  const dateOnly = (v) => !v ? '—' : String(v).slice(0,10).split('-').reverse().join('/');
  const toast = (m,t='success') => typeof window.toast === 'function' ? window.toast(m,t) : console.log(m);

  async function api(url, options={}) {
    const r = await fetch(url,{credentials:'same-origin',...options});
    const b = await r.json().catch(()=>({}));
    if(!r.ok || b.ok === false) throw new Error(b.error || `HTTP ${r.status}`);
    return b;
  }

  function admin() {
    return String(window.currentUser?.role || '').toLowerCase() === 'admin';
  }

  async function syncAuth() {
    try {
      const body = await api('/api/v2/auth/me');
      if(body.authenticated){
        window.currentUser = {
          username: String(body.username || body.user?.username || body.user_id || 'admin'),
          role: String(body.role || body.user?.role || '').toLowerCase(),
          user_id: body.user_id,
        };
      }
    } catch(e) {
      console.warn('sales runtime auth sync:', e.message);
    }
    $$('.admin-only-nav').forEach(el => el.style.display = admin() ? '' : 'none');
  }

  function showPage(page){
    const target = document.getElementById(`page-${page}`);
    if(!target) return;
    $$('.page').forEach(p=>p.classList.remove('active'));
    target.classList.add('active');
    $$('#sidebar .nav-item').forEach(n=>n.classList.remove('active'));
    $$('#sidebar .nav-item').forEach(n=>{
      const oc=n.getAttribute('onclick')||'';
      if(oc.includes(`'${page}'`) || oc.includes(`\"${page}\"`)) n.classList.add('active');
    });
    if(page==='admin-logs') $('#nav-registros')?.classList.add('active');
    const titles={dashboard:'Dashboard',inventario:'Inventario',ventas:'Ventas',clientes:'Clientes',ciclos:'Ciclos',devoluciones:'Devoluciones','admin-logs':'Registros'};
    if($('#topbar-title')) $('#topbar-title').textContent=titles[page]||page;
    window.currentPage=page;
    if(window.innerWidth<=768) window.closeMobileMenu?.();
    if(page==='ventas') loadSales();
    else if(page==='ciclos') loadCycles();
    else if(page==='dashboard') window.loadDashboard?.();
    else if(page==='inventario') window.loadInventario?.();
    else if(page==='clientes') window.loadClientes?.();
    else if(page==='devoluciones') window.loadDevoluciones?.();
    else if(page==='admin-logs') window.loadAdminLogs?.();
  }

  async function loadSales(){
    const tbody=$('#tbl-ventas tbody');
    if(!tbody) return;
    try{
      const q=($('#venta-search')?.value||'').trim();
      const body=await api(`${SALES_API}?q=${encodeURIComponent(q)}`);
      sales=Array.isArray(body.results)?body.results:[];
      renderSales();
    }catch(e){
      console.error('loadSales fixed:',e);
      tbody.innerHTML=`<tr><td colspan="9" class="empty"><div class="empty-title">Error al cargar ventas</div><div class="empty-text">${safe(e.message)}</div></td></tr>`;
    }
  }

  function renderSales(){
    const tbody=$('#tbl-ventas tbody');
    if(!tbody) return;
    const q=($('#venta-search')?.value||'').trim().toLowerCase();
    const rows=sales.filter(v=>{
      const text=[v.numero_factura,v.cliente_nombre,v.cliente_email,v.cliente_telefono].filter(Boolean).join(' ').toLowerCase();
      const state=String(v.estado||'Pendiente').toLowerCase();
      const payment=String(v.estado_pago||'').toLowerCase();
      const okFilter = !filter || (filter==='Abonado' ? payment==='abonado' : state===filter.toLowerCase());
      return okFilter && (!q || text.includes(q));
    });
    if(!rows.length){
      tbody.innerHTML='<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div><div class="empty-text">No hay ventas para este filtro.</div></td></tr>';
      return;
    }
    const isA=admin();
    tbody.innerHTML=rows.map(v=>{
      const state=String(v.estado||'Pendiente');
      const payment=String(v.estado_pago||state);
      const balance=Number(v.saldo_pendiente||0);
      const actions=[];
      if(isA) actions.push(`<button type="button" class="btn btn-ghost btn-sm btn-icon" data-sale-action="edit" data-id="${Number(v.id)}" title="Editar">✎</button>`);
      if(isA && state.toLowerCase()!=='pagado' && state.toLowerCase()!=='cancelado') actions.push(`<button type="button" class="btn btn-success btn-sm" data-sale-action="paid" data-id="${Number(v.id)}">Pagada</button>`);
      if(isA && balance>0 && state.toLowerCase()!=='cancelado') actions.push(`<button type="button" class="btn btn-gold btn-sm" data-sale-action="payment" data-id="${Number(v.id)}" data-invoice="${safe(v.numero_factura)}">Abono</button>`);
      if(isA && state.toLowerCase()==='pendiente') actions.push(`<button type="button" class="btn btn-ghost btn-sm btn-icon" data-sale-action="cancel" data-id="${Number(v.id)}" title="Cancelar">✕</button>`);
      if(isA) actions.push(`<button type="button" class="btn btn-danger btn-sm btn-icon" data-sale-action="delete" data-id="${Number(v.id)}" data-invoice="${safe(v.numero_factura)}" title="Eliminar">🗑</button>`);
      const badge=typeof window.badgeEstado==='function' ? window.badgeEstado(payment) : `<span class="badge badge-amber">${safe(payment)}</span>`;
      return `<tr>
        <td class="td-mono">${safe(v.numero_factura||'—')}</td>
        <td style="font-weight:500">${safe(v.cliente_nombre||'—')}</td>
        <td><span class="badge badge-blue">${safe(v.ciclo||'—')}</span></td>
        <td style="color:var(--ink3)">${dateOnly(v.fecha)}</td>
        <td>${safe(v.forma_pago||'Contado')}</td>
        <td class="td-mono" style="font-weight:600">${money(v.total)}</td>
        <td class="td-mono" style="color:var(--sage)">${money(v.ganancia)}</td>
        <td>${badge}</td>
        <td class="sales-actions">${actions.join('')||'<span style="font-size:11px;color:var(--ink3)">—</span>'}</td>
      </tr>`;
    }).join('');
    tbody.querySelectorAll('[data-sale-action]').forEach(b=>{
      const id=Number(b.dataset.id), action=b.dataset.saleAction;
      if(action==='edit') b.onclick=()=>openSale(id);
      if(action==='paid') b.onclick=()=>changeStatus(id,'Pagado');
      if(action==='cancel') b.onclick=()=>changeStatus(id,'Cancelado');
      if(action==='payment') b.onclick=()=>paymentModal(id,b.dataset.invoice||'');
      if(action==='delete') b.onclick=()=>deleteSale(id,b.dataset.invoice||'');
    });
  }

  async function changeStatus(id,state){
    try{
      await api(`${SALES_API}/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:state})});
      toast(state==='Pagado'?'Venta marcada como pagada':`Venta ${state.toLowerCase()}`);
      await loadSales();
      window.loadDashboard?.();
      loadCycles();
    }catch(e){toast(e.message,'error');}
  }

  async function deleteSale(id,invoice){
    if(!confirm(`¿Eliminar la venta ${invoice}?`)) return;
    try{
      await api(`${SALES_API}/${id}`,{method:'DELETE'});
      toast('Venta eliminada');
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      loadCycles();
    }catch(e){toast(e.message,'error');}
  }

  async function loadClients(selectedId){
    const body=await api(`${CLIENTS_API}?q=&limit=200`);
    const clients=body.results||[];
    const select=$('#vf-cliente');
    if(!select) return;
    select.innerHTML='<option value="">-- Sin cliente --</option>'+clients.map(c=>`<option value="${Number(c.id)}">${safe(c.nombre)}</option>`).join('');
    if(selectedId!=null) select.value=String(selectedId);
  }

  function modalOpen(){
    if(typeof window.openModal==='function') window.openModal('modal-venta');
    else $('#modal-venta')?.classList.add('open');
  }

  function resetSaleForm(){
    editingId=null;
    window.editVentaId=null;
    window.ventaItems=[];
    if($('#mv-title')) $('#mv-title').textContent='Nueva Venta';
    if($('#btn-save-venta')) $('#btn-save-venta').textContent='Registrar Venta';
    const today=new Date().toISOString().slice(0,10);
    if($('#vf-num')) $('#vf-num').value=`FAC-${Date.now()}`;
    if($('#vf-fecha')) $('#vf-fecha').value=today;
    ['vf-ciclo','vf-ciclo-inicio','vf-ciclo-fin','vf-email','vf-tel','vf-notas','vf-ref'].forEach(id=>{if($('#'+id)) $('#'+id).value='';});
    if($('#vf-cant')) $('#vf-cant').value='1';
    if($('#vf-pago')) $('#vf-pago').value='Contado';
    if($('#vf-estado')) $('#vf-estado').value='Pendiente';
    if($('#vf-abono-inicial')) $('#vf-abono-inicial').value='';
    if($('#vf-abono-inicial-group')) $('#vf-abono-inicial-group').style.display='none';
    if($('#sales-management-payments')) $('#sales-management-payments').style.display='none';
    if(typeof window.renderVentaItems==='function') window.renderVentaItems();
    else if($('#vf-items-body')) $('#vf-items-body').innerHTML='';
  }

  async function openNewSale(){
    try{
      resetSaleForm();
      await loadClients(null);
      modalOpen();
    }catch(e){toast(`No se pudo abrir nueva venta: ${e.message}`,'error');}
  }

  async function openSale(id){
    try{
      const body=await api(`${SALES_API}/${id}`);
      const v=body.venta||{};
      editingId=id; window.editVentaId=id;
      if($('#mv-title')) $('#mv-title').textContent='Editar Venta';
      if($('#btn-save-venta')) $('#btn-save-venta').textContent='Guardar cambios';
      if($('#vf-num')) $('#vf-num').value=v.numero_factura||'';
      if($('#vf-fecha')) $('#vf-fecha').value=v.fecha?String(v.fecha).slice(0,10):'';
      if($('#vf-ciclo')) $('#vf-ciclo').value=v.ciclo||'';
      if($('#vf-ciclo-inicio')) $('#vf-ciclo-inicio').value=v.fecha_inicio_ciclo||'';
      if($('#vf-ciclo-fin')) $('#vf-ciclo-fin').value=v.fecha_fin_ciclo||'';
      if($('#vf-pago')) $('#vf-pago').value=v.forma_pago||'Contado';
      if($('#vf-email')) $('#vf-email').value=v.cliente_email||'';
      if($('#vf-tel')) $('#vf-tel').value=v.cliente_telefono||'';
      if($('#vf-notas')) $('#vf-notas').value=v.notas||'';
      if($('#vf-estado')) $('#vf-estado').value=v.estado||'Pendiente';
      await loadClients(v.cliente_id);
      window.ventaItems=(body.items||[]).map(i=>({...i,cantidad:Number(i.cantidad||0)}));
      if(typeof window.renderVentaItems==='function') window.renderVentaItems();
      if($('#sales-management-payments')){
        const abonos=body.abonos||[];
        $('#sales-management-payments').style.display='';
        $('#sales-management-payments').innerHTML=`<div class="sales-payment-title">Historial de cuotas</div>${abonos.length?abonos.map((a,i)=>`<div class="sales-payment-row"><div><strong>Cuota ${i+1}</strong><div class="sales-payment-meta">${safe(a.forma_pago||'Abono')} · ${dateOnly(a.fecha)}</div></div><strong>${money(a.monto)}</strong></div>`).join(''):'<div class="sales-payment-empty">No hay abonos registrados.</div>'}<div class="sales-payment-totals"><span>Total abonado</span><strong>${money(v.total_abonado)}</strong></div><div class="sales-payment-totals"><span>Saldo pendiente</span><strong>${money(v.saldo_pendiente)}</strong></div>`;
      }
      modalOpen();
    }catch(e){toast(`No se pudo abrir la venta: ${e.message}`,'error');}
  }

  async function saveSale(){
    if(editingId!=null){
      const select=$('#vf-cliente');
      const payload={
        numero_factura:$('#vf-num')?.value.trim(),
        cliente_id:select?.value||null,
        cliente_nombre:select?.selectedOptions?.[0]?.text||'',
        cliente_email:$('#vf-email')?.value.trim()||'',
        cliente_telefono:$('#vf-tel')?.value.trim()||'',
        fecha:$('#vf-fecha')?.value||null,
        forma_pago:$('#vf-pago')?.value||'Contado',
        estado:$('#vf-estado')?.value||'Pendiente',
        notas:$('#vf-notas')?.value||'',
        ciclo:$('#vf-ciclo')?.value.trim()||'',
        fecha_inicio_ciclo:$('#vf-ciclo-inicio')?.value||null,
        fecha_fin_ciclo:$('#vf-ciclo-fin')?.value||null,
        items:window.ventaItems||[],
      };
      try{
        await api(`${SALES_API}/${editingId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        toast('Venta actualizada correctamente');
        if(typeof window.closeModal==='function') window.closeModal('modal-venta'); else $('#modal-venta')?.classList.remove('open');
        editingId=null;window.editVentaId=null;
        await loadSales();window.loadDashboard?.();loadCycles();
      }catch(e){toast(e.message,'error');}
      return;
    }
    const items=window.ventaItems||[];
    if(!items.length){toast('Agrega al menos un producto','error');return;}
    const payment=$('#vf-pago')?.value||'Contado';
    const total=items.reduce((s,i)=>s+Number(i.cantidad||0)*Number(i.precio_venta||0),0);
    let initial=0;
    if(payment==='Abono'){
      initial=Number($('#vf-abono-inicial')?.value||0);
      if(!Number.isFinite(initial)||initial<=0||initial>total){toast(`El abono inicial debe estar entre $1 y ${money(total)}`,'error');return;}
    }
    const select=$('#vf-cliente');
    const payload={numero_factura:$('#vf-num')?.value.trim(),cliente_id:select?.value||null,cliente_nombre:select?.selectedOptions?.[0]?.text||'',cliente_email:$('#vf-email')?.value.trim()||'',cliente_telefono:$('#vf-tel')?.value.trim()||'',fecha:$('#vf-fecha')?.value||null,forma_pago:payment,estado:'Pendiente',notas:$('#vf-notas')?.value||'',ciclo:$('#vf-ciclo')?.value.trim()||'',fecha_inicio_ciclo:$('#vf-ciclo-inicio')?.value||null,fecha_fin_ciclo:$('#vf-ciclo-fin')?.value||null,initial_payment:initial,items};
    try{
      await api(SALES_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      toast(payment==='Abono'?'Venta registrada con abono inicial':'Venta registrada correctamente');
      if(typeof window.closeModal==='function') window.closeModal('modal-venta'); else $('#modal-venta')?.classList.remove('open');
      window.ventaItems=[];
      await loadSales();window.loadDashboard?.();window.loadInventario?.();loadCycles();
    }catch(e){toast(e.message,'error');}
  }

  async function addItem(){
    const ref=$('#vf-ref')?.value.trim();
    const qty=Number($('#vf-cant')?.value||1);
    if(!ref){toast('Ingresa una referencia','error');return;}
    if(!Number.isInteger(qty)||qty<=0){toast('Cantidad inválida','error');return;}
    try{
      const body=await api(`${LEGACY_API}/productos/buscar/${encodeURIComponent(ref)}`);
      const p=body.result||body;
      if(!p?.id) throw new Error('Referencia no encontrada');
      if(!editingId && Number(p.stock||0)<qty) throw new Error(`Stock insuficiente. Disponible: ${p.stock}`);
      const items=window.ventaItems||[];
      const found=items.find(i=>String(i.referencia)===String(ref));
      if(found) found.cantidad=Number(found.cantidad||0)+qty;
      else items.push({producto_id:Number(p.id),referencia:p.referencia,nombre:p.nombre,cantidad:qty,precio_compra:Number(p.precio_compra||0),precio_venta:Number(p.precio_venta||0)});
      window.ventaItems=items;
      $('#vf-ref').value='';$('#vf-cant').value='1';
      if(typeof window.renderVentaItems==='function') window.renderVentaItems();
    }catch(e){toast(e.message,'error');}
  }

  function paymentModal(id,invoice){
    const old=$('#lumeon-fixed-payment');if(old)old.remove();
    const box=document.createElement('div');box.id='lumeon-fixed-payment';box.className='modal-overlay open';
    box.innerHTML=`<div class="modal" style="max-width:460px"><div class="modal-header"><div class="modal-title">Registrar abono</div><button class="btn-close" type="button">✕</button></div><div class="modal-body"><div style="font-size:12px;color:var(--ink3);margin-bottom:14px">Factura <strong>${safe(invoice)}</strong></div><div class="form-group"><label>Valor del abono</label><input id="fixed-payment-amount" type="number" min="1" step="1" placeholder="$0"></div><div class="form-group" style="margin-top:12px"><label>Forma de pago</label><select id="fixed-payment-method"><option>Abono</option><option>Contado</option><option>Transferencia</option><option>Nequi</option><option>Daviplata</option></select></div><div class="form-group" style="margin-top:12px"><label>Nota</label><input id="fixed-payment-note" placeholder="Opcional"></div></div><div class="modal-footer"><button class="btn btn-secondary" type="button" data-cancel>Cancelar</button><button class="btn btn-gold" type="button" data-save>Registrar abono</button></div></div>`;
    document.body.appendChild(box);
    const close=()=>box.remove();
    box.querySelector('.btn-close').onclick=close;box.querySelector('[data-cancel]').onclick=close;
    box.querySelector('[data-save]').onclick=async()=>{
      const amount=Number($('#fixed-payment-amount').value||0), method=$('#fixed-payment-method').value, note=$('#fixed-payment-note').value.trim();
      if(!Number.isFinite(amount)||amount<=0){toast('Ingresa un monto válido','error');return;}
      try{const result=await api(`${SALES_API}/${id}/payments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({monto:amount,forma_pago:method,nota:note})});close();toast(result.venta?.saldo_pendiente>0?`Abono registrado. Saldo: ${money(result.venta.saldo_pendiente)}`:'Abono registrado. Venta pagada.');await loadSales();window.loadDashboard?.();loadCycles();}catch(e){toast(e.message,'error');}
    };
    $('#fixed-payment-amount').focus();
  }

  async function loadCycles(){
    const container=$('#ciclos-container');
    if(!container) return;
    try{
      const r=await api(`${LEGACY_API}/ciclos`);
      const ciclos=Array.isArray(r)?r:(r.results||[]);
      if(!ciclos.length){container.innerHTML='<div class="empty"><div class="empty-title">Sin ciclos registrados</div><div class="empty-text">Las ventas con ciclo aparecerán aquí.</div></div>';return;}
      const summaries=await Promise.all(ciclos.map(c=>api(`${LEGACY_API}/ciclos/${encodeURIComponent(c)}/resumen`)));
      if(typeof window.renderCiclos==='function'){window.renderCiclos(summaries);return;}
      container.innerHTML=summaries.map(r=>`<div class="card"><div class="card-header"><div><div class="card-title">Ciclo ${safe(r.ciclo)}</div><div class="card-subtitle">${Number(r.num_ventas||0)} ventas</div></div><strong>${money(r.total)}</strong></div></div>`).join('');
    }catch(e){console.error('loadCycles fixed:',e);container.innerHTML=`<div class="empty"><div class="empty-title">Error al cargar ciclos</div><div class="empty-text">${safe(e.message)}</div></div>`;}
  }

  function bind(){
    if(ready) return;
    ready=true;
    syncAuth();
    const search=$('#venta-search'); if(search) search.oninput=renderSales;
    const states=['','Pendiente','Abonado','Pagado','Cancelado'];
    $$('#ventas-tabs .tab').forEach((button,index)=>{
      button.onclick=()=>{filter=states[index]||'';$$('#ventas-tabs .tab').forEach(b=>b.classList.remove('active'));button.classList.add('active');renderSales();};
    });
    const add=$('#vf-ref')?.parentElement?.querySelector('button'); if(add) add.onclick=addItem;
    $('#vf-ref')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();addItem();}});
    if($('#btn-save-venta')) $('#btn-save-venta').onclick=saveSale;
    const action=$('#topbar-action'); if(action) action.addEventListener('click',e=>{if(window.currentPage==='ventas'){e.preventDefault();e.stopImmediatePropagation();openNewSale();}},true);
    window.loadVentas=loadSales;
    window.editarVenta=openSale;
    window.saveVenta=saveSale;
    window.marcarPagada=id=>changeStatus(id,'Pagado');
    window.cambiarEstado=changeStatus;
    window.eliminarVenta=deleteSale;
    window.registrarAbono=paymentModal;
    window.openModalVenta=openNewSale;
    window.loadCiclos=loadCycles;
    if($('#page-ventas')?.classList.contains('active')) loadSales();
    if($('#page-ciclos')?.classList.contains('active')) loadCycles();
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',bind,{once:true});
  else bind();
})();
