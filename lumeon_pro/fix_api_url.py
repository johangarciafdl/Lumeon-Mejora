content = open('frontend/index.html', encoding='utf-8').read()

viejo = "const API = 'http://127.0.0.1:5000/api';"
nuevo = "const API = window.location.origin + '/api';"

if viejo in content:
    fixed = content.replace(viejo, nuevo)
    open('frontend/index.html', 'w', encoding='utf-8').write(fixed)
    print('✅ URL del API corregida para produccion')
else:
    print('⚠️  No se encontro la linea, buscando...')
    for i, line in enumerate(content.split('\n'), 1):
        if 'API' in line and '127' in line:
            print(f'  Linea {i}: {line.strip()}')
