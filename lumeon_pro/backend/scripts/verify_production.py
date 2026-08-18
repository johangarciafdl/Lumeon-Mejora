"""Read-only production checks for PythonAnywhere/Supabase.

Run from lumeon_pro/backend after installing requirements and creating .env:
    python scripts/verify_production.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")


def main() -> int:
    required = ["SECRET_KEY", "DATABASE_URL"]
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        print("FAIL: faltan variables:", ", ".join(missing))
        return 1

    url = os.getenv("DATABASE_URL", "")
    print("DATABASE_URL:", "PostgreSQL" if url.startswith(("postgresql://", "postgres://")) else "SQLite/otro")
    print("FLASK_ENV:", os.getenv("FLASK_ENV", ""))
    print("WHATSAPP_PROVIDER:", os.getenv("WHATSAPP_PROVIDER", "callmebot"))
    print("CALLMEBOT configurado:", "sí" if os.getenv("CALLMEBOT_API_KEY", "").strip() and os.getenv("CALLMEBOT_DEFAULT_PHONE", "").strip() else "no")

    from core.db import get_db  # noqa: E402

    conn = None
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        print("PASS: conexión a base de datos")

        checks = {
            "usuarios": "SELECT 1 FROM usuarios LIMIT 1",
            "clientes": "SELECT 1 FROM clientes LIMIT 1",
            "productos": "SELECT 1 FROM productos LIMIT 1",
            "ventas": "SELECT 1 FROM ventas LIMIT 1",
            "venta_items": "SELECT 1 FROM venta_items LIMIT 1",
            "assistant_sessions": "SELECT 1 FROM assistant_sessions LIMIT 1",
            "audit_log": "SELECT 1 FROM audit_log LIMIT 1",
            "sale_idempotency": "SELECT 1 FROM sale_idempotency LIMIT 1",
            "sale_returns": "SELECT 1 FROM sale_returns LIMIT 1",
            "invoice_deliveries": "SELECT 1 FROM invoice_deliveries LIMIT 1",
        }
        failed = False
        for name, sql in checks.items():
            try:
                conn.execute(sql).fetchone()
                print(f"PASS: tabla {name}")
            except Exception as exc:
                failed = True
                print(f"FAIL: tabla {name}: {exc}")

        if failed:
            return 2
        print("PASS: esquema de producción básico completo")
        return 0
    except Exception as exc:
        print("FAIL: conexión/configuración:", exc)
        return 3
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
