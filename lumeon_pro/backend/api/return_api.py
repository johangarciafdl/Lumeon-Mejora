from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.return_service import ReturnError, return_sale

return_api = Blueprint("return_api", __name__, url_prefix="/api/v2/devoluciones")


@return_api.post("/<int:sale_id>")
def create_return(sale_id: int):
    try:
        actor = current_actor()
        require(actor, "return_sale")
        data = request.get_json(silent=True) or {}
        conn = get_db()
        try:
            result = return_sale(
                conn,
                sale_id=sale_id,
                user_id=actor.id,
                idempotency_key=data.get("idempotency_key") or request.headers.get("Idempotency-Key"),
                reason=str(data.get("motivo") or ""),
            )
            conn.commit()
            return jsonify({"ok": True, **result})
        finally:
            conn.close()
    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ReturnError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
