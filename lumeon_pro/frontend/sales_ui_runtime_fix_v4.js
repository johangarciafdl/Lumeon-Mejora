(() => {
  'use strict';

  const V2 = '/api/v2';
  const API = '/api';

  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const safe = (v) => String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const money = (v) => new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
  }).format(Number(v || 0));

  const dateOnly = (v) => {
    if (!v) return '—';
    return String(v).slice(0, 10).split('-').reverse().join('/');
  };

  const notify = (m, type = 'success') => {
    if (typeof window.toast === 'function') window.toast(m, type);
    else console[type === 'error' ? 'error' : 'log'](m);
  };

  let sales = [];
  let salesFilter = '';
  let editingSaleId = null;
  let saleItems = [];
  let started = false;

  async function request(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      throw new Error(body.error || `HTTP ${response.status}`);
    }
    return body;
  }

  function admin() {
    return String(window.currentUser?.role || '').toLowerCase() === 'admin'
      || window.lumeonIsAdmin === true;
  }

  function syncAdmin() {
    $$('.admin-only-nav').forEach((el) => {
      el.style.display = admin() ? '' : 'none';
    });
  }

  async function syncAuth() {
    try {
      const body = await request(`${V2}/auth/me`);
      if (body.authenticated) {
        window.currentUser = {
          user_id: body.user_id,
          username: body.username || body.user?.username || String(body.user_id || ''),
          role: String(body.role || body.user?.role || '').toLowerCase(),
        };
        window.lumeonIsAdmin = window.currentUser.role === 'admin';
      }
    } catch (error) {
      console.warn('sales auth sync:', error.message);
    }
    syncAdmin();
  }

  function navigate(page) {
    const target = document.getElementById(`page-${page}`);
    if (!target) return;

    $$('.page').forEach((p) => p.classList.remove('active'));
    target.classList.add('active');
    window.currentPage = page;

    const titles = {
      dashboard: 'Dashboard',
      inventario: 'Inventario',
      ventas: 'Ventas',
      clientes: 'Clientes',
      ciclos: 'Ciclos',
      devoluciones: 'Devoluciones',
      'admin-logs': 'Registros',
    };
    if ($('#topbar-title')) $('#topbar-title').textContent = titles[page] || 'Lumeon';

    const topbar = $('#topbar-action');
    const labels = {
      inventario: 'Nuevo Producto',
      ventas: 'Nueva Venta',
      clientes: 'Nuevo Cliente',
      devoluciones: 'Nueva Devolución',
    };
    if (topbar) {
      if (labels[page]) {
        topbar.style.display = 'flex';
        topbar.textContent = `+ ${labels[page]}`;
        topbar.onclick = () => {
          if (page === 'ventas') window.openModalVenta?.();
          else if (page === 'inventario') window.openModalProducto?.();
          else if (page === 'clientes') window.openModalCliente?.();
          else if (page === 'devoluciones') window.openModalDevolucion?.();
        };
      } else {
        topbar.style.display = 'none';
      }
    }

    $$('#sidebar .nav-item').forEach((item) => item.classList.remove('active'));
    const map = {
      dashboard: 'dashboard',
      inventario: 'inventario',
      ventas: 'ventas',
      clientes: 'clientes',
      ciclos: 'ciclos',
      devoluciones: 'devoluciones',
      registros: 'admin-logs',
    };
    $$('#sidebar .nav-item').forEach((item) => {
      if (map[item.textContent.trim().toLowerCase()] === page) item.classList.add('active');
    });
    if (page === 'admin-logs') $('#nav-registros')?.classList.add('active');

    if (page === 'ventas') loadSales();
    else if (page === 'ciclos') loadCycles();
    else if (page === 'admin-logs') loadLogs();
    else if (page === 'dashboard') window.loadDashboard?.();
    else if (page === 'inventario') window.loadInventario?.();
    else if (page === 'clientes') window.loadClientes?.();
    else if (page === 'devoluciones') window.loadDevoluciones?.();

    window.closeMobileMenu?.();
  }

  function bindNavigation() {
    $$('#sidebar .nav-item').forEach((item) => {
      item.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        const text = item.textContent.trim().toLowerCase();
        const page = {
          dashboard: 'dashboard',
          inventario: 'inventario',
          ventas: 'ventas',
          clientes: 'clientes',
          ciclos: 'ciclos',
          devoluciones: 'devoluciones',
          registros: 'admin-logs',
        }[text];
        if (page) navigate(page);
      };
    });
    window.goto = navigate;
  }

  function ensureNewSaleButton() {
    const page = $('#page-ventas');
    if (!page || $('#sales-new-sale-button')) return;

    const header = page.querySelector('.page-header');
    if (!header) return;

    const button = document.createElement('button');
    button.id = 'sales-new-sale-button';
    button.type = 'button';
    button.className = 'btn btn-gold';
    button.textContent = '+ Nueva Venta';
    button.style.cssText = 'margin-left:auto;min-height:38px;white-space:nowrap;';
    button.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      window.openModalVenta?.();
    };

    header.style.display = 'flex';
    header.style.alignItems = 'flex-start';
    header.style.justifyContent = 'space-between';
    header.appendChild(button);
  }

  async function loadSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;

    try {
      const q = ($('#venta-search')?.value || '').trim();
      let body;
      try {
        body = await request(`${V2}/sales?q=${encodeURIComponent(q)}`);
        sales = Array.isArray(body.results) ? body.results : [];
      } catch (v2Error) {
        const legacy = await request(`${API}/ventas?q=${encodeURIComponent(q)}`);
        sales = Array.isArray(legacy) ? legacy : (legacy.results || []);
      }
      renderSales();
    } catch (error) {
      console.error('loadSales:', error);
      sales = [];
      tbody.innerHTML = `<tr><td colspan="9" class="empty"><div class="empty-title">Error al cargar ventas</div><div class="empty-text">${safe(error.message)}</div></td></tr>`;
    }
  }

  function renderSales() {
    const tbody = $('#tbl-ventas tbody');
    if (!tbody) return;

    const q = ($('#venta-search')?.value || '').trim().toLowerCase();
    const filter = String(salesFilter || '').toLowerCase();

    const filtered = sales.filter((sale) => {
      const text = [
        sale.numero_factura,
        sale.cliente_nombre,
        sale.cliente_email,
        sale.cliente_telefono,
      ].filter(Boolean).join(' ').toLowerCase();

      const state = String(sale.estado || 'Pendiente').toLowerCase();
      const payment = String(sale.estado_pago || '').toLowerCase();

      const stateMatches = !filter || (
        filter === 'abonado'
          ? payment === 'abonado'
          : state === filter
      );

      return stateMatches && (!q || text.includes(q));
    });

    if (!filtered.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty"><div class="empty-title">Sin ventas</div><div class="empty-text">No hay ventas para este filtro.</div></td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map((sale) => {
      const state = String(sale.estado || 'Pendiente');
      const shownState = String(sale.estado_pago || state);
      const balance = Number(sale.saldo_pendiente || 0);
      const canAdmin = admin();

      const actions = canAdmin ? `
        <button type="button" class="btn btn-ghost btn-sm btn-icon" onclick="window.openSaleForEdit(${Number(sale.id)});return false;" title="Editar">✎</button>
        ${state.toLowerCase() !== 'pagado' && state.toLowerCase() !== 'cancelado'
          ? `<button type="button" class="btn btn-success btn-sm" onclick="window.markSalePaid(${Number(sale.id)});return false;">Pagada</button>`
          : ''}
        ${balance > 0 && state.toLowerCase() !== 'cancelado'
          ? `<button type="button" class="btn btn-gold btn-sm" onclick="window.addSalePayment(${Number(sale.id)});return false;">Abono</button>`
          : ''}
        ${state.toLowerCase() === 'pendiente'
          ? `<button type="button" class="btn btn-ghost btn-sm btn-icon" onclick="window.cancelSale(${Number(sale.id)});return false;" title="Cancelar">✕</button>`
          : ''}
        <button type="button" class="btn btn-danger btn-sm btn-icon" onclick="window.deleteSaleFromUi(${Number(sale.id)}, '${safe(sale.numero_factura || '')}');return false;" title="Eliminar">🗑</button>
      ` : '<span style="font-size:11px;color:var(--ink3)">—</span>';

      const badge = typeof window.badgeEstado === 'function'
        ? window.badgeEstado(shownState)
        : `<span class="badge badge-amber">${safe(shownState)}</span>`;

      return `<tr>
        <td class="td-mono">${safe(sale.numero_factura || '—')}</td>
        <td style="font-weight:500">${safe(sale.cliente_nombre || '—')}</td>
        <td>${safe(sale.ciclo || '—')}</td>
        <td style="color:var(--ink3)">${dateOnly(sale.fecha)}</td>
        <td>${safe(sale.forma_pago || 'Contado')}</td>
        <td class="td-mono" style="font-weight:600">${money(sale.total)}</td>
        <td class="td-mono" style="color:var(--sage)">${money(sale.ganancia)}</td>
        <td>${badge}</td>
        <td class="sales-actions" style="white-space:nowrap;display:flex;gap:4px;align-items:center">${actions}</td>
      </tr>`;
    }).join('');
  }

  async function loadClients(selectedId = null) {
    const body = await request(`${V2}/clientes?q=&limit=200`);
    const clients = body.results || [];
    const select = $('#vf-cliente');
    if (!select) return;
    select.innerHTML = '<option value="">-- Sin cliente --</option>' + clients.map((client) =>
      `<option value="${Number(client.id)}">${safe(client.nombre)}</option>`
    ).join('');
    if (selectedId != null) select.value = String(selectedId);
  }

  function renderItems() {
    const tbody = $('#vf-items-body');
    if (!tbody) return;

    let total = 0;
    let gain = 0;

    tbody.innerHTML = saleItems.map((item, index) => {
      const qty = Number(item.cantidad || 0);
      const sell = Number(item.precio_venta || 0);
      const buy = Number(item.precio_compra || 0);
      const line = qty * sell;
      total += line;
      gain += qty * (sell - buy);

      return `<tr>
        <td class="td-mono">${safe(item.referencia)}</td>
        <td>${safe(item.nombre)}</td>
        <td>${qty}</td>
        <td>${money(buy)}</td>
        <td>${money(sell)}</td>
        <td>${money(line)}</td>
        <td><button type="button" class="btn btn-danger btn-sm btn-icon" onclick="window.removeSaleItem(${index});return false;">✕</button></td>
      </tr>`;
    }).join('');

    if ($('#vs-sub')) $('#vs-sub').textContent = money(total);
    if ($('#vs-total')) $('#vs-total').textContent = money(total);
    if ($('#vs-gan')) $('#vs-gan').textContent = money(gain);

    window.ventaItems = saleItems;
  }

  async function addItem() {
    const reference = $('#vf-ref')?.value.trim();
    const quantity = Number($('#vf-cant')?.value || 1);

    if (!reference) return notify('Ingresa la referencia', 'error');
    if (!Number.isInteger(quantity) || quantity <= 0) return notify('Cantidad inválida', 'error');

    try {
      const product = await request(`${API}/productos/buscar/${encodeURIComponent(reference)}`);
      if (!product?.id) throw new Error('Producto no encontrado');

      const index = saleItems.findIndex((item) => item.referencia === product.referencia);
      if (index >= 0) saleItems[index].cantidad += quantity;
      else {
        saleItems.push({
          producto_id: Number(product.id),
          referencia: product.referencia,
          nombre: product.nombre,
          cantidad: quantity,
          precio_compra: Number(product.precio_compra || 0),
          precio_venta: Number(product.precio_venta || 0),
        });
      }

      renderItems();
      if ($('#vf-ref')) $('#vf-ref').value = '';
      if ($('#vf-cant')) $('#vf-cant').value = '1';
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  function removeSaleItem(index) {
    saleItems.splice(index, 1);
    renderItems();
  }

  function openSaleModal() {
    const modal = $('#modal-venta');
    if (!modal) {
      notify('No se encontró el formulario de venta', 'error');
      return;
    }
    if (typeof window.openModal === 'function') window.openModal('modal-venta');
    else modal.classList.add('open');
  }

  function closeSaleModal() {
    const modal = $('#modal-venta');
    if (typeof window.closeModal === 'function') window.closeModal('modal-venta');
    else modal?.classList.remove('open');
    editingSaleId = null;
    saleItems = [];
    window.editVentaId = null;
    window.ventaItems = [];
  }

  async function openNewSale() {
    try {
      editingSaleId = null;
      saleItems = [];
      if ($('#mv-title')) $('#mv-title').textContent = 'Nueva Venta';
      if ($('#btn-save-venta')) $('#btn-save-venta').textContent = 'Registrar Venta';
      if ($('#vf-num')) $('#vf-num').value = `FAC-${Date.now()}`;
      if ($('#vf-fecha')) $('#vf-fecha').value = new Date().toISOString().slice(0, 10);
      if ($('#vf-pago')) $('#vf-pago').value = 'Contado';
      if ($('#vf-estado')) $('#vf-estado').value = 'Pendiente';
      if ($('#vf-ciclo')) $('#vf-ciclo').value = '';
      if ($('#vf-ciclo-inicio')) $('#vf-ciclo-inicio').value = '';
      if ($('#vf-ciclo-fin')) $('#vf-ciclo-fin').value = '';
      if ($('#vf-email')) $('#vf-email').value = '';
      if ($('#vf-tel')) $('#vf-tel').value = '';
      if ($('#vf-notas')) $('#vf-notas').value = '';
      if ($('#vf-abono-inicial')) $('#vf-abono-inicial').value = '';
      if ($('#vf-abono-inicial-group')) $('#vf-abono-inicial-group').style.display = 'none';
      if ($('#sales-management-payments')) $('#sales-management-payments').style.display = 'none';
      await loadClients(null);
      renderItems();
      openSaleModal();
    } catch (error) {
      notify(`No se pudo abrir nueva venta: ${error.message}`, 'error');
    }
  }

  async function openEditSale(id) {
    try {
      const detail = await request(`${V2}/sales/${id}`);
      const sale = detail.venta || {};
      editingSaleId = id;
      if ($('#mv-title')) $('#mv-title').textContent = 'Editar Venta';
      if ($('#btn-save-venta')) $('#btn-save-venta').textContent = 'Guardar cambios';

      const set = (selector, value) => {
        const element = $(selector);
        if (element) element.value = value ?? '';
      };

      set('#vf-num', sale.numero_factura);
      set('#vf-fecha', sale.fecha ? String(sale.fecha).slice(0, 10) : '');
      set('#vf-ciclo', sale.ciclo);
      set('#vf-ciclo-inicio', sale.fecha_inicio_ciclo);
      set('#vf-ciclo-fin', sale.fecha_fin_ciclo);
      set('#vf-pago', sale.forma_pago || 'Contado');
      set('#vf-email', sale.cliente_email);
      set('#vf-tel', sale.cliente_telefono);
      set('#vf-notas', sale.notas);
      set('#vf-estado', sale.estado || 'Pendiente');

      saleItems = (detail.items || []).map((item) => ({
        producto_id: Number(item.producto_id),
        referencia: item.referencia,
        nombre: item.nombre,
        cantidad: Number(item.cantidad || 0),
        precio_compra: Number(item.precio_compra || 0),
        precio_venta: Number(item.precio_venta || 0),
      }));

      await loadClients(sale.cliente_id);
      renderItems();

      const paymentBox = $('#sales-management-payments');
      if (paymentBox) {
        const abonos = detail.abonos || [];
        paymentBox.style.display = '';
        paymentBox.innerHTML = `<div style="font-size:11px;font-weight:600;margin-bottom:10px">Historial de cuotas</div>` +
          (abonos.length
            ? abonos.map((item, index) => `<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--border)"><div><strong>Cuota ${index + 1}</strong><div style="font-size:10px;color:var(--ink3)">${safe(item.forma_pago || 'Abono')} · ${dateOnly(item.fecha)}</div></div><strong>${money(item.monto)}</strong></div>`).join('')
            : '<div style="font-size:12px;color:var(--ink3)">No hay abonos registrados.</div>') +
          `<div style="display:flex;justify-content:space-between;margin-top:12px;font-size:12px;font-weight:600"><span>Total abonado</span><strong>${money(sale.total_abonado)}</strong></div>` +
          `<div style="display:flex;justify-content:space-between;margin-top:5px;font-size:12px;font-weight:600;color:var(--gold)"><span>Saldo pendiente</span><strong>${money(sale.saldo_pendiente)}</strong></div>`;
      }

      openSaleModal();
    } catch (error) {
      notify(`No se pudo abrir la venta: ${error.message}`, 'error');
    }
  }

  async function saveSale() {
    const client = $('#vf-cliente');

    const payload = {
      numero_factura: $('#vf-num')?.value.trim(),
      cliente_id: client?.value || null,
      cliente_nombre: client?.selectedOptions?.[0]?.text || '',
      cliente_email: $('#vf-email')?.value.trim() || '',
      cliente_telefono: $('#vf-tel')?.value.trim() || '',
      fecha: $('#vf-fecha')?.value || null,
      forma_pago: $('#vf-pago')?.value || 'Contado',
      estado: $('#vf-estado')?.value || 'Pendiente',
      notas: $('#vf-notas')?.value || '',
      ciclo: $('#vf-ciclo')?.value.trim() || '',
      fecha_inicio_ciclo: $('#vf-ciclo-inicio')?.value || null,
      fecha_fin_ciclo: $('#vf-ciclo-fin')?.value || null,
      items: saleItems,
    };

    try {
      if (editingSaleId != null) {
        await request(`${V2}/sales/${editingSaleId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        notify('Venta actualizada correctamente');
      } else {
        if (!saleItems.length) {
          notify('Agrega al menos un producto', 'error');
          return;
        }

        const total = saleItems.reduce(
          (sum, item) => sum + Number(item.cantidad || 0) * Number(item.precio_venta || 0),
          0,
        );

        const payment = payload.forma_pago;
        let initial = 0;

        if (payment === 'Abono') {
          initial = Number($('#vf-abono-inicial')?.value || 0);
          if (!Number.isFinite(initial) || initial <= 0 || initial > total) {
            notify(`El abono inicial debe estar entre $1 y ${money(total)}`, 'error');
            return;
          }
        }

        await request(`${V2}/sales`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...payload, initial_payment: initial }),
        });

        notify(payment === 'Abono' ? 'Venta registrada con abono inicial' : 'Venta registrada correctamente');
      }

      closeSaleModal();
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      loadCycles();
    } catch (error) {
      console.error('saveSale:', error);
      notify(error.message, 'error');
    }
  }

  async function changeStatus(id, state) {
    try {
      await request(`${V2}/sales/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estado: state }),
      });
      notify(state === 'Pagado' ? 'Venta marcada como pagada' : `Venta ${state}`);
      await loadSales();
      window.loadDashboard?.();
      loadCycles();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function addPayment(id) {
    const sale = sales.find((row) => Number(row.id) === Number(id));
    const invoice = sale?.numero_factura || `Venta ${id}`;
    const raw = prompt(`Valor del abono para ${invoice}:`, '');
    if (raw === null) return;
    const amount = Number(String(raw).replace(',', '.'));
    if (!Number.isFinite(amount) || amount <= 0) {
      notify('Monto inválido', 'error');
      return;
    }

    try {
      const body = await request(`${V2}/sales/${id}/payments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monto: amount, forma_pago: 'Abono' }),
      });
      notify(Number(body.venta?.saldo_pendiente || 0) > 0
        ? `Abono registrado. Saldo: ${money(body.venta.saldo_pendiente)}`
        : 'Abono registrado. Venta pagada');
      await loadSales();
      loadCycles();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function cancelSale(id) {
    if (!confirm('¿Cancelar esta venta?')) return;
    await changeStatus(id, 'Cancelado');
  }

  async function deleteSaleFromUi(id, invoice) {
    if (!confirm(`¿Eliminar la venta ${invoice}? Esta acción restaurará el stock.`)) return;
    try {
      await request(`${V2}/sales/${id}`, { method: 'DELETE' });
      notify('Venta eliminada correctamente');
      await loadSales();
      window.loadDashboard?.();
      window.loadInventario?.();
      loadCycles();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function loadCycles() {
    const box = $('#ciclos-container');
    if (!box) return;
    try {
      const raw = await request(`${API}/ciclos`);
      const cycles = Array.isArray(raw) ? raw : (raw.results || []);

      if (!cycles.length) {
        box.innerHTML = '<div class="empty"><div class="empty-title">Sin ciclos</div><div class="empty-text">No hay ciclos registrados.</div></div>';
        return;
      }

      const details = await Promise.all(cycles.map(async (cycle) => {
        try {
          return await request(`${API}/ciclos/${encodeURIComponent(cycle)}/resumen`);
        } catch (_) {
          return { ciclo: cycle, total: 0, ganancia: 0, num_ventas: 0, ventas: [] };
        }
      }));

      box.innerHTML = details.map((item) => `<div class="card" style="margin-bottom:12px">
        <div class="card-header"><div><div class="card-title">Ciclo ${safe(item.ciclo)}</div><div class="card-subtitle">${Number(item.num_ventas || 0)} ventas</div></div><strong>${money(item.total)}</strong></div>
        <div style="font-size:11px;color:var(--ink3);margin-bottom:10px">Ganancia ${money(item.ganancia)}</div>
      </div>`).join('');
    } catch (error) {
      box.innerHTML = `<div class="empty"><div class="empty-title">Error al cargar ciclos</div><div class="empty-text">${safe(error.message)}</div></div>`;
    }
  }

  async function loadLogs() {
    const box = $('#admin-logs-list');
    if (!box) return;
    try {
      const body = await request(`${V2}/admin/logs?limit=200`);
      const logs = body.results || [];
      box.innerHTML = logs.length
        ? logs.map((log) => `<div class="admin-log-card"><div class="admin-log-head"><strong>${safe(log.action)}</strong><span>${safe(log.username || 'sistema')}</span><span>${safe(log.created_at || '')}</span></div><div class="admin-log-entity">${safe(log.entity_type || 'sistema')} #${safe(log.entity_id || '—')}</div><div class="admin-log-meta">${safe(log.metadata || '')}</div></div>`).join('')
        : '<div class="empty"><div class="empty-title">Sin registros</div></div>';
    } catch (error) {
      box.innerHTML = `<div class="empty"><div class="empty-title">Error al cargar registros</div><div class="empty-text">${safe(error.message)}</div></div>`;
    }
  }

  function bindSales() {
    $('#venta-search')?.addEventListener('input', renderSales);

    $('#ventas-tabs')?.querySelectorAll('.tab').forEach((button, index) => {
      const states = ['', 'Pendiente', 'Abonado', 'Pagado', 'Cancelado'];
      button.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        salesFilter = states[index] || '';
        $('#ventas-tabs').querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
        button.classList.add('active');
        renderSales();
      };
    });

    const addButton = $('#vf-ref')?.parentElement?.querySelector('button');
    if (addButton) addButton.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      addItem();
    };

    $('#vf-ref')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        addItem();
      }
    });

    const saveButton = $('#btn-save-venta');
    if (saveButton) saveButton.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      saveSale();
    };

    $$('#modal-venta .btn-close, #modal-venta .modal-footer .btn-secondary').forEach((button) => {
      button.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        closeSaleModal();
      };
    });

    const payment = $('#vf-pago');
    if (payment) {
      payment.onchange = () => {
        const box = $('#vf-abono-inicial-group');
        if (box) box.style.display = payment.value === 'Abono' ? '' : 'none';
      };
    }
  }

  function bindGlobals() {
    window.openModalVenta = openNewSale;
    window.openSaleForEdit = openEditSale;
    window.markSalePaid = (id) => changeStatus(id, 'Pagado');
    window.cancelSale = cancelSale;
    window.addSalePayment = addPayment;
    window.deleteSaleFromUi = deleteSaleFromUi;
    window.removeSaleItem = removeSaleItem;
    window.loadVentas = loadSales;
    window.renderVentas = renderSales;
    window.filterVentas = (button, state) => {
      salesFilter = state || '';
      $('#ventas-tabs')?.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
      button?.classList.add('active');
      renderSales();
    };
    window.saveVenta = saveSale;
    window.editarVenta = openEditSale;
    window.marcarPagada = (id) => changeStatus(id, 'Pagado');
    window.eliminarVenta = deleteSaleFromUi;
    window.registrarAbono = addPayment;
    window.loadCiclos = loadCycles;
    window.loadAdminLogs = loadLogs;
    window.addVentaItem = addItem;
  }

  function start() {
    if (started) return;
    started = true;

    bindNavigation();
    bindSales();
    bindGlobals();
    ensureNewSaleButton();
    syncAuth();

    if ($('#page-ventas')?.classList.contains('active')) loadSales();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
