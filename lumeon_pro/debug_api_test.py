import json
import urllib.request
import urllib.error
import http.cookiejar
import random

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
headers = {'Content-Type': 'application/json'}

login_data = json.dumps({'username': 'admin1', 'password': 'admin123'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:5000/api/login', data=login_data, headers=headers, method='POST')
try:
    res = opener.open(req, timeout=10)
    print('LOGIN', res.getcode())
    print(res.read().decode())
except Exception as e:
    print('LOGIN ERROR', e)
    raise

venta = {
    'numero_factura': 'TEST-' + str(random.randint(10000, 99999)),
    'cliente_nombre': 'Prueba',
    'cliente_email': 'test@example.com',
    'cliente_telefono': '1234567890',
    'items': [
        {'referencia': 'TEST', 'nombre': 'Producto de prueba', 'cantidad': 1, 'precio_venta': 10000, 'precio_compra': 5000}
    ],
    'fecha': '2026-04-10',
    'forma_pago': 'Contado',
    'estado': 'Pendiente',
    'notas': 'Prueba automatizada'
}
venta_data = json.dumps(venta).encode('utf-8')
req2 = urllib.request.Request('http://127.0.0.1:5000/api/ventas', data=venta_data, headers=headers, method='POST')
try:
    res2 = opener.open(req2, timeout=30)
    print('VENTA', res2.getcode())
    print(res2.read().decode())
except urllib.error.HTTPError as e:
    print('VENTA HTTPERR', e.code)
    print(e.read().decode())
except Exception as e:
    print('VENTA ERROR', e)
