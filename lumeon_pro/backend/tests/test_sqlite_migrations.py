import sqlite3

from services.migration_service import apply_pending


def test_sqlite_migrations_build_complete_schema(tmp_path):
    db_path = tmp_path / "lumeon-test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        first = apply_pending(conn)
        second = apply_pending(conn)

        assert first
        assert second == []

        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {
            "usuarios",
            "clientes",
            "productos",
            "ventas",
            "venta_items",
            "assistant_sessions",
            "audit_log",
            "venta_devoluciones",
            "venta_devolucion_items",
            "invoice_deliveries",
            "schema_migrations",
        }.issubset(tables)

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(ventas)").fetchall()
        }
        assert "idempotency_key" in columns
    finally:
        conn.close()
