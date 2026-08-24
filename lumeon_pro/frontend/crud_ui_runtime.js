(() => {
  'use strict';

  const V2 = '/api/v2';
  const esc = (v) => String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  const money = (v) => new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(Number(v || 0));

  const request = async (url, options = {}) => {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      throw new Error(body.error || `HTTP ${response.status}`);
    }
    return body;
  };

  const notify = (message, type = 'success') => {
    if (typeof window.toast === 'function') window.toast(message, type);
    else console.log(message);
  };

  async function loadInventario() {
    const tbody = document.querySelector('#tbl-inventario tbody');
    if (!tbody) return;
    try {
      const q = document.getElementById('inv-search')?.value || '';
      const data = await request(`${V2}/productos?q=${encodeURIComponent(q)}&limit=100`);
      const products = data.results || [];
      tbody.innerHTML = products.map((p) => {
        const margin = Number(p.precio_venta || 0) - Number(p.precio_compra || 0);
        const marginPct = Number(p.precio_compra || 0) > 0
          ? `${(margin / Number(p.precio_compra) * 100).toFixed(1)}%` : '—';
        const status = Number(p.stock) === 0
          ? '<span class="badge badge-red">Agotado</span>'
          : Number(p.stock) <= Number(p.stock_minimo)
            ? '<span class="badge badge-amber">Bajo</span>'
            : '<span class="badge badge-green">OK</span>';
        return `<tr>
          <td class="td-mono">${esc(p.referencia)}</td>
          <td><div style="font-weight:500">${esc(p.nombre)}</div><div style="font-size:11px;color:var(--ink3)">${esc(p.descripcion || '')}</div></td>
          <td><span class="badge badge-gray">${esc(p.categoria)}</span></td>
          <td class="td-mono">${money(p.precio_compra)}</td>
          <td class="td-mono">${money(p.precio_venta)}</td>
          <td class="td-mono" style="color:var(--sage)">${money(margin)} <span style="color:var(--ink3)">${marginPct}</span></td>
          <td><strong>${Number(p.stock || 0)}</strong></td>
          <td>${status}</td>
          <td style="white-space:nowrap;display:flex;gap:4px">
            <button type="button" class="btn btn-ghost btn-sm btn-icon" data-edit-product="${p.id}" title="Editar">✎</button>
            <button type="button" class="btn btn-danger btn-sm btn-icon" data-delete-product="${p.id}" data-name="${esc(p.nombre)}" title="Eliminar">✕</button>
          </td>
        </tr>`;
      }).join('') || '<tr><td colspan="9" class="empty"><div class="empty-title">Sin productos</div></td></tr>';

      tbody.querySelectorAll('[data-edit-product]').forEach((button) => {
        button.onclick = () => editProducto(Number(button.dataset.editProduct));
      });
      tbody.querySelectorAll('[data-delete-product]').forEach((button) => {
        button.onclick = () => delProducto(Number(button.dataset.deleteProduct), button.dataset.name || '');
      });
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty"><div class="empty-title">Error al cargar inventario</div><div class="empty-text">${esc(error.message)}</div></td></tr>`;
    }
  }

  async function editProducto(id) {
    try {
      const data = await request(`${V2}/productos?q=&limit=100`);
      const product = (data.results || []).find((item) => Number(item.id) === Number(id));
      if (!product) throw new Error('Producto no encontrado');
      window.editProductoId = Number(id);
      document.getElementById('mp-title').textContent = 'Editar Producto';
      const fields = {
        nombre: product.nombre,
        ref: product.referencia,
        cat: product.categoria,
        desc: product.descripcion,
        pc: product.precio_compra,
        pv: product.precio_venta,
        stock: product.stock,
        smin: product.stock_minimo,
      };
      Object.entries(fields).forEach(([key, value]) => {
        const element = document.getElementById(`mp-${key}`);
        if (element) element.value = value ?? '';
      });
      window.openModal('modal-producto');
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function saveProducto() {
    const body = {
      nombre: document.getElementById('mp-nombre')?.value.trim(),
      referencia: document.getElementById('mp-ref')?.value.trim(),
      categoria: document.getElementById('mp-cat')?.value,
      descripcion: document.getElementById('mp-desc')?.value.trim(),
      precio_compra: Number(document.getElementById('mp-pc')?.value || 0),
      precio_venta: Number(document.getElementById('mp-pv')?.value || 0),
      stock: Number(document.getElementById('mp-stock')?.value || 0),
      stock_minimo: Number(document.getElementById('mp-smin')?.value || 0),
    };
    if (!body.nombre || !body.referencia) return notify('Nombre y referencia son obligatorios', 'error');
    try {
      const id = Number(window.editProductoId || 0);
      if (id) {
        await request(`${V2}/productos/${id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        notify('Producto actualizado');
      } else {
        await request(`${V2}/productos`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        notify('Producto creado');
      }
      window.editProductoId = null;
      window.closeModal('modal-producto');
      await loadInventario();
      window.loadDashboard?.();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function delProducto(id, name) {
    if (!confirm(`¿Eliminar "${name}"?`)) return;
    try {
      await request(`${V2}/productos/${id}`, { method: 'DELETE' });
      notify('Producto eliminado');
      await loadInventario();
      window.loadDashboard?.();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function loadClientes() {
    const tbody = document.querySelector('#tbl-clientes tbody');
    if (!tbody) return;
    try {
      const q = document.getElementById('cli-search')?.value || '';
      const data = await request(`${V2}/clientes?q=${encodeURIComponent(q)}&limit=100`);
      const clients = data.results || [];
      tbody.innerHTML = clients.map((c) => `<tr>
        <td style="font-weight:500">${esc(c.nombre)}</td>
        <td class="td-mono">${esc(c.documento || '—')}</td>
        <td>${esc(c.telefono || '—')}</td>
        <td>${esc(c.ciudad || '—')}</td>
        <td style="color:var(--ink3)">${esc(c.email || '—')}</td>
        <td style="display:flex;gap:4px">
          <button type="button" class="btn btn-ghost btn-sm btn-icon" data-edit-client="${c.id}" title="Editar">✎</button>
          <button type="button" class="btn btn-danger btn-sm btn-icon" data-delete-client="${c.id}" data-name="${esc(c.nombre)}" title="Eliminar">✕</button>
        </td>
      </tr>`).join('') || '<tr><td colspan="6" class="empty"><div class="empty-title">Sin clientes</div></td></tr>';

      tbody.querySelectorAll('[data-edit-client]').forEach((button) => {
        button.onclick = () => editCliente(Number(button.dataset.editClient));
      });
      tbody.querySelectorAll('[data-delete-client]').forEach((button) => {
        button.onclick = () => eliminarCliente(Number(button.dataset.deleteClient), button.dataset.name || '');
      });
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty"><div class="empty-title">Error al cargar clientes</div><div class="empty-text">${esc(error.message)}</div></td></tr>`;
    }
  }

  async function editCliente(id) {
    try {
      const data = await request(`${V2}/clientes?q=&limit=100`);
      const client = (data.results || []).find((item) => Number(item.id) === Number(id));
      if (!client) throw new Error('Cliente no encontrado');
      window.editClienteId = Number(id);
      document.getElementById('mc-title').textContent = 'Editar Cliente';
      const fields = {
        nombre: client.nombre, doc: client.documento, tel: client.telefono,
        dir: client.direccion, ciudad: client.ciudad, email: client.email,
      };
      Object.entries(fields).forEach(([key, value]) => {
        const element = document.getElementById(`mc-${key}`);
        if (element) element.value = value ?? '';
      });
      window.openModal('modal-cliente');
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function saveCliente() {
    const body = {
      nombre: document.getElementById('mc-nombre')?.value.trim(),
      documento: document.getElementById('mc-doc')?.value.trim(),
      telefono: document.getElementById('mc-tel')?.value.trim(),
      direccion: document.getElementById('mc-dir')?.value.trim(),
      ciudad: document.getElementById('mc-ciudad')?.value.trim(),
      email: document.getElementById('mc-email')?.value.trim(),
    };
    if (!body.nombre) return notify('El nombre es obligatorio', 'error');
    try {
      const id = Number(window.editClienteId || 0);
      if (id) {
        await request(`${V2}/clientes/${id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        notify('Cliente actualizado');
      } else {
        await request(`${V2}/clientes`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        notify('Cliente creado');
      }
      window.editClienteId = null;
      window.closeModal('modal-cliente');
      await loadClientes();
      window.loadDashboard?.();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  async function eliminarCliente(id, name) {
    if (!confirm(`¿Eliminar al cliente "${name}"?`)) return;
    try {
      await request(`${V2}/clientes/${id}`, { method: 'DELETE' });
      notify('Cliente eliminado');
      await loadClientes();
      window.loadDashboard?.();
    } catch (error) {
      notify(error.message, 'error');
    }
  }

  window.loadInventario = loadInventario;
  window.editProducto = editProducto;
  window.saveProducto = saveProducto;
  window.delProducto = delProducto;
  window.loadClientes = loadClientes;
  window.editCliente = editCliente;
  window.saveCliente = saveCliente;
  window.eliminarCliente = eliminarCliente;

  function start() {
    if (window.__lumeonCrudRuntimeReady) return;
    window.__lumeonCrudRuntimeReady = true;
    if (document.getElementById('page-inventario')?.classList.contains('active')) loadInventario();
    if (document.getElementById('page-clientes')?.classList.contains('active')) loadClientes();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
