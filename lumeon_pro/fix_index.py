content = open('frontend/index.html', encoding='utf-8').read()

# 1. Fix número de factura automático - consulta el backend
viejo_fac = """async function openModalVenta(){
  ventaItems = [];
  renderVentaItems();
  document.getElementById('vf-num').value = `FAC-${String(Date.now()).slice(-4)}`;
  document.getElementById('vf-fecha').value = new Date().toISOString().split('T')[0];
  document.getElementById('vf-notas').value = '';
  document.getElementById('vf-email').value = '';
  document.getElementById('vf-tel').value = '';
  // Load clientes
  const cls = await fetch(`${API}/clientes`).then(r=>r.json());
  document.getElementById('vf-cliente').innerHTML = '<option value="">-- Sin cliente --</option>' + cls.map(c=>`<option value="${c.id}">${c.nombre}</option>`).join('');
  openModal('modal-venta');
}"""

nuevo_fac = """async function openModalVenta(){
  ventaItems = [];
  renderVentaItems();
  // Generar número de factura automático consultando el último del backend
  try {
    const ventas = await fetch(`${API}/ventas`).then(r=>r.json());
    let maxNum = 0;
    ventas.forEach(v => {
      const match = v.numero_factura.match(/FAC-(\d+)/);
      if(match) maxNum = Math.max(maxNum, parseInt(match[1]));
    });
    document.getElementById('vf-num').value = `FAC-${String(maxNum + 1).padStart(4,'0')}`;
  } catch(e) {
    document.getElementById('vf-num').value = `FAC-${String(Date.now()).slice(-6)}`;
  }
  document.getElementById('vf-fecha').value = new Date().toISOString().split('T')[0];
  document.getElementById('vf-notas').value = '';
  document.getElementById('vf-email').value = '';
  document.getElementById('vf-tel').value = '';
  document.getElementById('vf-pago').value = 'Contado';
  document.getElementById('vf-estado').value = 'Pendiente';
  // Load clientes
  const cls = await fetch(`${API}/clientes`).then(r=>r.json());
  document.getElementById('vf-cliente').innerHTML = '<option value="">-- Sin cliente --</option>' + cls.map(c=>`<option value="${c.id}">${c.nombre}</option>`).join('');
  openModal('modal-venta');
}"""

# 2. Fix número de pedido automático también
viejo_ped = """function openModalPedido(){
  pedidoItems=[];
  renderPedidoItems();
  document.getElementById('pp-num').value=`PED-${String(Date.now()).slice(-4)}`;
  document.getElementById('pp-fecha').value=new Date().toISOString().split('T')[0];
  openModal('modal-pedido');
}"""

nuevo_ped = """async function openModalPedido(){
  pedidoItems=[];
  renderPedidoItems();
  // Generar número de pedido automático
  try {
    const pedidos = await fetch(`${API}/pedidos`).then(r=>r.json());
    let maxNum = 0;
    pedidos.forEach(p => {
      const match = p.numero_pedido.match(/PED-(\d+)/);
      if(match) maxNum = Math.max(maxNum, parseInt(match[1]));
    });
    document.getElementById('pp-num').value = `PED-${String(maxNum + 1).padStart(4,'0')}`;
  } catch(e) {
    document.getElementById('pp-num').value = `PED-${String(Date.now()).slice(-6)}`;
  }
  document.getElementById('pp-fecha').value=new Date().toISOString().split('T')[0];
  document.getElementById('pp-ciclo').value='';
  document.getElementById('pp-notas').value='';
  openModal('modal-pedido');
}"""

# 3. Fix CSS background-clip
viejo_css = 'background:linear-gradient(135deg,var(--purple2),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent'
nuevo_css = 'background:linear-gradient(135deg,var(--purple2),var(--pink));background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent'

fixed = content
cambios = 0

if viejo_fac in fixed:
    fixed = fixed.replace(viejo_fac, nuevo_fac)
    cambios += 1
    print('✅ Número de factura automático corregido')
else:
    print('⚠️  No se encontró openModalVenta - revisa manualmente')

if viejo_ped in fixed:
    fixed = fixed.replace(viejo_ped, nuevo_ped)
    cambios += 1
    print('✅ Número de pedido automático corregido')
else:
    print('⚠️  No se encontró openModalPedido - revisa manualmente')

if viejo_css in fixed:
    fixed = fixed.replace(viejo_css, nuevo_css)
    cambios += 1
    print('✅ CSS background-clip corregido')
else:
    print('ℹ️  CSS ya estaba corregido')

open('frontend/index.html', 'w', encoding='utf-8').write(fixed)
print(f'\n✅ index.html actualizado con {cambios} correcciones')
