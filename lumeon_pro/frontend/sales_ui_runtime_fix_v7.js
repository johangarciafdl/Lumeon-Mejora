(() => {
  'use strict';

  const V2 = '/api/v2';
  const API = '/api';
  let sales = [];
  let filter = '';
  let editingId = null;
  let saleItems = [];

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  const money = (v) => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0}).format(Number(v||0));
  const notify = (m,t='success') => typeof window.toast === 'function' ? window.toast(m,t) : console.log(m);
  const isAdmin = () => String(window.currentUser?.role || '').toLowerCase() === 'admin' || window.lumeonIsAdmin === true;

  async function req(url, options={}) {
    const r = await fetch(url, {credentials:'same-origin', ...options});
    const body = await r.json().catch(() => ({}));
    if (!r.ok || body.ok === false) throw new Error(body.error || `HTTP ${r.status}`);
    return body;
  }

  function resetSalesView() {
    filter = '';
    $$('#ventas-tabs .tab').forEach((t,i) => t.classList.toggle('active', i === 0));
    const search = $('#venta-search');
    if (search) search.value = '';
  }

  async function loadSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;
    try {
      const q = ($('#venta-search')?.value || '').trim();
      const rows = await req(`${API}/ventas?q=${encodeURIComponent(q)}&estado=`);
      sales = Array.isArray(rows) ? rows : (rows.results || []);
      renderSales();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty"><div class="empty-title">Error al cargar ventas</div><div class="empty-text">${esc(e.message)}</div></td></tr>`;
    }
  }

  function saleStatus(v) {
    return String(v.estado_pago || v.estado || 'Pendiente');
  }

  function renderSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;
    const q = ($('#venta-search')?.value || '').trim().toLowerCase();
    const f = filter.toLowerCase();
    const data = sales.filter(v => {
      const text = [v.numero_factura,v.cliente_nombre,v.cliente_email,v.cliente_telefono].filter(Boolean).join(' ').toLowerCase();
      const st = String(v.estado || '').toLowerCase();
      const ps = String(v.estado_pago || '').toLowerCase();
      const okState = !f || (f === 'abonado' ? ps === 'abonado' : st === f);
      return okState && (!q || text.includes(q));
    });
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div><div class="empty-text">No hay ventas para este filtro.</div></td></tr>';
      return;
    }
    tbody.innerHTML = data.map(v => {
      const admin = isAdmin();
      const st = String(v.estado || 'Pendiente').toLowerCase();
      const balance = Number(v.saldo_pendiente || 0);
      return `<tr>
        <td class="td-mono">${esc(v.numero_factura||'—')}</td>
        <td style="font-weight:500">${esc(v.cliente_nombre||'—')}</td>
        <td>${esc(v.ciclo||'—')}</td>
        <td style="color:var(--ink3)">${v.fecha ? String(v.fecha).slice(0,10).split('-').reverse().join('/') : '—'}</td>
        <td>${esc(v.forma_pago||'Contado')}</td>
        <td class="td-mono" style="font-weight:600">${money(v.total)}</td>
        <td class="td-mono" style="color:var(--sage)">${money(v.ganancia)}</td>
        <td>${typeof window.badgeEstado === 'function' ? window.badgeEstado(saleStatus(v)) : `<span class="badge badge-amber">${esc(saleStatus(v))}</span>`}</td>
        <td class="sales-actions" style="white-space:nowrap;display:flex;gap:4px;align-items:center">
          ${admin ? `<button type="button" class="btn btn-ghost btn-sm btn-icon" data-action="edit" data-id="${v.id}">✎</button>` : ''}
          ${admin && st !== 'pagado' && st !== 'cancelado' ? `<button type="button" class="btn btn-success btn-sm" data-action="paid" data-id="${v.id}">Pagada</button>` : ''}
          ${admin && balance > 0 && st !== 'cancelado' ? `<button type="button" class="btn btn-gold btn-sm" data-action="payment" data-id="${v.id}">Abono</button>` : ''}
          ${admin && st === 'pendiente' ? `<button type="button" class="btn btn-ghost btn-sm btn-icon" data-action="cancel" data-id="${v.id}">✕</button>` : ''}
          ${admin ? `<button type="button" class="btn btn-danger btn-sm btn-icon" data-action="delete" data-id="${v.id}" data-invoice="${esc(v.numero_factura||'')}">🗑</button>` : ''}
        </td>
      </tr>`;
    }).join('');
    tbody.querySelectorAll('[data-action]').forEach(btn => {
      const id = Number(btn.dataset.id);
      const a = btn.dataset.action;
      if (a === 'edit') btn.onclick = () => openSale(id);
      if (a === 'paid') btn.onclick = () => markPaid(id);
      if (a === 'payment') btn.onclick = () => addPayment(id);
      if (a === 'cancel') btn.onclick = () => changeStatus(id,'Cancelado');
      if (a === 'delete') btn.onclick = () => deleteSale(id,btn.dataset.invoice||'');
    });
  }

  function bindFilters() {
    const states = ['', 'Pendiente', 'Abonado', 'Pagado', 'Cancelado'];
    $$('#ventas-tabs .tab').forEach((tab,i) => {
      tab.type = 'button';
      tab.onclick = (e) => {
        e.preventDefault(); e.stopPropagation();
        filter = states[i] || '';
        $$('#ventas-tabs .tab').forEach((x,j)=>x.classList.toggle('active',j===i));
        renderSales();
      };
    });
    const search = $('#venta-search');
    if (search) search.oninput = renderSales;
  }

  function removeExtraNewSaleButtons() {
    $$('#page-ventas .page-header button').forEach(b => {
      if ((b.textContent||'').toLowerCase().includes('nueva venta')) b.remove();
    });
  }

  function closeSaleModal() {
    $('#modal-venta')?.classList.remove('open');
    editingId = null;
    saleItems = [];
    window.editVentaId = null;
    window.ventaItems = [];
  }

  async function loadClients(selected) {
    const data = await req(`${API}/clientes?q=`);
    const rows = Array.isArray(data) ? data : (data.results || []);
    const select = $('#vf-cliente');
    if (!select) return;
    select.innerHTML = '<option value="">-- Sin cliente --</option>' + rows.map(c=>`<option value="${c.id}">${esc(c.nombre)}</option>`).join('');
    if (selected != null) select.value = String(selected);
  }

  function calc() {
    return saleItems.reduce((a,i)=>{ const q=Number(i.cantidad||0), pv=Number(i.precio_venta||0), pc=Number(i.precio_compra||0); a.total += q*pv; a.gain += q*(pv-pc); return a; },{total:0,gain:0});
  }

  function renderItems() {
    window.ventaItems = saleItems;
    const body = $('#vf-items-body');
    if (!body) return;
    const c = calc();
    body.innerHTML = saleItems.map((i,n)=>`<tr><td>${esc(i.referencia)}</td><td>${esc(i.nombre)}</td><td>${i.cantidad}</td><td>${money(i.precio_compra)}</td><td>${money(i.precio_venta)}</td><td>${money(Number(i.cantidad)*Number(i.precio_venta))}</td><td><button type="button" class="btn btn-danger btn-sm btn-icon" onclick="window.removeSaleItem(${n});return false;">✕</button></td></tr>`).join('');
    if ($('#vs-sub')) $('#vs-sub').textContent = money(c.total);
    if ($('#vs-total')) $('#vs-total').textContent = money(c.total);
    if ($('#vs-gan')) $('#vs-gan').textContent = money(c.gain);
  }

  async function addSaleItem() {
    const ref = ($('#vf-ref')?.value||'').trim();
    const qty = Number($('#vf-cant')?.value||1);
    if (!ref) return notify('Ingresa la referencia','error');
    if (!Number.isInteger(qty) || qty <= 0) return notify('Cantidad inválida','error');
    try {
      const product = await req(`${API}/productos/buscar/${encodeURIComponent(ref)}`);
      if (!product?.id) throw new Error('Producto no encontrado');
      const ex = saleItems.find(x=>x.referencia===product.referencia);
      if (ex) ex.cantidad += qty;
      else saleItems.push({producto_id:Number(product.id),referencia:product.referencia,nombre:product.nombre,cantidad:qty,precio_compra:Number(product.precio_compra||0),precio_venta:Number(product.precio_venta||0)});
      renderItems();
      $('#vf-ref').value=''; $('#vf-cant').value='1';
    } catch(e){ notify(e.message,'error'); }
  }
  window.addSaleItem = addSaleItem;
  window.removeSaleItem = (n)=>{ saleItems.splice(n,1); renderItems(); };

  function bindModal() {
    const modal = $('#modal-venta');
    if (!modal) return;
    const closeButtons = modal.querySelectorAll('.btn-close,button');
    closeButtons.forEach(btn => {
      const t = (btn.textContent||'').trim().toLowerCase();
      if (t === 'cancelar' || t === '×') btn.onclick = (e)=>{e.preventDefault();e.stopPropagation();closeSaleModal();};
    });
    const add = $('#vf-ref')?.parentElement?.querySelector('button');
    if (add) add.onclick = (e)=>{e.preventDefault();e.stopPropagation();addSaleItem();};
    const ref = $('#vf-ref'); if (ref) ref.onkeydown=(e)=>{if(e.key==='Enter'){e.preventDefault();addSaleItem();}};
    const save = $('#btn-save-venta'); if (save) save.onclick=(e)=>{e.preventDefault();e.stopPropagation();saveSale();};
  }

  function resetNewSaleForm() {
    editingId=null; saleItems=[]; window.editVentaId=null; window.ventaItems=[];
    if ($('#mv-title')) $('#mv-title').textContent='Nueva Venta';
    if ($('#btn-save-venta')) $('#btn-save-venta').textContent='Registrar Venta';
    if ($('#vf-num')) $('#vf-num').value=`FAC-${Date.now()}`;
    if ($('#vf-fecha')) $('#vf-fecha').value=new Date().toISOString().slice(0,10);
    if ($('#vf-pago')) $('#vf-pago').value='Contado';
    if ($('#vf-estado')) $('#vf-estado').value='Pendiente';
    if ($('#vf-abono-inicial')) $('#vf-abono-inicial').value='';
    if ($('#abono-inicial-group')) $('#abono-inicial-group').style.display='none';
    const addRow=$('#vf-ref')?.parentElement; if(addRow)addRow.style.display='flex';
    const table=$('#vf-items-body')?.closest('.items-table-wrap'); if(table)table.style.display='block';
    renderItems();
  }

  async function openNewSale() {
    try { resetNewSaleForm(); await loadClients(null); bindModal(); $('#modal-venta')?.classList.add('open'); } catch(e){ notify(e.message,'error'); }
  }
  window.openModalVenta = openNewSale;

  async function openSale(id) {
    try {
      const d = await req(`${V2}/sales/${id}`);
      const v=d.venta||d;
      editingId=Number(id); window.editVentaId=editingId;
      if ($('#mv-title')) $('#mv-title').textContent='Editar Venta';
      if ($('#btn-save-venta')) $('#btn-save-venta').textContent='Guardar cambios';
      if ($('#vf-num')) $('#vf-num').value=v.numero_factura||'';
      if ($('#vf-fecha')) $('#vf-fecha').value=v.fecha?String(v.fecha).slice(0,10):'';
      if ($('#vf-ciclo')) $('#vf-ciclo').value=v.ciclo||'';
      if ($('#vf-ciclo-inicio')) $('#vf-ciclo-inicio').value=v.fecha_inicio_ciclo||'';
      if ($('#vf-ciclo-fin')) $('#vf-ciclo-fin').value=v.fecha_fin_ciclo||'';
      if ($('#vf-pago')) $('#vf-pago').value=v.forma_pago||'Contado';
      if ($('#vf-estado')) $('#vf-estado').value=v.estado||'Pendiente';
      if ($('#vf-email')) $('#vf-email').value=v.cliente_email||'';
      if ($('#vf-tel')) $('#vf-tel').value=v.cliente_telefono||'';
      if ($('#vf-notas')) $('#vf-notas').value=v.notas||'';
      await loadClients(v.cliente_id);
      saleItems=(d.items||[]).map(x=>({...x}));
      renderItems();
      bindModal();
      $('#modal-venta')?.classList.add('open');
    } catch(e){ notify(e.message,'error'); }
  }
  window.editarVenta=openSale; window.openSaleForEdit=openSale;

  async function saveSale() {
    const customer=$('#vf-cliente');
    const selectedName=customer?.options[customer.selectedIndex]?.text||'';
    const payload={
      numero_factura:($('#vf-num')?.value||'').trim(),
      cliente_id:customer?.value||null,
      cliente_nombre:selectedName,
      cliente_email:($('#vf-email')?.value||'').trim(),
      cliente_telefono:($('#vf-tel')?.value||'').trim(),
      fecha:$('#vf-fecha')?.value||'',
      forma_pago:$('#vf-pago')?.value||'Contado',
      estado:$('#vf-estado')?.value||'Pendiente',
      notas:$('#vf-notas')?.value||'',
      ciclo:($('#vf-ciclo')?.value||'').trim(),
      fecha_inicio_ciclo:$('#vf-ciclo-inicio')?.value||'',
      fecha_fin_ciclo:$('#vf-ciclo-fin')?.value||''
    };
    try {
      if (editingId) {
        payload.items = saleItems;
        await req(`${V2}/sales/${editingId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        notify('Venta actualizada correctamente');
      } else {
        const c=calc();
        if (!saleItems.length) return notify('Agrega al menos un producto','error');
        const form=payload.forma_pago;
        const initial=form==='Abono'?Number($('#vf-abono-inicial')?.value||0):0;
        if(form==='Abono' && (!Number.isFinite(initial)||initial<=0||initial>c.total)) return notify(`El abono inicial debe estar entre $1 y ${money(c.total)}`,'error');
        await req(`${V2}/sales`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,items:saleItems,initial_payment:initial})});
        notify('Venta registrada correctamente');
      }
      closeSaleModal();
      await loadSales();
      window.loadDashboard?.(); window.loadCiclos?.();
    } catch(e){ notify(e.message,'error'); }
  }
  window.saveVenta=saveSale;

  async function markPaid(id){
    try { await req(`${V2}/sales/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:'Pagado'})}); notify('Venta marcada como pagada'); await loadSales(); window.loadDashboard?.(); window.loadCiclos?.(); }
    catch(e){ notify(e.message,'error'); }
  }
  window.markSalePaid=markPaid; window.marcarPagada=markPaid;

  async function changeStatus(id,status){
    try { await req(`${V2}/sales/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:status})}); notify(`Venta ${status.toLowerCase()}`); await loadSales(); window.loadDashboard?.(); }
    catch(e){ notify(e.message,'error'); }
  }
  window.changeStatus=changeStatus; window.cambiarEstado=changeStatus; window.cancelSale=(id)=>changeStatus(id,'Cancelado');

  async function addPayment(id){
    const value=prompt('Valor del abono:');
    if(value===null) return;
    const amount=Number(String(value).replace(',','.'));
    if(!Number.isFinite(amount)||amount<=0) return notify('Monto inválido','error');
    try { await req(`${V2}/sales/${id}/payments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({monto:amount,forma_pago:'Abono'})}); notify('Abono registrado'); await loadSales(); window.loadDashboard?.(); window.loadCiclos?.(); }
    catch(e){ notify(e.message,'error'); }
  }
  window.addSalePayment=addPayment; window.registrarAbono=addPayment;

  async function deleteSale(id,invoice){
    if(!confirm(`¿Eliminar la venta ${invoice}?`)) return;
    try { await req(`${V2}/sales/${id}`,{method:'DELETE'}); notify('Venta eliminada'); await loadSales(); window.loadDashboard?.(); window.loadCiclos?.(); }
    catch(e){ notify(e.message,'error'); }
  }
  window.deleteSaleFromUi=deleteSale; window.eliminarVenta=deleteSale;

  function bindTopbar(){
    const action=$('#topbar-action');
    if(!action) return;
    action.onclick=(e)=>{ e.preventDefault(); e.stopPropagation(); if(window.currentPage==='ventas')openNewSale(); else if(window.currentPage==='inventario')window.openModalProducto?.(); else if(window.currentPage==='clientes')window.openModalCliente?.(); else if(window.currentPage==='devoluciones')window.openModalDevolucion?.(); };
  }

  function bindNavigation(){
    const original=window.goto;
    window.goto=(page)=>{
      if(typeof original==='function') original(page);
      if(page==='ventas'){
        setTimeout(()=>{ resetSalesView(); bindFilters(); bindModal(); bindTopbar(); removeExtraNewSaleButtons(); loadSales(); },20);
      }
    };
  }

  function start(){
    if(window.__lumeonSalesV7) return;
    window.__lumeonSalesV7=true;
    removeExtraNewSaleButtons();
    bindFilters();
    bindModal();
    bindTopbar();
    bindNavigation();
    if($('#page-ventas')?.classList.contains('active')){
      resetSalesView();
      loadSales();
    }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
