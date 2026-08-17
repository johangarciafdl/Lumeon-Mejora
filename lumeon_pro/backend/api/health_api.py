from flask import Blueprint, jsonify
from core.db import get_db

health_api = Blueprint("health_api", __name__)

@health_api.get("/health")
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"ok": True, "status": "healthy", "service": "lumeon"})
    except Exception:
        return jsonify({"ok": False, "status": "unhealthy", "service": "lumeon"}), 503
