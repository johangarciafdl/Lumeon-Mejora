from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.auth_service import AuthenticationError, current_actor

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/v2/auth")


@auth_api.get("/me")
def me():
    try:
        actor = current_actor()
        return jsonify({"ok": True, "authenticated": True, "user_id": actor.id, "role": actor.role})
    except AuthenticationError:
        return jsonify({"ok": True, "authenticated": False}), 200


@auth_api.post("/session")
def set_session():
    """Bridge endpoint for an already authenticated legacy session.

    It deliberately accepts only an internal numeric user id and role from the
    existing application session; it does not implement password authentication.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    role = str(data.get("role") or "vendedor")
    if not isinstance(user_id, int) or user_id <= 0:
        return jsonify({"ok": False, "error": "user_id inválido"}), 400
    if role not in {"admin", "vendedor", "cajero", "almacen"}:
        return jsonify({"ok": False, "error": "rol inválido"}), 400
    session["user_id"] = user_id
    session["role"] = role
    session.permanent = True
    return jsonify({"ok": True, "authenticated": True, "user_id": user_id, "role": role})


@auth_api.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})
