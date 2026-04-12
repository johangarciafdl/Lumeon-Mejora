content = open('backend/app.py', encoding='utf-8').read()

# 1. Revertir imports
viejo_imports = '''import sqlite3, os, smtplib, io, re, threading
try:
    import pg8000
    USE_POSTGRES = True
except ImportError:
    USE_POSTGRES = False'''

nuevo_imports = 'import sqlite3, os, smtplib, io, re, threading'

# 2. Revertir DATABASE_URL
viejo_db = '''DB = os.path.join(os.path.dirname(__file__), "database.db")
DATABASE_URL = os.getenv("DATABASE_URL", "")'''

nuevo_db = 'DB = os.path.join(os.path.dirname(__file__), "database.db")'

# 3. Revertir get_db
viejo_getdb = '''def get_db():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url and database_url.startswith("postgresql"):
        import pg8000.native
        import urllib.parse as urlparse
        result = urlparse.urlparse(database_url)
        conn = pg8000.dbapi.connect(
            host=result.hostname,
            port=result.port or 5432,
            database=result.path[1:],
            user=result.username,
            password=result.password,
            ssl_context=True
        )
        return conn
    else:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        return conn

def is_postgres():
    url = os.getenv("DATABASE_URL", "")
    return url and url.startswith("postgresql")

def row_to_dict(row, cursor=None):
    if row is None:
        return None
    if hasattr(row, 'keys'):
        return dict(row)
    if cursor:
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    return row'''

nuevo_getdb = '''def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn'''

# 4. Revertir init_db - quitar el bloque de postgres
viejo_init_check = '''    database_url = os.getenv("DATABASE_URL", "")
    if database_url and database_url.startswith("postgresql"):
        _init_postgres(conn, c)
    else:
        _init_sqlite(conn, c)

def _init_postgres(conn, c):
    statements = ["""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT NOT NULL,
        nombre TEXT,
        rol TEXT DEFAULT 'admin',
        activo INTEGER DEFAULT 1,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""","""
    CREATE TABLE IF NOT EXISTS productos (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        referencia TEXT UNIQUE NOT NULL,
        descripcion TEXT,
        categoria TEXT DEFAULT 'General',
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        stock_minimo INTEGER DEFAULT 5,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""","""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        direccion TEXT,
        email TEXT,
        ciudad TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""","""
    CREATE TABLE IF NOT EXISTS ventas (
        id SERIAL PRIMARY KEY,
        numero_factura TEXT UNIQUE NOT NULL,
        cliente_id INTEGER,
        cliente_nombre TEXT,
        cliente_email TEXT,
        cliente_telefono TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        forma_pago TEXT DEFAULT 'Contado',
        subtotal REAL DEFAULT 0,
        total REAL DEFAULT 0,
        ganancia REAL DEFAULT 0,
        estado TEXT DEFAULT 'Pendiente',
        notas TEXT,
        pdf_enviado INTEGER DEFAULT 0,
        usuario_id INTEGER
    )""","""
    CREATE TABLE IF NOT EXISTS venta_items (
        id SERIAL PRIMARY KEY,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER DEFAULT 1,
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        subtotal REAL DEFAULT 0,
        ganancia REAL DEFAULT 0
    )""","""
    CREATE TABLE IF NOT EXISTS pedidos (
        id SERIAL PRIMARY KEY,
        numero_pedido TEXT UNIQUE NOT NULL,
        proveedor TEXT DEFAULT 'Natura',
        venta_id INTEGER,
        fecha_pedido TEXT,
        fecha_entrega TEXT,
        fecha_cancelacion TEXT,
        total REAL DEFAULT 0,
        estado TEXT DEFAULT 'Pendiente',
        notas TEXT,
        ciclo TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )""","""
    CREATE TABLE IF NOT EXISTS pedido_items (
        id SERIAL PRIMARY KEY,
        pedido_id INTEGER NOT NULL,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER DEFAULT 1,
        precio_compra REAL DEFAULT 0,
        subtotal REAL DEFAULT 0
    )""","""
    CREATE TABLE IF NOT EXISTS devoluciones (
        id SERIAL PRIMARY KEY,
        venta_id INTEGER,
        numero_factura TEXT,
        cliente_nombre TEXT,
        referencia TEXT,
        nombre TEXT,
        cantidad INTEGER DEFAULT 1,
        motivo TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'Procesada'
    )"""]
    for stmt in statements:
        c.execute(stmt)
    conn.commit()
    print("✅ Tablas PostgreSQL creadas/verificadas")

def _init_sqlite(conn, c):
    c.executescript("""'''

nuevo_init_check = '    c.executescript("""'

fixed = content
cambios = 0

if viejo_imports in fixed:
    fixed = fixed.replace(viejo_imports, nuevo_imports)
    cambios += 1
    print('✅ imports revertidos')
else:
    print('⚠️  imports no encontrados')

if viejo_db in fixed:
    fixed = fixed.replace(viejo_db, nuevo_db)
    cambios += 1
    print('✅ DATABASE_URL removido')

if viejo_getdb in fixed:
    fixed = fixed.replace(viejo_getdb, nuevo_getdb)
    cambios += 1
    print('✅ get_db revertido a SQLite')
else:
    print('⚠️  get_db no encontrado')

if viejo_init_check in fixed:
    fixed = fixed.replace(viejo_init_check, nuevo_init_check)
    cambios += 1
    print('✅ init_db revertido a SQLite')
else:
    print('⚠️  init_db postgres no encontrado')

open('backend/app.py', 'w', encoding='utf-8').write(fixed)
print(f'\n✅ app.py revertido con {cambios} cambios - listo para Railway')
