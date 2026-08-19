from __future__ import annotations

import argparse
import shutil
import sqlite3
from pathlib import Path

PLACEHOLDER_DOCUMENTS = {"0", "00", "000", "0000", "00000", "000000", "0000000"}

SALE_EXTRA_COLUMNS = {
    "pdf_enviado": "INTEGER",
    "ciclo": "TEXT",
    "fecha_inicio_ciclo": "TEXT",
    "fecha_fin_ciclo": "TEXT",
    "total_abonado": "REAL",
    "saldo_pendiente": "REAL",
    "estado_pago": "TEXT",
    "num_ediciones": "INTEGER",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate legacy Lumeon SQLite data into V2 SQLite.")
    parser.add_argument("--source", required=True, type=Path, help="Legacy SQLite database")
    parser.add_argument("--target", required=True, type=Path, help="V2 SQLite database")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually modify the target. Without this flag the script only validates and reports.",
    )
    return parser.parse_args()


def connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def ensure_sale_history_columns(conn: sqlite3.Connection) -> None:
    existing = table_columns(conn, "ventas")
    for name, sql_type in SALE_EXTRA_COLUMNS.items():
        if name not in existing:
            conn.execute(f'ALTER TABLE ventas ADD COLUMN "{name}" {sql_type}')


def ensure_legacy_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS legacy_pedidos (
            id INTEGER PRIMARY KEY,
            numero_pedido TEXT NOT NULL,
            proveedor TEXT,
            venta_id INTEGER,
            fecha_pedido TEXT,
            fecha_entrega TEXT,
            fecha_cancelacion TEXT,
            total REAL,
            estado TEXT,
            notas TEXT,
            ciclo TEXT,
            creado_en TEXT,
            cliente_nombre TEXT
        );

        CREATE TABLE IF NOT EXISTS legacy_pedido_items (
            id INTEGER PRIMARY KEY,
            pedido_id INTEGER NOT NULL,
            referencia TEXT,
            nombre TEXT,
            cantidad INTEGER,
            precio_compra REAL,
            subtotal REAL
        );

        CREATE TABLE IF NOT EXISTS legacy_abonos (
            id INTEGER PRIMARY KEY,
            venta_id INTEGER NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT,
            metodo TEXT,
            notas TEXT,
            usuario_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS legacy_devoluciones (
            id INTEGER PRIMARY KEY,
            venta_id INTEGER,
            numero_factura TEXT,
            cliente_nombre TEXT,
            referencia TEXT,
            nombre TEXT,
            cantidad INTEGER,
            motivo TEXT,
            fecha TEXT,
            estado TEXT
        );
        """
    )


def normalize_document(value: object) -> str | None:
    value = "" if value is None else str(value).strip()
    if not value or value in PLACEHOLDER_DOCUMENTS:
        return None
    return value


def require_no_collisions(old: sqlite3.Connection, new: sqlite3.Connection) -> None:
    old_product_refs = {r["referencia"] for r in old.execute("SELECT referencia FROM productos")}
    new_product_refs = {r["referencia"] for r in new.execute("SELECT referencia FROM productos")}
    collisions = sorted(old_product_refs & new_product_refs)
    if collisions:
        raise RuntimeError(f"Referencias de producto ya existentes en destino: {collisions}")

    old_invoices = {r["numero_factura"] for r in old.execute("SELECT numero_factura FROM ventas")}
    new_invoices = {r["numero_factura"] for r in new.execute("SELECT numero_factura FROM ventas")}
    collisions = sorted(old_invoices & new_invoices)
    if collisions:
        raise RuntimeError(f"Facturas ya existentes en destino: {collisions}")


def insert_or_map_users(old: sqlite3.Connection, new: sqlite3.Connection, user_map: dict[int, int]) -> None:
    for row in old.execute("SELECT * FROM usuarios ORDER BY id"):
        existing = new.execute(
            "SELECT id, rol, activo FROM usuarios WHERE username=?",
            (row["username"],),
        ).fetchone()
        if existing:
            user_map[row["id"]] = int(existing["id"])
            continue
        cur = new.execute(
            """INSERT INTO usuarios(username,password,email,nombre,rol,activo,creado_en)
               VALUES (?,?,?,?,?,?,?)""",
            (
                row["username"],
                row["password"],
                row["email"],
                row["nombre"],
                row["rol"] or "vendedor",
                row["activo"] if row["activo"] is not None else 1,
                row["creado_en"],
            ),
        )
        user_map[row["id"]] = int(cur.lastrowid)


def migrate_customers(old: sqlite3.Connection, new: sqlite3.Connection, customer_map: dict[int, int]) -> None:
    for row in old.execute("SELECT * FROM clientes ORDER BY id"):
        document = normalize_document(row["documento"])
        if document:
            existing = new.execute("SELECT id FROM clientes WHERE documento=?", (document,)).fetchone()
            if existing:
                customer_map[row["id"]] = int(existing["id"])
                continue
        cur = new.execute(
            """INSERT INTO clientes(nombre,documento,telefono,direccion,email,ciudad,creado_en)
               VALUES (?,?,?,?,?,?,?)""",
            (
                row["nombre"],
                document,
                row["telefono"] or None,
                row["direccion"] or None,
                (row["email"] or "").strip().lower() or None,
                row["ciudad"] or None,
                row["creado_en"],
            ),
        )
        customer_map[row["id"]] = int(cur.lastrowid)


def migrate_products(old: sqlite3.Connection, new: sqlite3.Connection, product_map: dict[int, int]) -> None:
    for row in old.execute("SELECT * FROM productos ORDER BY id"):
        existing = new.execute("SELECT id FROM productos WHERE referencia=?", (row["referencia"],)).fetchone()
        if existing:
            product_map[row["id"]] = int(existing["id"])
            continue
        cur = new.execute(
            """INSERT INTO productos(nombre,referencia,descripcion,categoria,precio_compra,precio_venta,stock,stock_minimo,creado_en)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                row["nombre"],
                row["referencia"],
                row["descripcion"],
                row["categoria"] or "General",
                row["precio_compra"] or 0,
                row["precio_venta"] or 0,
                row["stock"] or 0,
                row["stock_minimo"] or 0,
                row["creado_en"],
            ),
        )
        product_map[row["id"]] = int(cur.lastrowid)


def migrate_sales(
    old: sqlite3.Connection,
    new: sqlite3.Connection,
    customer_map: dict[int, int],
    user_map: dict[int, int],
    sale_map: dict[int, int],
) -> None:
    for row in old.execute("SELECT * FROM ventas ORDER BY id"):
        existing = new.execute("SELECT id FROM ventas WHERE numero_factura=?", (row["numero_factura"],)).fetchone()
        if existing:
            sale_map[row["id"]] = int(existing["id"])
            continue

        old_customer_id = row["cliente_id"]
        new_customer_id = customer_map.get(old_customer_id) if old_customer_id is not None else None
        new_user_id = user_map.get(row["usuario_id"]) if row["usuario_id"] is not None else None

        cur = new.execute(
            """INSERT INTO ventas(
                    numero_factura,idempotency_key,cliente_id,cliente_nombre,cliente_email,cliente_telefono,
                    fecha,forma_pago,subtotal,total,ganancia,estado,notas,usuario_id,
                    pdf_enviado,ciclo,fecha_inicio_ciclo,fecha_fin_ciclo,total_abonado,saldo_pendiente,
                    estado_pago,num_ediciones
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["numero_factura"],
                f"legacy-sale-{row['id']}",
                new_customer_id,
                row["cliente_nombre"],
                row["cliente_email"],
                row["cliente_telefono"],
                row["fecha"],
                row["forma_pago"] or "Contado",
                row["subtotal"] or 0,
                row["total"] or 0,
                row["ganancia"] or 0,
                row["estado"] or "Pendiente",
                row["notas"],
                new_user_id,
                row["pdf_enviado"],
                row["ciclo"],
                row["fecha_inicio_ciclo"],
                row["fecha_fin_ciclo"],
                row["total_abonado"],
                row["saldo_pendiente"],
                row["estado_pago"],
                row["num_ediciones"],
            ),
        )
        sale_map[row["id"]] = int(cur.lastrowid)


def migrate_sale_items(old: sqlite3.Connection, new: sqlite3.Connection, product_map: dict[int, int], sale_map: dict[int, int]) -> None:
    for row in old.execute("SELECT * FROM venta_items ORDER BY id"):
        new_sale_id = sale_map[row["venta_id"]]
        exists = new.execute(
            "SELECT id FROM venta_items WHERE venta_id=? AND referencia=? AND idempotency_key IS NULL"
            if "idempotency_key" in table_columns(new, "venta_items") else
            "SELECT id FROM venta_items WHERE venta_id=? AND referencia=?",
            (new_sale_id, row["referencia"]),
        ).fetchone()
        if exists:
            continue
        new.execute(
            """INSERT INTO venta_items(venta_id,producto_id,referencia,nombre,cantidad,precio_compra,precio_venta,subtotal,ganancia)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                new_sale_id,
                product_map.get(row["producto_id"]) if row["producto_id"] is not None else None,
                row["referencia"],
                row["nombre"],
                row["cantidad"] or 0,
                row["precio_compra"] or 0,
                row["precio_venta"] or 0,
                row["subtotal"] or 0,
                row["ganancia"] or 0,
            ),
        )


def migrate_legacy_tables(old: sqlite3.Connection, new: sqlite3.Connection, sale_map: dict[int, int], user_map: dict[int, int]) -> None:
    ensure_legacy_tables(new)

    for row in old.execute("SELECT * FROM pedidos ORDER BY id"):
        new.execute(
            """INSERT OR REPLACE INTO legacy_pedidos
            (id,numero_pedido,proveedor,venta_id,fecha_pedido,fecha_entrega,fecha_cancelacion,total,estado,notas,ciclo,creado_en,cliente_nombre)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["id"], row["numero_pedido"], row["proveedor"], sale_map.get(row["venta_id"]) if row["venta_id"] else None,
                row["fecha_pedido"], row["fecha_entrega"], row["fecha_cancelacion"], row["total"], row["estado"],
                row["notas"], row["ciclo"], row["creado_en"], row["cliente_nombre"],
            ),
        )

    for row in old.execute("SELECT * FROM pedido_items ORDER BY id"):
        new.execute(
            """INSERT OR REPLACE INTO legacy_pedido_items
            (id,pedido_id,referencia,nombre,cantidad,precio_compra,subtotal)
            VALUES (?,?,?,?,?,?,?)""",
            (row["id"], row["pedido_id"], row["referencia"], row["nombre"], row["cantidad"], row["precio_compra"], row["subtotal"]),
        )

    for row in old.execute("SELECT * FROM abonos ORDER BY id"):
        new.execute(
            """INSERT OR REPLACE INTO legacy_abonos
            (id,venta_id,monto,fecha,metodo,notas,usuario_id)
            VALUES (?,?,?,?,?,?,?)""",
            (row["id"], sale_map[row["venta_id"]], row["monto"], row["fecha"], row["metodo"], row["notas"], user_map.get(row["usuario_id"]) if row["usuario_id"] else None),
        )

    for row in old.execute("SELECT * FROM devoluciones ORDER BY id"):
        new.execute(
            """INSERT OR REPLACE INTO legacy_devoluciones
            (id,venta_id,numero_factura,cliente_nombre,referencia,nombre,cantidad,motivo,fecha,estado)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (row["id"], sale_map.get(row["venta_id"]) if row["venta_id"] else None, row["numero_factura"], row["cliente_nombre"], row["referencia"], row["nombre"], row["cantidad"], row["motivo"], row["fecha"], row["estado"]),
        )


def migrate(source: Path, target: Path, apply: bool) -> None:
    if source.resolve() == target.resolve():
        raise RuntimeError("Source y target no pueden ser la misma base")

    if apply:
        backup = target.with_suffix(target.suffix + ".pre-legacy-migration.bak")
        shutil.copy2(target, backup)
        print(f"BACKUP DESTINO: {backup}")

    old = connect(source)
    new = connect(target)
    try:
        if not apply:
            # Validate against the current destination without mutating it.
            require_no_collisions(old, new)
            print("DRY-RUN: no se modificará el destino")
            print("usuarios:", count(old, "usuarios"))
            print("clientes:", count(old, "clientes"))
            print("productos:", count(old, "productos"))
            print("ventas:", count(old, "ventas"))
            print("venta_items:", count(old, "venta_items"))
            print("placeholders_documento:", old.execute("SELECT COUNT(*) FROM clientes WHERE TRIM(COALESCE(documento,'')) IN ('0','00','000','0000','00000','000000','0000000')").fetchone()[0])
            print("ventas_cliente_huerfano:", old.execute("SELECT COUNT(*) FROM ventas v LEFT JOIN clientes c ON c.id=v.cliente_id WHERE v.cliente_id IS NOT NULL AND c.id IS NULL").fetchone()[0])
            print("pedidos_venta_huerfana:", old.execute("SELECT COUNT(*) FROM pedidos p LEFT JOIN ventas v ON v.id=p.venta_id WHERE p.venta_id IS NOT NULL AND v.id IS NULL").fetchone()[0])
            return

        ensure_sale_history_columns(new)
        require_no_collisions(old, new)

        user_map: dict[int, int] = {}
        customer_map: dict[int, int] = {}
        product_map: dict[int, int] = {}
        sale_map: dict[int, int] = {}

        insert_or_map_users(old, new, user_map)
        migrate_customers(old, new, customer_map)
        migrate_products(old, new, product_map)
        migrate_sales(old, new, customer_map, user_map, sale_map)
        migrate_sale_items(old, new, product_map, sale_map)
        migrate_legacy_tables(old, new, sale_map, user_map)

        new.commit()
        print("MIGRACIÓN APLICADA")
        print("map usuarios:", user_map)
        print("map clientes:", len(customer_map))
        print("map productos:", len(product_map))
        print("map ventas:", len(sale_map))
    except Exception:
        new.rollback()
        raise
    finally:
        old.close()
        new.close()


def main() -> None:
    args = parse_args()
    migrate(args.source, args.target, args.apply)


if __name__ == "__main__":
    main()
