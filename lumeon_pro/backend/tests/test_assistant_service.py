import sqlite3

from services.assistant_service import AssistantService


def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE clientes (id INTEGER PRIMARY KEY, nombre TEXT, documento TEXT, telefono TEXT, email TEXT, ciudad TEXT);
    CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT, referencia TEXT, stock INTEGER, stock_minimo INTEGER, precio_venta REAL);
    INSERT INTO clientes VALUES (1,'Juan Perez','123','3045201946','juan@example.com','Medellín');
    INSERT INTO productos VALUES (1,'Cafe Lumeon','CAF-01',4,5,10000);
    """)
    return conn


def test_search_customer_is_read_only():
    conn = db()
    service = AssistantService(conn)
    intent = service.parse('buscar cliente Juan')
    result = service.execute_read(intent)
    assert intent.requires_confirmation is False
    assert result['results'][0]['nombre'] == 'Juan Perez'


def test_low_stock():
    conn = db()
    service = AssistantService(conn)
    result = service.execute_read(service.parse('stock bajo'))
    assert result['results'][0]['referencia'] == 'CAF-01'


def test_mutation_requires_confirmation():
    intent = AssistantService().parse('registrar cliente')
    assert intent.name == 'create_customer'
    assert intent.requires_confirmation is True
