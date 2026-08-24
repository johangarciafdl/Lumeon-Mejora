(() => {
  'use strict';

  const API = '/api/v2';
  const originalEdit = window.editarVenta;
  const originalNew = window.openModalVenta;

  const safe = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  async function getClients() {
    const response = await fetch(`${API}/clientes?q=&limit=100`, {
      credentials: 'same-origin',
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      throw new Error(body.error || `HTTP ${response.status}`);
    }
    return body.results || [];
  }

  async function fillClients(selectedId) {
    const select = document.getElementById('vf-cliente');
    if (!select) return;
    const clients = await getClients();
    select.innerHTML = '<option value="">-- Sin cliente --</option>' + clients.map(c => `<option value="${Number(c.id)}">${safe(c.nombre)}</option>`).join('');
    if (selectedId != null) select.value = String(selectedId);
  }

  async function loadDetail(id) {
    const response = await fetch(`${API}/sales/${id}`, { credentials: 'same-origin' });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
  }

  function syncFormFromDetail(detail) {
    const sale = detail.venta || {};
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = value ?? '';
    };
    set('vf-num', sale.numero_factura);
    set('vf-fecha', sale.fecha ? String(sale.fecha).slice(0, 10) : '');
    set('vf-ciclo', sale.ciclo);
    set('vf-ciclo-inicio', sale.fecha_inicio_ciclo);
    set('vf-ciclo-fin', sale.fecha_fin_ciclo);
    set('vf-pago', sale.forma_pago || 'Contado');
    set('vf-email', sale.cliente_email);
    set('vf-tel', sale.cliente_telefono);
    set('vf-notas', sale.notas);
    set('vf-estado', sale.estado || 'Pendiente');
    const items = detail.items || [];
    if (typeof window.renderVentaItems === 'function') {
      window.ventaItems = items.map(x => ({
        producto_id: x.producto_id,
        referencia: x.referencia,
        nombre: x.nombre,
        cantidad: Number(x.cantidad || 0),
        precio_compra: Number(x.precio_compra || 0),
        precio_venta: Number(x.precio_venta || 0),
      }));
      window.renderVentaItems();
    }
  }

  if (typeof originalEdit === 'function') {
    window.editarVenta = async function(id) {
      await originalEdit(id);
      try {
        const detail = await loadDetail(id);
        syncFormFromDetail(detail);
        await fillClients(detail.venta?.cliente_id);
      } catch (error) {
        if (typeof window.toast === 'function') window.toast(error.message, 'error');
      }
    };
  }

  if (typeof originalNew === 'function') {
    window.openModalVenta = async function() {
      await originalNew();
      try {
        await fillClients(null);
        const select = document.getElementById('vf-cliente');
        if (select) select.value = '';
        const date = document.getElementById('vf-fecha');
        if (date && !date.value) date.value = new Date().toISOString().slice(0, 10);
      } catch (error) {
        if (typeof window.toast === 'function') window.toast(`No se pudieron cargar los clientes: ${error.message}`, 'error');
      }
    };
  }

})();
