from __future__ import annotations

from flask import Blueprint, jsonify

from core.db import get_db
from services.provider_health import get_provider_status

system_api = Blueprint("system_api", __name__, url_prefix="/api/v2/system")


@system_api.get("/status")
def status():
    database_ok = False
    conn = None
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        database_ok = True
    except Exception:
        database_ok = False
    finally:
        if conn:
            conn.close()
    return jsonify({
        "ok": database_ok,
        "database": "ok" if database_ok else "error",
        "providers": [p.__dict__ for p in get_provider_status()],
    }), (200 if database_ok else 503)
