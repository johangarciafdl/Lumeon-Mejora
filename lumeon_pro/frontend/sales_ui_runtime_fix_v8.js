(() => {
  'use strict';

  const V2 = '/api/v2';
  const API = '/api';
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const esc = (v) => String(v ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  const money = (v) => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',minimumFractionDigits:0}).format(Number(v||0));
  const notify = (m,t='success') => window.toast ? window.toast(m,t) : console.log(m);
  const admin = () => String(window.currentUser?.role||'').toLowerCase()==='admin' || window.lumeonIsAdmin===true;

  let rows = [];
  let stateFilter = '';
  let editId = null;
  let items = [];
  let booted = false;

  async function request(url, options={}) {
    const r = await fetch(url,{credentials:'same-origin',...options});
    const body = await r.json().catch(()=>({}));
    if(!r.ok || body.ok===false) throw new Error(body.error || `HTTP ${r.status}`);
    return body;
  }

  function resetFilter() {
    stateFilter='';
    $$('#ventas-tabs .tab').forEach((t,i)=>t.classList.toggle('active',i===0));
    if($('#venta-search')) $('#venta-search').value='';
  }

  async function loadVentas() {
    const tbody=$('#tbl-ventas tbody');
    if(!tbody) return;
    try {
      const q=($('#venta-search')?.value||'').trim();
      // Legacy GET is the stable compatibility endpoint and is known to contain the existing records.
      const data=await request(`${API}/ventas?q=${encodeURIComponent(q)}&estado=`);
      rows=Array.isArray(data)?data:(data.results||[]);
      render();
    } catch(e) {
      tbody.innerHTML=`<tr><td colspan="9" class="empty"><div class="empty-title">Error al cargar ventas</div><div class="empty-text">${esc(e.message)}</div></td></tr>`;
    }
  }
  window.loadVentas=loadVentas;

  function render() {
    const tbody=$('#tbl-ventas tbody');
    if(!tbody) return;
    const q=($('#venta-search')?.value||'').trim().toLowerCase();
    const f=String(stateFilter||'').toLowerCase();
    const data=rows.filter(v=>{
      const text=[v.numero_factura,v.cliente_nombre,v.cliente_email,v.cliente_telefono].filter(Boolean).join(' ').toLowerCase();
      const st=String(v.estado||'').toLowerCase();
      const ps=String(v.estado_pago||'').toLowerCase();
      const matchState=!f || (f==='abonado'?ps==='abonado':st===f);
      return matchState && (!q || text.includes(q));
    });
    if(!data.length){
      tbody.innerHTML='<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div><div class="empty-text">No hay ventas para este filtro.</div></td></tr>';
      return;
    }
    tbody.innerHTML=data.map(v=>{
      const st=String(v.estado||'Pendiente');
      const ps=String(v.estado_pago||st);
      const balance=Number(v.saldo_pendiente||0);
      const canPay=admin() && !['pagado','cancelado'].includes(st.toLowerCase());
      return `<tr>
        <td class="td-mono">${esc(v.numero_factura||'—')}</td>
        <td style="font-weight:500">${esc(v.cliente_nombre||'—')}</td>
        <td>${esc(v.ciclo||'—')}</td>
        <td>${v.fecha?String(v.fecha).slice(0,10).split('-').reverse().join('/'): '—'}</td>
        <td>${esc(v.forma_pago||'Contado')}</td>
        <td class="td-mono" style="font-weight:600">${money(v.total)}</td>
        <td class="td-mono" style="color:var(--sage)">${money(v.ganancia)}</td>
        <td>${window.badgeEstado?window.badgeEstado(ps):`<span class="badge badge-amber">${esc(ps)}</span>`}</td>
        <td class="sales-actions" style="white-space:nowrap;display:flex;gap:4px;align-items:center">
          ${admin()?`<button type="button" class="btn btn-ghost btn-sm btn-icon" data-act="edit" data-id="${v.id}">✎</button>`:''}
          ${canPay?`<button type="button" class="btn btn-success btn-sm" data-act="paid" data-id="${v.id}">Pagada</button>`:''}
          ${admin()&&balance>0&&st.toLowerCase()!=='cancelado'?`<button type="button" class="btn btn-gold btn-sm" data-act="payment" data-id="${v.id}">Abono</button>`:''}
          ${admin()&&st.toLowerCase()==='pendiente'?`<button type="button" class="btn btn-ghost btn-sm btn-icon" data-act="cancel" data-id="${v.id}">✕</button>`:''}
          ${admin()?`<button type="button" class="btn btn-danger btn-sm btn-icon" data-act="delete" data-id="${v.id}" data-invoice="${esc(v.numero_factura||'')}">🗑</button>`:''}
        </td>
      </tr>`;
    }).join('');
    tbody.querySelectorAll('[data-act]').forEach(b=>{
      const id=Number(b.dataset.id), a=b.dataset.act;
      if(a==='edit') b.onclick=()=>openEdit(id);
      if(a==='paid') b.onclick=()=>setStatus(id,'Pagado');
      if(a==='payment') b.onclick=()=>addPayment(id);
      if(a==='cancel') b.onclick=()=>setStatus(id,'Cancelado');
      if(a==='delete') b.onclick=()=>removeSale(id,b.dataset.invoice||'');
    });
  }

  window.filterVentas=(button,state)=>{
    stateFilter=String(state||'');
    $$('#ventas-tabs .tab').forEach(t=>t.classList.remove('active'));
    button?.classList.add('active');
    render();
  };

  function bindFilters(){
    const states=['','Pendiente','Abonado','Pagado','Cancelado'];
    $$('#ventas-tabs .tab').forEach((b,i)=>{
      b.type='button';
      b.onclick=(e)=>{e.preventDefault();e.stopPropagation();window.filterVentas(b,states[i]||'');};
    });
    const search=$('#venta-search');
    if(search) search.oninput=render;
  }

  function removePageNewSaleButtons(){
    $$('#page-ventas .page-header button').forEach(b=>{
      if((b.textContent||'').toLowerCase().includes('nueva venta')) b.remove();
    });
  }

  async function clients(selected=null){
    const data=await request(`${API}/clientes?q=`);
    const list=Array.isArray(data)?data:(data.results||[]);
    const s=$('#vf-cliente');
    if(!s) return;
    s.innerHTML='<option value="">-- Sin cliente --</option>'+list.map(c=>`<option value="${c.id}">${esc(c.nombre)}</option>`).join('');
    if(selected!=null) s.value=String(selected);
  }

  function calc(){return items.reduce((a,i)=>{const q=Number(i.cantidad||0),p=Number(i.precio_venta||0),c=Number(i.precio_compra||0);a.total+=q*p;a.gain+=q*(p-c);return a;},{total:0,gain:0});}

  function renderItems(){
    window.ventaItems=items;
    const body=$('#vf-items-body');
    if(!body) return;
    const c=calc();
    body.innerHTML=items.map((i,n)=>`<tr><td>${esc(i.referencia)}</td><td>${esc(i.nombre)}</td><td>${i.cantidad}</td><td>${money(i.precio_compra)}</td><td>${money(i.precio_venta)}</td><td>${money(i.cantidad*i.precio_venta)}</td><td><button type="button" class="btn btn-danger btn-sm btn-icon" data-rm="${n}">✕</button></td></tr>`).join('');
    if($('#vs-sub')) $('#vs-sub').textContent=money(c.total);
    if($('#vs-total')) $('#vs-total').textContent=money(c.total);
    if($('#vs-gan')) $('#vs-gan').textContent=money(c.gain);
    body.querySelectorAll('[data-rm]').forEach(b=>b.onclick=()=>{items.splice(Number(b.dataset.rm),1);renderItems();});
  }

  async function addItem(){
    const ref=($('#vf-ref')?.value||'').trim();
    const qty=Number($('#vf-cant')?.value||1);
    if(!ref) return notify('Ingresa la referencia','error');
    if(!Number.isInteger(qty)||qty<=0) return notify('Cantidad inválida','error');
    try{
      const p=await request(`${API}/productos/buscar/${encodeURIComponent(ref)}`);
      if(!p?.id) throw new Error('Producto no encontrado');
      const ex=items.find(x=>x.referencia===p.referencia);
      if(ex) ex.cantidad+=qty;
      else items.push({producto_id:Number(p.id),referencia:p.referencia,nombre:p.nombre,cantidad:qty,precio_compra:Number(p.precio_compra||0),precio_venta:Number(p.precio_venta||0)});
      renderItems();
      $('#vf-ref').value=''; $('#vf-cant').value='1';
    }catch(e){notify(e.message,'error');}
  }
  window.addSaleItem=addItem;

  function modalOpen(){ $('#modal-venta')?.classList.add('open'); }
  function modalClose(){ $('#modal-venta')?.classList.remove('open'); editId=null; items=[]; window.editVentaId=null; window.ventaItems=[]; }

  function bindModal(){
    const m=$('#modal-venta'); if(!m) return;
    const add=$('#vf-ref')?.parentElement?.querySelector('button'); if(add){add.type='button';add.onclick=(e)=>{e.preventDefault();addItem();};}
    const ref=$('#vf-ref'); if(ref) ref.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();addItem();}};
    const save=$('#btn-save-venta'); if(save){save.type='button';save.onclick=(e)=>{e.preventDefault();saveSale();};}
    m.querySelectorAll('button').forEach(b=>{const t=(b.textContent||'').trim().toLowerCase();if(t==='cancelar'||t==='×'||String(b.className).includes('btn-close')) b.onclick=(e)=>{e.preventDefault();modalClose();};});
    const pay=$('#vf-pago'); if(pay) pay.onchange=()=>{const g=$('#abono-inicial-group');if(g)g.style.display=pay.value==='Abono'?'':'none';};
  }

  async function openNew(){
    try{
      editId=null; items=[]; window.editVentaId=null; window.ventaItems=[];
      if($('#mv-title')) $('#mv-title').textContent='Nueva Venta';
      if($('#btn-save-venta')) $('#btn-save-venta').textContent='Registrar Venta';
      if($('#vf-num')) $('#vf-num').value=`FAC-${Date.now()}`;
      if($('#vf-fecha')) $('#vf-fecha').value=new Date().toISOString().slice(0,10);
      if($('#vf-pago')) $('#vf-pago').value='Contado';
      if($('#vf-estado')) $('#vf-estado').value='Pendiente';
      await clients(null); renderItems(); bindModal(); modalOpen();
    }catch(e){notify(e.message,'error');}
  }
  window.openModalVenta=openNew;

  async function openEdit(id){
    try{
      const d=await request(`${V2}/sales/${id}`); const v=d.venta||{};
      editId=Number(id); window.editVentaId=editId;
      if($('#mv-title')) $('#mv-title').textContent='Editar Venta';
      if($('#btn-save-venta')) $('#btn-save-venta').textContent='Guardar cambios';
      if($('#vf-num')) $('#vf-num').value=v.numero_factura||'';
      if($('#vf-fecha')) $('#vf-fecha').value=v.fecha?String(v.fecha).slice(0,10):'';
      if($('#vf-ciclo')) $('#vf-ciclo').value=v.ciclo||'';
      if($('#vf-ciclo-inicio')) $('#vf-ciclo-inicio').value=v.fecha_inicio_ciclo||'';
      if($('#vf-ciclo-fin')) $('#vf-ciclo-fin').value=v.fecha_fin_ciclo||'';
      if($('#vf-pago')) $('#vf-pago').value=v.forma_pago||'Contado';
      if($('#vf-estado')) $('#vf-estado').value=v.estado||'Pendiente';
      if($('#vf-email')) $('#vf-email').value=v.cliente_email||'';
      if($('#vf-tel')) $('#vf-tel').value=v.cliente_telefono||'';
      if($('#vf-notas')) $('#vf-notas').value=v.notas||'';
      await clients(v.cliente_id); items=(d.items||[]).map(x=>({...x})); renderItems(); bindModal(); modalOpen();
    }catch(e){notify(e.message,'error');}
  }
  window.editarVenta=openEdit; window.openSaleForEdit=openEdit;

  async function saveSale(){
    const c=$('#vf-cliente');
    const payload={numero_factura:($('#vf-num')?.value||'').trim(),cliente_id:c?.value||null,cliente_nombre:c?.options[c.selectedIndex]?.text||'',cliente_email:($('#vf-email')?.value||'').trim(),cliente_telefono:($('#vf-tel')?.value||'').trim(),fecha:$('#vf-fecha')?.value||'',forma_pago:$('#vf-pago')?.value||'Contado',estado:$('#vf-estado')?.value||'Pendiente',notas:$('#vf-notas')?.value||'',ciclo:($('#vf-ciclo')?.value||'').trim(),fecha_inicio_ciclo:$('#vf-ciclo-inicio')?.value||'',fecha_fin_ciclo:$('#vf-ciclo-fin')?.value||''};
    try{
      if(editId){
        await request(`${V2}/sales/${editId}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,items})});
        notify('Venta actualizada correctamente');
      }else{
        if(!items.length) return notify('Agrega al menos un producto','error');
        const total=calc().total;
        const initial=payload.forma_pago==='Abono'?Number($('#vf-abono-inicial')?.value||0):0;
        if(payload.forma_pago==='Abono' && (!Number.isFinite(initial)||initial<=0||initial>total)) return notify(`El abono inicial debe estar entre $1 y ${money(total)}`,'error');
        await request(`${V2}/sales`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,items,initial_payment:initial})});
        notify('Venta registrada correctamente');
      }
      modalClose(); await loadVentas(); window.loadDashboard?.(); window.loadCiclos?.();
    }catch(e){notify(e.message,'error');}
  }
  window.saveVenta=saveSale;

  async function setStatus(id,status){
    try{await request(`${V2}/sales/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({estado:status})});notify(status==='Pagado'?'Venta marcada como pagada':'Venta cancelada');await loadVentas();window.loadDashboard?.();window.loadCiclos?.();}
    catch(e){notify(e.message,'error');}
  }
  window.marcarPagada=(id)=>setStatus(id,'Pagado'); window.markSalePaid=window.marcarPagada; window.cambiarEstado=setStatus;

  async function addPayment(id){
    const v=prompt('Valor del abono:'); if(v===null) return; const amount=Number(String(v).replace(',','.')); if(!Number.isFinite(amount)||amount<=0) return notify('Monto inválido','error');
    try{await request(`${V2}/sales/${id}/payments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({monto:amount,forma_pago:'Abono'})});notify('Abono registrado');await loadVentas();window.loadDashboard?.();window.loadCiclos?.();}
    catch(e){notify(e.message,'error');}
  }
  window.registrarAbono=addPayment; window.addSalePayment=addPayment;

  async function removeSale(id,invoice){if(!confirm(`¿Eliminar la venta ${invoice}?`))return;try{await request(`${V2}/sales/${id}`,{method:'DELETE'});notify('Venta eliminada');await loadVentas();window.loadDashboard?.();window.loadCiclos?.();}catch(e){notify(e.message,'error');}}
  window.eliminarVenta=removeSale; window.deleteSaleFromUi=removeSale;

  function bindTopbar(){const b=$('#topbar-action');if(!b)return;b.type='button';b.onclick=(e)=>{e.preventDefault();e.stopPropagation();if(window.currentPage==='ventas')openNew();else if(window.currentPage==='inventario')window.openModalProducto?.();else if(window.currentPage==='clientes')window.openModalCliente?.();else if(window.currentPage==='devoluciones')window.openModalDevolucion?.();};}

  function bindNavigation(){
    const original=window.goto;
    window.goto=(page)=>{
      if(typeof original==='function') original(page);
      if(page==='ventas') setTimeout(()=>{resetFilter();bindFilters();bindModal();bindTopbar();removePageNewSaleButtons();loadVentas();},10);
    };
  }

  function start(){
    if(booted) return; booted=true;
    removePageNewSaleButtons(); bindFilters(); bindModal(); bindTopbar(); bindNavigation();
    if($('#page-ventas')?.classList.contains('active')){resetFilter();loadVentas();}
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();
