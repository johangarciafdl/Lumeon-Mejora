(() => {
  'use strict';

  const API = '/api/v2';
  let salesCache = [];
  let salesFilter = '';
  let editingSaleId = null;

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  const safe = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const money = (value) => new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(Number(value || 0));

  const dateOnly = (value) => {
    if (!value) return '—';
    return String(value).slice(0, 10).split('-').reverse().join('/');
  };

  const toast = (message, type = 'success') => {
    if (typeof window.toast === 'function') return window.toast(message, type);
    console[type === 'error' ? 'error' : 'log'](message);
  };

  async function request(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      const error = new Error(body.error || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function isAdmin() {
    return String(window.currentUser?.role || '').toLowerCase() === 'admin';
  }

  function currentPageTitle(page) {
    return {
      dashboard: 'Dashboard',
      inventario: 'Inventario',
      ventas: 'Ventas',
      clientes: 'Clientes',
      ciclos: 'Ciclos',
      devoluciones: 'Devoluciones',
      'admin-logs': 'Registros',
    }[page] || 'Lumeon';
  }

  function closeMobileMenu() {
    if (typeof window.closeMobileMenu === 'function') {
      window.closeMobileMenu();
    } else {
      $('#sidebar')?.classList.remove('mobile-open');
      $('#mobile-menu-backdrop')?.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  function markNavigation(page) {
    $$('#sidebar .nav-item').forEach(item => item.classList.remove('active'));
    const target = `page-${page}`;
    $$('#sidebar .nav-item').forEach(item => {
      const onclick = item.getAttribute('onclick') || '';
      if (onclick.includes(`'${page}'`) || onclick.includes(`\"${page}\"`)) {
        item.classList.add('active');
      }
    });
    if (page === 'admin-logs') {
      $('#nav-registros')?.classList.add('active');
    }
  }

  function navigate(page) {
    const pageEl = document.getElementById(`page-${page}`);
    if (!pageEl) return;

    $$('.page').forEach(el => el.classList.remove('active'));
    pageEl.classList.add('active');
    markNavigation(page);

    const title = $('#topbar-title');
    if (title) title.textContent = currentPageTitle(page);

    const topbarAction = $('#topbar-action');
    const labels = {
      inventario: 'Nuevo Producto',
      ventas: 'Nueva Venta',
      clientes: 'Nuevo Cliente',
      devoluciones: 'Nueva Devolución',
    };
    if (topbarAction) {
      if (labels[page]) {
        topbarAction.textContent = `+ ${labels[page]}`;
        topbarAction.style.display = 'flex';
      } else {
        topbarAction.style.display = 'none';
      }
    }

    const content = $('#content');
    if (content) content.scrollTop = 0;
    window.currentPage = page;
    closeMobileMenu();

    try {
      if (page === 'dashboard') window.loadDashboard?.();
      else if (page === 'inventario') window.loadInventario?.();
      else if (page === 'ventas') loadSales();
      else if (page === 'clientes') window.loadClientes?.();
      else if (page === 'ciclos') window.loadCiclos?.();
      else if (page === 'devoluciones') window.loadDevoluciones?.();
      else if (page === 'admin-logs') window.loadAdminLogs?.();
    } catch (error) {
      console.error('Lumeon navigation error', error);
      toast(error.message, 'error');
    }
  }

  function bindNavigation() {
    const mapping = [
      ['dashboard', 'Dashboard'],
      ['inventario', 'Inventario'],
      ['ventas', 'Ventas'],
      ['clientes', 'Clientes'],
      ['ciclos', 'Ciclos'],
      ['devoluciones', 'Devoluciones'],
      ['admin-logs', 'Registros'],
    ];

    $$('#sidebar .nav-item').forEach(item => {
      item.onclick = (event) => {
        event.preventDefault();
        const text = item.textContent.trim().toLowerCase();
        const found = mapping.find(([, label]) => text === label.toLowerCase());
        if (found) navigate(found[0]);
      };
    });

    window.goto = navigate;
    window.navigateLumeon = navigate;
  }

  function showAdminNav() {
    const admin = isAdmin();
    $$('.admin-only-nav').forEach(el => {
      el.style.display = admin ? '' : 'none';
    });
  }

  function patchTopbar() {
    const action = $('#topbar-action');
    if (!action) return;
    action.onclick = () => {
      const page = window.currentPage;
      if (page === 'ventas') openSaleEditor();
      else if (page === 'inventario') window.openModalProducto?.();
      else if (page === 'clientes') window.openModalCliente?.();
      else if (page === 'devoluciones') window.openModalDevolucion?.();
    };
  }

  function ensureSaleModalEnhancements() {
    const modalBody = document.querySelector('#modal-venta .modal-body');
    if (!modalBody) return;

    let payments = $('#sales-management-payments');
    if (!payments) {
      payments = document.createElement('div');
      payments.id = 'sales-management-payments';
      payments.style.cssText = 'display:none;margin-top:18px;padding-top:16px;border-top:1px solid var(--border)';
      modalBody.appendChild(payments);
    }

    let initialGroup = $('#vf-abono-inicial-group');
    if (!initialGroup) {
      const payment = $('#vf-pago');
      if (payment?.parentElement) {
        initialGroup = document.createElement('div');
        initialGroup.id = 'vf-abono-inicial-group';
        initialGroup.className = 'form-group';
        initialGroup.style.display = 'none';
        initialGroup.innerHTML = '<label>Abono inicial</label><input id="vf-abono-inicial" type="number" min="0" step="1" placeholder="$0">';
        payment.parentElement.insertAdjacentElement('afterend', initialGroup);
      }
    }

    const payment = $('#vf-pago');
    if (payment) {
      payment.onchange = () => {
        const box = $('#vf-abono-inicial-group');
        if (box) box.style.display = payment.value === 'Abono' ? '' : 'none';
      };
    }
  }

  function setProductEditorVisible(visible) {
    const ref = $('#vf-ref');
    const adder = ref?.parentElement;
    const itemWrap = document.querySelector('#modal-venta .items-table-wrap');
    const summary = $('#venta-summary');
    if (adder) adder.style.display = visible ? '' : 'none';
    if (itemWrap) itemWrap.style.display = visible ? '' : 'none';
    if (summary) summary.style.display = visible ? '' : 'none';
  }

  function setEditorDefaults() {
    $('#mv-title') && ($('#mv-title').textContent = 'Nueva Venta');
    $('#btn-save-venta') && ($('#btn-save-venta').textContent = 'Registrar Venta');
    editingSaleId = null;
    window.editVentaId = null;
    window.ventaItems = [];
    setProductEditorVisible(true);
    const payments = $('#sales-management-payments');
    if (payments) payments.style.display = 'none';
    if ($('#vf-abono-inicial')) $('#vf-abono-inicial').value = '';
    if ($('#vf-pago')) $('#vf-pago').value = 'Contado';
    if ($('#vf-estado')) $('#vf-estado').value = 'Pendiente';
  }

  function calculateItems(items) {
    return (items || []).reduce((acc, item) => {
      const qty = Number(item.cantidad || 0);
      const price = Number(item.precio_venta || 0);
      const purchase = Number(item.precio_compra || 0);
      acc.total += qty * price;
      acc.ganancia += qty * (price - purchase);
      return acc;
    }, { total: 0, ganancia: 0 });
  }

  function renderSaleItems(items) {
    window.ventaItems = (items || []).map(item => ({ ...item }));
    const body = $('#vf-items-body');
    if (!body) return;
    let total = 0;
    let gain = 0;

    body.innerHTML = window.ventaItems.map((item, index) => {
      const qty = Number(item.cantidad || 0);
      const sale = Number(item.precio_venta || 0);
      const purchase = Number(item.precio_compra || 0);
      const line = qty * sale;
      total += line;
      gain += qty * (sale - purchase);
      return `<tr>
        <td class="td-mono">${safe(item.referencia)}</td>
        <td>${safe(item.nombre)}</td>
        <td>${qty}</td>
        <td class="td-mono">${money(purchase)}</td>
        <td class="td-mono">${money(sale)}</td>
        <td class="item-total">${money(line)}</td>
        <td><button type="button" class="btn btn-danger btn-sm btn-icon" data-remove-sale-item="${index}">✕</button></td>
      </tr>`;
    }).join('');

    if ($('#vs-sub')) $('#vs-sub').textContent = money(total);
    if ($('#vs-total')) $('#vs-total').textContent = money(total);
    if ($('#vs-gan')) $('#vs-gan').textContent = money(gain);

    body.querySelectorAll('[data-remove-sale-item]').forEach(btn => {
      btn.addEventListener('click', () => {
        const index = Number(btn.dataset.removeSaleItem);
        window.ventaItems.splice(index, 1);
        renderSaleItems(window.ventaItems);
      });
    });
  }

  async function loadClientsIntoSale(selectedId) {
    const response = await request('/api/clientes?q=&limit=200');
    const clients = response.results || [];
    const select = $('#vf-cliente');
    if (!select) return;
    select.innerHTML = '<option value="">-- Sin cliente --</option>' + clients.map(c => `<option value="${Number(c.id)}">${safe(c.nombre)}</option>`).join('');
    if (selectedId != null) select.value = String(selectedId);
  }

  function populateSaleForm(sale) {
    $('#vf-num') && ($('#vf-num').value = sale.numero_factura || '');
    $('#vf-fecha') && ($('#vf-fecha').value = sale.fecha ? String(sale.fecha).slice(0, 10) : '');
    $('#vf-ciclo') && ($('#vf-ciclo').value = sale.ciclo || '');
    $('#vf-ciclo-inicio') && ($('#vf-ciclo-inicio').value = sale.fecha_inicio_ciclo || '');
    $('#vf-ciclo-fin') && ($('#vf-ciclo-fin').value = sale.fecha_fin_ciclo || '');
    $('#vf-pago') && ($('#vf-pago').value = sale.forma_pago || 'Contado');
    $('#vf-email') && ($('#vf-email').value = sale.cliente_email || '');
    $('#vf-tel') && ($('#vf-tel').value = sale.cliente_telefono || '');
    $('#vf-notas') && ($('#vf-notas').value = sale.notas || '');
    $('#vf-estado') && ($('#vf-estado').value = sale.estado || 'Pendiente');
  }

  function paymentHistoryHtml(detail) {
    const abonos = detail.abonos || [];
    const rows = abonos.map((item, index) => `<div class="sales-payment-row">
      <div><strong>Cuota ${index + 1}</strong><div class="sales-payment-meta">${safe(item.forma_pago || 'Abono')} · ${dateOnly(item.fecha)}</div></div>
      <strong>${money(item.monto)}</strong>
    </div>`).join('');
    return `<div class="sales-payment-title">Historial de cuotas</div>
      ${rows || '<div class="sales-payment-empty">No hay abonos registrados.</div>'}
      <div class="sales-payment-totals"><span>Total abonado</span><strong>${money(detail.venta.total_abonado)}</strong></div>
      <div class="sales-payment-totals"><span>Saldo pendiente</span><strong>${money(detail.venta.saldo_pendiente)}</strong></div>`;
  }

  async function openSaleEditor(id = null) {
    ensureSaleModalEnhancements();
    const modal = $('#modal-venta');
    if (!modal) return;

    if (id == null) {
      setEditorDefaults();
      $('#vf-fecha') && ($('#vf-fecha').value = new Date().toISOString().slice(0, 10));
      await loadClientsIntoSale(null);
      if (typeof window.renderVentaItems === 'function') window.renderVentaItems();
      else renderSaleItems([]);
      if ($('#vf-num')) $('#vf-num').value = `FAC-${Date.now()}`;
      if (typeof window.openModal === 'function') window.openModal('modal-venta');
      return;
    }

    try {
      const detail = await request(`${API}/sales/${id}`);
      editingSaleId = id;
      window.editVentaId = id;
      populateSaleForm(detail.venta);
      await loadClientsIntoSale(detail.venta.cliente_id);
      renderSaleItems(detail.items);
      setProductEditorVisible(true);
      $('#mv-title') && ($('#mv-title').textContent = 'Editar Venta');
      $('#btn-save-venta') && ($('#btn-save-venta').textContent = 'Guardar cambios');

      const payments = $('#sales-management-payments');
      if (payments) {
        payments.style.display = '';
        payments.innerHTML = paymentHistoryHtml(detail);
      }

      if (typeof window.openModal === 'function') window.openModal('modal-venta');
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  async function addSaleItemFromUi() {
    const ref = $('#vf-ref')?.value.trim();
    const qty = Number($('#vf-cant')?.value || 1);
    if (!ref) return toast('Ingresa una referencia', 'error');
    if (!Number.isInteger(qty) || qty <= 0) return toast('Cantidad inválida', 'error');

    try {
      const response = await request(`/api/productos/buscar/${encodeURIComponent(ref)}`);
      const product = response.result || response;
      if (!product?.id) throw new Error('Referencia no encontrada');
      if (Number(product.stock || 0) < qty && !editingSaleId) {
        throw new Error(`Stock insuficiente. Disponible: ${product.stock}`);
      }
      const existingIndex = window.ventaItems.findIndex(i => i.referencia === ref);
      if (existingIndex >= 0) {
        window.ventaItems[existingIndex].cantidad += qty;
      } else {
        window.ventaItems.push({
          producto_id: Number(product.id),
          referencia: product.referencia,
          nombre: product.nombre,
          cantidad: qty,
          precio_compra: Number(product.precio_compra || 0),
          precio_venta: Number(product.precio_venta || 0),
        });
      }
      $('#vf-ref').value = '';
      $('#vf-cant').value = '1';
      renderSaleItems(window.ventaItems);
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  async function saveSale() {
    if (editingSaleId != null) {
      const select = $('#vf-cliente');
      const payload = {
        numero_factura: $('#vf-num')?.value.trim(),
        cliente_id: select?.value || null,
        cliente_nombre: select?.selectedOptions?.[0]?.text || '',
        cliente_email: $('#vf-email')?.value.trim() || '',
        cliente_telefono: $('#vf-tel')?.value.trim() || '',
        fecha: $('#vf-fecha')?.value || null,
        forma_pago: $('#vf-pago')?.value || 'Contado',
        estado: $('#vf-estado')?.value || 'Pendiente',
        notas: $('#vf-notas')?.value || '',
        ciclo: $('#vf-ciclo')?.value.trim() || '',
        fecha_inicio_ciclo: $('#vf-ciclo-inicio')?.value || null,
        fecha_fin_ciclo: $('#vf-ciclo-fin')?.value || null,
        items: window.ventaItems || [],
      };

      try {
        await request(`${API}/sales/${editingSaleId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        toast('Venta actualizada correctamente');
        if (typeof window.closeModal === 'function') window.closeModal('modal-venta');
        editingSaleId = null;
        window.editVentaId = null;
        await loadSales();
        window.loadDashboard?.();
        window.loadCiclos?.();
      } catch (error) {
        toast(error.message, 'error');
      }
      return;
    }

    const items = window.ventaItems || [];
    if (!items.length) return toast('Agrega al menos un producto', 'error');

    const paymentMethod = $('#vf-pago')?.value || 'Contado';
    const total = calculateItems(items).total;
    const initialPayment = paymentMethod === 'Abono' ? Number($('#vf-abono-inicial')?.value || 0) : 0;
    if (paymentMethod === 'Abono' && (!Number.isFinite(initialPayment) || initialPayment <= 0 || initialPayment > total)) {
      return toast(`El abono inicial debe estar entre $1 y ${money(total)}`, 'error');
    }

    const select = $('#vf-cliente');
    const payload = {
      numero_factura: $('#vf-num')?.value.trim(),
      cliente_id: select?.value || null,
      cliente_nombre: select?.selectedOptions?.[0]?.text || '',
      cliente_email: $('#vf-email')?.value.trim() || '',
      cliente_telefono: $('#vf-tel')?.value.trim() || '',
      fecha: $('#vf-fecha')?.value || null,
      forma_pago: paymentMethod,
      estado: 'Pendiente',
      notas: $('#vf-notas')?.value || '',
      ciclo: $('#vf-ciclo')?.value.trim() || '',
      fecha_inicio_ciclo: $('#vf-ciclo-inicio')?.value || null,
      fecha_fin_ciclo: $('#vf-ciclo-fin')?.value || null,
      initial_payment: initialPayment,
      items,
    };

    try {
      await request(`${API}/sales`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      toast(paymentMethod === 'Abono' ? 'Venta registrada con abono inicial' : 'Venta registrada correctamente');
      if (typeof window.closeModal === 'function') window.closeModal('modal-venta');
      window.ventaItems = [];
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      window.loadCiclos?.();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  async function changeStatus(id, state) {
    try {
      await request(`${API}/sales/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estado: state }),
      });
      toast(state === 'Pagado' ? 'Venta marcada como pagada' : `Venta ${state.toLowerCase()}`);
      await loadSales();
      window.loadDashboard?.();
      window.loadCiclos?.();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  async function deleteSale(id, invoice) {
    if (!window.confirm(`¿Eliminar la venta ${invoice}?`)) return;
    try {
      await request(`${API}/sales/${id}`, { method: 'DELETE' });
      toast('Venta eliminada');
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      window.loadCiclos?.();
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  function showPaymentModal(id, invoice) {
    const existing = $('#lumeon-payment-modal');
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = 'lumeon-payment-modal';
    modal.className = 'modal-overlay open';
    modal.innerHTML = `<div class="modal" style="max-width:460px">
      <div class="modal-header"><div class="modal-title">Registrar abono</div><button type="button" class="btn-close" id="lumeon-payment-close">✕</button></div>
      <div class="modal-body">
        <div style="font-size:12px;color:var(--ink3);margin-bottom:14px">Factura <strong style="color:var(--ink)">${safe(invoice)}</strong></div>
        <div class="form-group"><label>Valor del abono</label><input id="lumeon-payment-amount" type="number" min="1" step="1" placeholder="0"></div>
        <div class="form-group" style="margin-top:14px"><label>Forma de pago</label><select id="lumeon-payment-method"><option>Abono</option><option>Contado</option><option>Transferencia</option><option>Nequi</option><option>Daviplata</option></select></div>
        <div class="form-group" style="margin-top:14px"><label>Nota</label><input id="lumeon-payment-note" placeholder="Opcional"></div>
      </div>
      <div class="modal-footer"><button class="btn btn-secondary" id="lumeon-payment-cancel">Cancelar</button><button class="btn btn-gold" id="lumeon-payment-save">Registrar abono</button></div>
    </div>`;
    document.body.appendChild(modal);
    const close = () => modal.remove();
    $('#lumeon-payment-close').onclick = close;
    $('#lumeon-payment-cancel').onclick = close;
    $('#lumeon-payment-save').onclick = async () => {
      const amount = Number($('#lumeon-payment-amount').value || 0);
      const method = $('#lumeon-payment-method').value;
      const note = $('#lumeon-payment-note').value.trim();
      if (!Number.isFinite(amount) || amount <= 0) return toast('Ingresa un monto válido', 'error');
      try {
        const result = await request(`${API}/sales/${id}/payments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ monto: amount, forma_pago: method, nota: note }),
        });
        close();
        toast(result.venta?.saldo_pendiente > 0 ? `Abono registrado. Saldo: ${money(result.venta.saldo_pendiente)}` : 'Abono registrado. Venta pagada.');
        await loadSales();
        window.loadDashboard?.();
        window.loadCiclos?.();
      } catch (error) {
        toast(error.message, 'error');
      }
    };
    $('#lumeon-payment-amount').focus();
  }

  function renderSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;
    const query = ($('#venta-search')?.value || '').trim().toLowerCase();

    const filtered = salesCache.filter(sale => {
      const status = String(sale.estado || '').toLowerCase();
      const payment = String(sale.estado_pago || '').toLowerCase();
      const text = [sale.numero_factura, sale.cliente_nombre, sale.cliente_email, sale.cliente_telefono].filter(Boolean).join(' ').toLowerCase();
      const matchesSearch = !query || text.includes(query);
      let matchesFilter = true;
      if (salesFilter === 'Abonado') matchesFilter = payment === 'abonado';
      else if (salesFilter) matchesFilter = status === salesFilter.toLowerCase();
      return matchesSearch && matchesFilter;
    });

    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div><div class="empty-text">No hay ventas para este filtro.</div></td></tr>';
      return;
    }

    tbody.innerHTML = filtered.map(sale => {
      const admin = isAdmin();
      const status = String(sale.estado || 'Pendiente');
      const paymentStatus = String(sale.estado_pago || status);
      const balance = Number(sale.saldo_pendiente || 0);
      const actions = [];
      if (admin) actions.push(`<button type="button" class="btn btn-ghost btn-sm btn-icon" data-action="edit" data-id="${Number(sale.id)}" title="Editar">✎</button>`);
      if (admin && status.toLowerCase() !== 'pagado' && status.toLowerCase() !== 'cancelado') actions.push(`<button type="button" class="btn btn-success btn-sm" data-action="paid" data-id="${Number(sale.id)}">Pagada</button>`);
      if (admin && balance > 0 && status.toLowerCase() !== 'cancelado') actions.push(`<button type="button" class="btn btn-gold btn-sm" data-action="payment" data-id="${Number(sale.id)}" data-invoice="${safe(sale.numero_factura)}">Abono</button>`);
      if (admin && status.toLowerCase() === 'pendiente') actions.push(`<button type="button" class="btn btn-ghost btn-sm btn-icon" data-action="cancel" data-id="${Number(sale.id)}" title="Cancelar">✕</button>`);
      if (admin) actions.push(`<button type="button" class="btn btn-danger btn-sm btn-icon" data-action="delete" data-id="${Number(sale.id)}" data-invoice="${safe(sale.numero_factura)}" title="Eliminar">🗑</button>`);
      return `<tr>
        <td class="td-mono">${safe(sale.numero_factura)}</td>
        <td style="font-weight:500">${safe(sale.cliente_nombre || '—')}</td>
        <td><span class="badge badge-blue">${safe(sale.ciclo || '—')}</span></td>
        <td style="color:var(--ink3)">${dateOnly(sale.fecha)}</td>
        <td>${safe(sale.forma_pago || 'Contado')}</td>
        <td class="td-mono" style="font-weight:600">${money(sale.total)}</td>
        <td class="td-mono" style="color:var(--sage)">${money(sale.ganancia)}</td>
        <td>${typeof window.badgeEstado === 'function' ? window.badgeEstado(paymentStatus) : `<span class="badge badge-amber">${safe(paymentStatus)}</span>`}</td>
        <td class="sales-actions">${actions.join('') || '<span style="font-size:11px;color:var(--ink3)">—</span>'}</td>
      </tr>`;
    }).join('');

    tbody.querySelectorAll('[data-action]').forEach(button => {
      const action = button.dataset.action;
      const id = Number(button.dataset.id);
      if (action === 'edit') button.onclick = () => openSaleEditor(id);
      if (action === 'paid') button.onclick = () => changeStatus(id, 'Pagado');
      if (action === 'cancel') button.onclick = () => changeStatus(id, 'Cancelado');
      if (action === 'payment') button.onclick = () => showPaymentModal(id, button.dataset.invoice || '');
      if (action === 'delete') button.onclick = () => deleteSale(id, button.dataset.invoice || '');
    });
  }

  async function loadSales() {
    try {
      const q = ($('#venta-search')?.value || '').trim();
      const body = await request(`${API}/sales?q=${encodeURIComponent(q)}`);
      salesCache = body.results || [];
      renderSales();
    } catch (error) {
      toast(`No se pudieron cargar las ventas: ${error.message}`, 'error');
    }
  }

  function bindSalesUi() {
    $('#venta-search')?.addEventListener('input', renderSales);
    $('#ventas-tabs')?.querySelectorAll('.tab').forEach((button, index) => {
      const states = ['', 'Pendiente', 'Abonado', 'Pagado', 'Cancelado'];
      button.onclick = () => {
        salesFilter = states[index];
        $('#ventas-tabs').querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        renderSales();
      };
    });
    const add = $('#vf-ref')?.parentElement?.querySelector('button');
    if (add) add.onclick = addSaleItemFromUi;
    $('#vf-ref')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); addSaleItemFromUi(); }
    });
    const save = $('#btn-save-venta');
    if (save) save.onclick = saveSale;
  }

  function patchNavigationAfterLoad() {
    bindNavigation();
    patchTopbar();
    showAdminNav();
    if (window.currentPage === 'ventas') loadSales();
  }

  function patchExistingUserUi() {
    showAdminNav();
    const observer = new MutationObserver(() => showAdminNav());
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function start() {
    ensureSaleModalEnhancements();
    bindSalesUi();
    patchNavigationAfterLoad();
    patchExistingUserUi();
    window.loadVentas = loadSales;
    window.filterVentas = (button, state) => {
      salesFilter = state || '';
      $('#ventas-tabs')?.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      button?.classList.add('active');
      renderSales();
    };
    window.editarVenta = openSaleEditor;
    window.saveVenta = saveSale;
    window.marcarPagada = id => changeStatus(id, 'Pagado');
    window.cambiarEstado = changeStatus;
    window.eliminarVenta = deleteSale;
    window.registrarAbono = showPaymentModal;
    window.openModalVenta = () => openSaleEditor();
    if ($('#page-ventas')?.classList.contains('active')) loadSales();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
