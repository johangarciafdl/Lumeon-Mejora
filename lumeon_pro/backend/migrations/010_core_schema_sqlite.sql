CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    nombre TEXT,
    rol TEXT NOT NULL DEFAULT 'vendedor',
    activo INTEGER NOT NULL DEFAULT 1,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    documento TEXT,
    telefono TEXT,
    direccion TEXT,
    email TEXT,
    ciudad TEXT,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_clientes_documento_nonempty ON clientes(documento) WHERE documento IS NOT NULL AND documento <> '';
CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre);
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    referencia TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    categoria TEXT NOT NULL DEFAULT 'General',
    precio_compra REAL NOT NULL DEFAULT 0,
    precio_venta REAL NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura TEXT NOT NULL UNIQUE,
    cliente_id INTEGER REFERENCES clientes(id),
    cliente_nombre TEXT,
    cliente_email TEXT,
    cliente_telefono TEXT,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    forma_pago TEXT NOT NULL DEFAULT 'Contado',
    subtotal REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    ganancia REAL NOT NULL DEFAULT 0,
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    notas TEXT,
    usuario_id INTEGER REFERENCES usuarios(id)
);
CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON ventas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);

CREATE TABLE IF NOT EXISTS venta_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES productos(id),
    referencia TEXT,
    nombre TEXT,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_compra REAL NOT NULL DEFAULT 0,
    precio_venta REAL NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL DEFAULT 0,
    ganancia REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_venta_items_venta ON venta_items(venta_id);
CREATE INDEX IF NOT EXISTS idx_venta_items_producto ON venta_items(producto_id);

CREATE TABLE IF NOT EXISTS assistant_sessions (
    session_id TEXT PRIMARY KEY,
    pending_intent TEXT,
    pending_payload TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_created ON audit_log(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id, created_at);
