(() => {
  'use strict';

  const API = '/api';
  const V2 = '/api/v2';
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const esc = (v) => String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
  const money = (v) => new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(Number(v || 0));
  const dateOnly = (v) => v ? String(v).slice(0, 10).split('-').reverse().join('/') : '—';
  const notify = (m, t = 'success') => {
    if (typeof window.toast === 'function') window.toast(m, t);
    else if (t === 'error') console.error(m); else console.log(m);
  };

  let sales = [];
  let filter = '';
  let editingId = null;
  let items = [];
  let installed = false;

  async function api(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
  }

  function isAdmin() {
    return window.lumeonIsAdmin === true || String(window.currentUser?.role || '').toLowerCase() === 'admin';
  }

  async function syncAuth() {
    try {
      const body = await api(`${V2}/auth/me`);
      if (body.authenticated) {
        window.currentUser = {
          user_id: body.user_id,
          username: body.username || body.user?.username || String(body.user_id || ''),
          role: String(body.role || body.user?.role || '').toLowerCase(),
        };
        window.lumeonIsAdmin = window.currentUser.role === 'admin';
      }
    } catch (error) {
      console.warn('Lumeon sales auth:', error.message);
    }
    $$('.admin-only-nav').forEach((el) => { el.style.display = isAdmin() ? '' : 'none'; });
  }

  function closeModalDirect() {
    const modal = $('#modal-venta');
    if (modal) modal.classList.remove('open');
    editingId = null;
    items = [];
    window.editVentaId = null;
    window.ventaItems = [];
  }

  function openModalDirect() {
    const modal = $('#modal-venta');
    if (!modal) { notify('No se encontró el formulario de venta', 'error'); return false; }
    modal.classList.add('open');
    return true;
  }

  function removeDuplicateNewSaleButtons() {
    $$('#page-ventas .page-header button').forEach((button) => {
      if ((button.textContent || '').toLowerCase().includes('nueva venta')) button.remove();
    });
    $('#sales-new-sale-button')?.remove();
  }

  function configureTopbar() {
    const button = $('#topbar-action');
    if (!button) return;
    button.style.display = 'flex';
    button.textContent = '+ Nueva Venta';
    button.type = 'button';
    button.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      window.openModalVenta();
    };
  }

  function configureModal() {
    const modal = $('#modal-venta');
    if (!modal) return;

    const save = $('#btn-save-venta');
    if (save) {
      save.type = 'button';
      save.onclick = (event) => { event.preventDefault(); event.stopPropagation(); window.saveVenta(); };
    }

    modal.querySelectorAll('button').forEach((button) => {
      if (button === save) return;
      const text = (button.textContent || '').trim().toLowerCase();
      const klass = String(button.className || '').toLowerCase();
      if (text === '×' || text === 'cancelar' || klass.includes('modal-close')) {
        button.type = 'button';
        button.onclick = (event) => { event.preventDefault(); event.stopPropagation(); closeModalDirect(); };
      }
    });

    const productBox = $('#vf-ref')?.parentElement;
    const add = productBox?.querySelector('button');
    if (add) {
      add.type = 'button';
      add.onclick = (event) => { event.preventDefault(); event.stopPropagation(); window.addSaleItem(); };
    }

    const ref = $('#vf-ref');
    if (ref) ref.onkeydown = (event) => {
      if (event.key === 'Enter') { event.preventDefault(); window.addSaleItem(); }
    };

    const payment = $('#vf-pago');
    if (payment) payment.onchange = () => {
      const group = $('#abono-inicial-group');
      if (group) group.style.display = payment.value === 'Abono' ? '' : 'none';
    };
  }

  async function loadSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;
    try {
      const q = ($('#venta-search')?.value || '').trim();
      const body = await api(`${V2}/sales?q=${encodeURIComponent(q)}`);
      sales = body.results || [];
      renderSales();
    } catch (error) {
      sales = [];
      tbody.innerHTML = `<tr><td colspan="9" class="empty"><div class="empty-title">Error al cargar ventas</div><div class="empty-text">${esc(error.message)}</div></td></tr>`;
    }
  }

  function renderSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;
    const q = ($('#venta-search')?.value || '').trim().toLowerCase();
    const f = String(filter || '').toLowerCase();
    const data = sales.filter((sale) => {
      const text = [sale.numero_factura, sale.cliente_nombre, sale.cliente_email, sale.cliente_telefono].filter(Boolean).join(' ').toLowerCase();
      const state = String(sale.estado || 'Pendiente').toLowerCase();
      const payment = String(sale.estado_pago || '').toLowerCase();
      const stateOk = !f || (f === 'abonado' ? payment === 'abonado' : state === f);
      return stateOk && (!q || text.includes(q));
    });

    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div><div class="empty-text">No hay ventas para este filtro.</div></td></tr>';
      return;
    }

    tbody.innerHTML = data.map((sale) => {
      const admin = isAdmin();
      const state = String(sale.estado || 'Pendiente');
      const shown = String(sale.estado_pago || state);
      const balance = Number(sale.saldo_pendiente || 0);
      const actions = admin ? `
        <button type="button" class="btn btn-ghost btn-sm btn-icon" data-a="edit" data-id="${Number(sale.id)}" title="Editar">✎</button>
        ${state.toLowerCase() !== 'pagado' && state.toLowerCase() !== 'cancelado' ? `<button type="button" class="btn btn-success btn-sm" data-a="paid" data-id="${Number(sale.id)}">Pagada</button>` : ''}
        ${balance > 0 && state.toLowerCase() !== 'cancelado' ? `<button type="button" class="btn btn-gold btn-sm" data-a="payment" data-id="${Number(sale.id)}">Abono</button>` : ''}
        ${state.toLowerCase() === 'pendiente' ? `<button type="button" class="btn btn-ghost btn-sm btn-icon" data-a="cancel" data-id="${Number(sale.id)}" title="Cancelar">✕</button>` : ''}
        <button type="button" class="btn btn-danger btn-sm btn-icon" data-a="delete" data-id="${Number(sale.id)}" data-invoice="${esc(sale.numero_factura || '')}" title="Eliminar">🗑</button>
      ` : '—';
      const badge = typeof window.badgeEstado === 'function' ? window.badgeEstado(shown) : `<span class="badge badge-amber">${esc(shown)}</span>`;
      return `<tr>
        <td class="td-mono">${esc(sale.numero_factura || '—')}</td>
        <td style="font-weight:500">${esc(sale.cliente_nombre || '—')}</td>
        <td>${esc(sale.ciclo || '—')}</td>
        <td style="color:var(--ink3)">${dateOnly(sale.fecha)}</td>
        <td>${esc(sale.forma_pago || 'Contado')}</td>
        <td class="td-mono" style="font-weight:600">${money(sale.total)}</td>
        <td class="td-mono" style="color:var(--sage)">${money(sale.ganancia)}</td>
        <td>${badge}</td>
        <td class="sales-actions" style="white-space:nowrap;display:flex;gap:4px;align-items:center">${actions}</td>
      </tr>`;
    }).join('');

    tbody.querySelectorAll('[data-a]').forEach((button) => {
      const id = Number(button.dataset.id);
      const action = button.dataset.a;
      if (action === 'edit') button.onclick = () => window.openSaleForEdit(id);
      if (action === 'paid') button.onclick = () => window.markSalePaid(id);
      if (action === 'payment') button.onclick = () => window.addSalePayment(id);
      if (action === 'cancel') button.onclick = () => window.cancelSale(id);
      if (action === 'delete') button.onclick = () => window.deleteSaleFromUi(id, button.dataset.invoice || '');
    });
  }

  function bindSalesFilters() {
    const search = $('#venta-search');
    if (search) search.oninput = renderSales;
    const tabs = $$('#ventas-tabs .tab');
    const states = ['', 'Pendiente', 'Abonado', 'Pagado', 'Cancelado'];
    tabs.forEach((tab, index) => {
      tab.type = 'button';
      tab.onclick = (event) => {
        event.preventDefault(); event.stopPropagation();
        filter = states[index] || '';
        tabs.forEach((x) => x.classList.remove('active'));
        tab.classList.add('active');
        renderSales();
      };
    });
  }

  async function loadClients(selectedId = null) {
    const body = await api(`${V2}/clientes?q=&limit=200`);
    const select = $('#vf-cliente');
    if (!select) return;
    select.innerHTML = '<option value="">-- Sin cliente --</option>' + (body.results || []).map((client) => `<option value="${Number(client.id)}">${esc(client.nombre)}</option>`).join('');
    if (selectedId != null) select.value = String(selectedId);
  }

  function renderSaleItems() {
    const tbody = $('#vf-items-body');
    if (!tbody) return;
    let total = 0; let gain = 0;
    tbody.innerHTML = items.map((item, index) => {
      const qty = Number(item.cantidad || 0); const buy = Number(item.precio_compra || 0); const sell = Number(item.precio_venta || 0); const line = qty * sell;
      total += line; gain += qty * (sell - buy);
      return `<tr><td class="td-mono">${esc(item.referencia)}</td><td>${esc(item.nombre)}</td><td>${qty}</td><td>${money(buy)}</td><td>${money(sell)}</td><td>${money(line)}</td><td><button type="button" class="btn btn-danger btn-sm btn-icon" onclick="window.removeSaleItem(${index});return false;">✕</button></td></tr>`;
    }).join('');
    if ($('#vs-sub')) $('#vs-sub').textContent = money(total);
    if ($('#vs-total')) $('#vs-total').textContent = money(total);
    if ($('#vs-gan')) $('#vs-gan').textContent = money(gain);
    window.ventaItems = items;
  }

  async function addSaleItem() {
    const ref = ($('#vf-ref')?.value || '').trim();
    const qty = Number($('#vf-cant')?.value || 1);
    if (!ref) return notify('Ingresa la referencia', 'error');
    if (!Number.isInteger(qty) || qty <= 0) return notify('Cantidad inválida', 'error');
    try {
      const product = await api(`${API}/productos/buscar/${encodeURIComponent(ref)}`);
      if (!product?.id) throw new Error('Producto no encontrado');
      const existing = items.find((item) => item.referencia === product.referencia);
      if (existing) existing.cantidad += qty;
      else items.push({ producto_id: Number(product.id), referencia: product.referencia, nombre: product.nombre, cantidad: qty, precio_compra: Number(product.precio_compra || 0), precio_venta: Number(product.precio_venta || 0) });
      renderSaleItems();
      if ($('#vf-ref')) $('#vf-ref').value = '';
      if ($('#vf-cant')) $('#vf-cant').value = '1';
    } catch (error) { notify(error.message, 'error'); }
  }

  function removeSaleItem(index) { items.splice(index, 1); renderSaleItems(); }

  function openNewSale() {
    editingId = null; items = []; window.editVentaId = null; window.ventaItems = [];
    if ($('#mv-title')) $('#mv-title').textContent = 'Nueva Venta';
    if ($('#btn-save-venta')) $('#btn-save-venta').textContent = 'Registrar Venta';
    if ($('#vf-num')) $('#vf-num').value = `FAC-${Date.now()}`;
    if ($('#vf-fecha')) $('#vf-fecha').value = new Date().toISOString().slice(0, 10);
    if ($('#vf-pago')) $('#vf-pago').value = 'Contado';
    if ($('#vf-estado')) $('#vf-estado').value = 'Pendiente';
    if ($('#abono-inicial-group')) $('#abono-inicial-group').style.display = 'none';
    Promise.resolve(loadClients(null)).then(() => { renderSaleItems(); openModalDirect(); }).catch((e) => notify(e.message, 'error'));
  }

  async function openSaleForEdit(id) {
    try {
      const body = await api(`${V2}/sales/${id}`);
      const sale = body.venta || {};
      editingId = Number(id);
      if ($('#mv-title')) $('#mv-title').textContent = 'Editar Venta';
      if ($('#btn-save-venta')) $('#btn-save-venta').textContent = 'Guardar cambios';
      if ($('#vf-num')) $('#vf-num').value = sale.numero_factura || '';
      if ($('#vf-fecha')) $('#vf-fecha').value = sale.fecha ? String(sale.fecha).slice(0,10) : '';
      if ($('#vf-ciclo')) $('#vf-ciclo').value = sale.ciclo || '';
      if ($('#vf-ciclo-inicio')) $('#vf-ciclo-inicio').value = sale.fecha_inicio_ciclo || '';
      if ($('#vf-ciclo-fin')) $('#vf-ciclo-fin').value = sale.fecha_fin_ciclo || '';
      if ($('#vf-pago')) $('#vf-pago').value = sale.forma_pago || 'Contado';
      if ($('#vf-estado')) $('#vf-estado').value = sale.estado || 'Pendiente';
      if ($('#vf-email')) $('#vf-email').value = sale.cliente_email || '';
      if ($('#vf-tel')) $('#vf-tel').value = sale.cliente_telefono || '';
      if ($('#vf-notas')) $('#vf-notas').value = sale.notas || '';
      await loadClients(sale.cliente_id);
      items = Array.isArray(body.items) ? body.items.map((x) => ({ ...x })) : [];
      renderSaleItems();
      // Editing metadata is independent from adding products.
      const addRow = $('#vf-ref')?.parentElement; if (addRow) addRow.style.display = 'none';
      const table = $('#vf-items-body')?.closest('.items-table-wrap'); if (table) table.style.display = 'none';
      openModalDirect();
    } catch (error) { notify(error.message, 'error'); }
  }

  async function saveVenta() {
    const client = $('#vf-cliente');
    const payload = {
      numero_factura: ($('#vf-num')?.value || '').trim(),
      cliente_id: client?.value || null,
      cliente_nombre: client?.selectedOptions?.[0]?.text || '',
      cliente_email: ($('#vf-email')?.value || '').trim(),
      cliente_telefono: ($('#vf-tel')?.value || '').trim(),
      fecha: $('#vf-fecha')?.value || null,
      forma_pago: $('#vf-pago')?.value || 'Contado',
      estado: $('#vf-estado')?.value || 'Pendiente',
      notas: $('#vf-notas')?.value || '',
      ciclo: ($('#vf-ciclo')?.value || '').trim(),
      fecha_inicio_ciclo: $('#vf-ciclo-inicio')?.value || null,
      fecha_fin_ciclo: $('#vf-ciclo-fin')?.value || null,
    };
    try {
      if (editingId != null) {
        await api(`${V2}/sales/${editingId}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ ...payload, items }) });
        notify('Venta actualizada correctamente');
      } else {
        if (!items.length) return notify('Agrega al menos un producto', 'error');
        const total = items.reduce((sum, item) => sum + Number(item.cantidad || 0) * Number(item.precio_venta || 0), 0);
        const initial = payload.forma_pago === 'Abono' ? Number($('#vf-abono-inicial')?.value || 0) : 0;
        if (payload.forma_pago === 'Abono' && (!Number.isFinite(initial) || initial <= 0 || initial > total)) return notify(`Abono inicial inválido. Debe estar entre $1 y ${money(total)}`, 'error');
        await api(`${V2}/sales`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ ...payload, items, initial_payment: initial }) });
        notify(payload.forma_pago === 'Abono' ? 'Venta registrada con abono inicial' : 'Venta registrada correctamente');
      }
      closeModalDirect();
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      return loadCycles();
    } catch (error) { notify(error.message, 'error'); }
  }

  async function markSalePaid(id) { return statusSale(id, 'Pagado'); }
  async function cancelSale(id) { return statusSale(id, 'Cancelado'); }

  async function statusSale(id, state) {
    try {
      await api(`${V2}/sales/${id}/status`, { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ estado: state }) });
      notify(state === 'Pagado' ? 'Venta marcada como pagada' : 'Venta cancelada');
      await loadSales();
      window.loadDashboard?.();
      await loadCycles();
    } catch (error) { notify(error.message, 'error'); }
  }

  async function deleteSaleFromUi(id, invoice) {
    if (!confirm(`¿Eliminar la venta ${invoice}?`)) return;
    try {
      await api(`${V2}/sales/${id}`, { method: 'DELETE' });
      notify('Venta eliminada');
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      await loadCycles();
    } catch (error) { notify(error.message, 'error'); }
  }

  async function addSalePayment(id) {
    const raw = prompt('Valor del abono / cuota:');
    if (raw === null) return;
    const amount = Number(String(raw).replace(',', '.'));
    if (!Number.isFinite(amount) || amount <= 0) return notify('Monto inválido', 'error');
    try {
      const body = await api(`${V2}/sales/${id}/payments`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ monto: amount, forma_pago: 'Abono' }) });
      const sale = body.venta || {};
      notify(Number(sale.saldo_pendiente || 0) > 0 ? `Abono registrado. Saldo: ${money(sale.saldo_pendiente)}` : 'Abono registrado. Venta pagada.');
      await loadSales();
      await loadCycles();
    } catch (error) { notify(error.message, 'error'); }
  }

  async function loadCycles() {
    const box = $('#ciclos-container');
    if (!box) return;
    try {
      const raw = await api(`${API}/ciclos`);
      const cycles = Array.isArray(raw) ? raw : (raw.results || []);
      if (!cycles.length) { box.innerHTML = '<div class="empty"><div class="empty-title">Sin ciclos</div><div class="empty-text">No hay ciclos registrados.</div></div>'; return; }
      const summaries = await Promise.all(cycles.map(async (cycle) => {
        try { return await api(`${API}/ciclos/${encodeURIComponent(cycle)}/resumen`); }
        catch { return {ciclo: cycle, total: 0, ganancia: 0, num_ventas: 0}; }
      }));
      box.innerHTML = summaries.map((s) => `<div class="card" style="margin-bottom:12px"><div class="card-header"><div><div class="card-title">Ciclo ${esc(s.ciclo)}</div><div class="card-subtitle">${Number(s.num_ventas || 0)} ventas</div></div><strong>${money(s.total)}</strong></div><div style="font-size:11px;color:var(--ink3)">Ganancia ${money(s.ganancia)}</div></div>`).join('');
    } catch (error) { box.innerHTML = `<div class="empty"><div class="empty-title">Error al cargar ciclos</div><div class="empty-text">${esc(error.message)}</div></div>`; }
  }

  async function loadLogs() {
    const box = $('#admin-logs-list');
    if (!box) return;
    try {
      const body = await api(`${V2}/admin/logs?limit=200`);
      const logs = body.results || [];
      box.innerHTML = logs.length ? logs.map((log) => `<div class="admin-log-card"><div class="admin-log-head"><strong>${esc(log.action)}</strong><span>${esc(log.username || 'sistema')}</span><span>${esc(log.created_at || '')}</span></div><div class="admin-log-entity">${esc(log.entity_type || 'sistema')} #${esc(log.entity_id || '—')}</div><div class="admin-log-meta">${esc(log.metadata || '')}</div></div>`).join('') : '<div class="empty"><div class="empty-title">Sin registros</div></div>';
    } catch (error) { box.innerHTML = `<div class="empty"><div class="empty-title">Error al cargar registros</div><div class="empty-text">${esc(error.message)}</div></div>`; }
  }

  function bindNavigation() {
    const map = {dashboard:'dashboard',inventario:'inventario',ventas:'ventas',clientes:'clientes',ciclos:'ciclos',devoluciones:'devoluciones',registros:'admin-logs'};
    $$('#sidebar .nav-item').forEach((item) => {
      item.onclick = (event) => {
        event.preventDefault(); event.stopPropagation();
        const key = item.textContent.trim().toLowerCase();
        if (map[key]) navigate(map[key]);
      };
    });
  }

  function navigate(page) {
    const target = document.getElementById(`page-${page}`);
    if (!target) return;
    $$('.page').forEach((p) => p.classList.remove('active'));
    target.classList.add('active');
    window.currentPage = page;
    const titles = {dashboard:'Dashboard',inventario:'Inventario',ventas:'Ventas',clientes:'Clientes',ciclos:'Ciclos',devoluciones:'Devoluciones','admin-logs':'Registros'};
    if ($('#topbar-title')) $('#topbar-title').textContent = titles[page] || 'Lumeon';
    if (page === 'ventas') loadSales();
    if (page === 'ciclos') loadCycles();
    if (page === 'admin-logs') loadLogs();
    if (page === 'dashboard') window.loadDashboard?.();
    if (page === 'inventario') window.loadInventario?.();
    if (page === 'clientes') window.loadClientes?.();
    if (page === 'devoluciones') window.loadDevoluciones?.();
    window.closeMobileMenu?.();
  }

  function bindSales() {
    $('#venta-search')?.addEventListener('input', renderSales);
    const states = ['', 'Pendiente', 'Abonado', 'Pagado', 'Cancelado'];
    $$('#ventas-tabs .tab').forEach((tab, index) => {
      tab.type = 'button';
      tab.onclick = (event) => { event.preventDefault(); event.stopPropagation(); filter = states[index] || ''; $$('#ventas-tabs .tab').forEach((x) => x.classList.remove('active')); tab.classList.add('active'); renderSales(); };
    });
  }

  function expose() {
    window.openModalVenta = openNewSale;
    window.saveVenta = saveVenta;
    window.openSaleForEdit = openSaleForEdit;
    window.editarVenta = openSaleForEdit;
    window.markSalePaid = markSalePaid;
    window.marcarPagada = markSalePaid;
    window.cancelSale = cancelSale;
    window.cambiarEstado = statusSale;
    window.deleteSaleFromUi = deleteSaleFromUi;
    window.eliminarVenta = deleteSaleFromUi;
    window.addSalePayment = addSalePayment;
    window.registrarAbono = addSalePayment;
    window.addSaleItem = addSaleItem;
    window.removeSaleItem = removeSaleItem;
    window.loadVentas = loadSales;
  }

  function start() {
    if (installed) return;
    installed = true;
    removeDuplicateNewSaleButtons();
    expose();
    configureTopbar();
    configureModal();
    bindNavigation();
    bindSales();
    syncAuth();
    setTimeout(removeDuplicateNewSaleButtons, 50);
    setTimeout(removeDuplicateNewSaleButtons, 500);
    setTimeout(removeDuplicateNewSaleButtons, 1500);
    const active = document.querySelector('.page.active');
    if (active?.id === 'page-ventas') loadSales();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
