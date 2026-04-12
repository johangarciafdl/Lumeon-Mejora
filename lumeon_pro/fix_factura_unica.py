content = open('frontend/index.html', encoding='utf-8').read()

# Fix: usar timestamp completo para garantizar unicidad
viejo = """  // Generar número de factura automático consultando el último del backend
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
  }"""

nuevo = """  // Generar número de factura automático único
  try {
    const ventas = await fetch(`${API}/ventas`).then(r=>r.json());
    let maxNum = 0;
    ventas.forEach(v => {
      const match = v.numero_factura.match(/FAC-(\d+)/);
      if(match) maxNum = Math.max(maxNum, parseInt(match[1]));
    });
    const siguiente = maxNum + 1;
    document.getElementById('vf-num').value = `FAC-${String(siguiente).padStart(4,'0')}-${Date.now().toString().slice(-4)}`;
  } catch(e) {
    document.getElementById('vf-num').value = `FAC-${Date.now()}`;
  }"""

if viejo in content:
    fixed = content.replace(viejo, nuevo)
    open('frontend/index.html', 'w', encoding='utf-8').write(fixed)
    print('✅ Número de factura único corregido')
else:
    print('⚠️  No encontrado')
    # Buscar la línea actual
    for i, line in enumerate(content.split('\n'), 1):
        if 'FAC-' in line and 'padStart' in line:
            print(f'  Linea {i}: {line.strip()}')
