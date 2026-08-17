from services.assistant_parser import parse_create_customer, parse_create_product


def test_parse_customer_command():
    data = parse_create_customer("registrar cliente nombre: Carlos Pérez, telefono: 3045201946, correo: carlos@example.com")
    assert data["nombre"] == "Carlos Pérez"
    assert data["telefono"] == "3045201946"
    assert data["email"] == "carlos@example.com"


def test_parse_product_command():
    data = parse_create_product("registrar producto nombre: Café, referencia: CAF-001, stock: 10, precio_venta: 12000")
    assert data["nombre"] == "Café"
    assert data["referencia"] == "CAF-001"
    assert data["stock"] == "10"
    assert data["precio_venta"] == "12000"
