from __future__ import annotations

import hmac
import os

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/v2/auth")


def _is_password_match(stored: str, supplied: str) -> bool:
    stored = str(stored or "")
    supplied = str(supplied or "")
    if stored.startswith(("scrypt:", "pbkdf2:", "argon2:")):
        try:
            return check_password_hash(stored, supplied)
        except ValueError:
            return False
    return hmac.compare_digest(stored, supplied)


def _bootstrap_admin(conn, username: str, password: str, email: str):
    configured_user = os.getenv("ADMIN_USERNAME", "").strip()
    configured_password = os.getenv("ADMIN_PASSWORD", "")
    configured_email = os.getenv("ADMIN_EMAIL", "admin@lumeon.local").strip() or "admin@lumeon.local"
    if not configured_user or not configured_password:
        return None
    if not hmac.compare_digest(username, configured_user) or not hmac.compare_digest(password, configured_password):
        return None

    row = conn.execute("SELECT id, username, password, email, nombre, rol, activo FROM usuarios WHERE username=?", (username,)).fetchone()
    password_hash = generate_password_hash(configured_password)
    if row is None:
        conn.execute(
            "INSERT INTO usuarios(username, password, email, nombre, rol, activo) VALUES (?, ?, ?, ?, ?, ?)",
            (username, password_hash, configured_email, "Administrador", "admin", True),
        )
        conn.commit()
        row = conn.execute("SELECT id, username, password, email, nombre, rol, activo FROM usuarios WHERE username=?", (username,)).fetchone()
    elif str(row["rol"]) != "admin" or not bool(row["activo"]):
        return None
    else:
        conn.execute("UPDATE usuarios SET password=?, email=?, rol='admin', activo=TRUE WHERE id=?", (password_hash, configured_email, row["id"]))
        conn.commit()
        row = conn.execute("SELECT id, username, password, email, nombre, rol, activo FROM usuarios WHERE id=?", (row["id"],)).fetchone()
    return row


@auth_api.get("/me")
def me():
    try:
        actor = current_actor()
        return jsonify({"ok": True, "authenticated": True, "user_id": actor.id, "role": actor.role})
    except AuthenticationError:
        return jsonify({"ok": True, "authenticated": False}), 200


@auth_api.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    if not username or not password:
        return jsonify({"ok": False, "error": "Usuario y contraseña son obligatorios"}), 400

    conn = get_db()
    try:
        row = _bootstrap_admin(conn, username, password, str(data.get("email") or ""))
        if row is None:
            row = conn.execute(
                "SELECT id, username, password, email, nombre, rol, activo FROM usuarios WHERE username=?",
                (username,),
            ).fetchone()
        if row is None or not bool(row["activo"]) or not _is_password_match(row["password"], password):
            return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401

        # Upgrade legacy plaintext passwords after a successful login.
        if not str(row["password"]).startswith(("scrypt:", "pbkdf2:", "argon2:")):
            conn.execute("UPDATE usuarios SET password=? WHERE id=?", (generate_password_hash(password), row["id"]))
            conn.commit()

        session.clear()
        session["user_id"] = int(row["id"])
        session["role"] = str(row["rol"])
        session.permanent = True
        return jsonify({"ok": True, "authenticated": True, "user_id": int(row["id"]), "role": str(row["rol"])})
    finally:
        conn.close()


@auth_api.post("/session")
def set_session():
    """Bridge endpoint for a trusted legacy app; disabled unless explicitly configured."""
    bridge_token = os.getenv("LEGACY_SESSION_BRIDGE_TOKEN", "").strip()
    supplied_token = request.headers.get("X-Legacy-Session-Token", "").strip()
    if not bridge_token or not hmac.compare_digest(supplied_token, bridge_token):
        return jsonify({"ok": False, "error": "Puente de sesión no autorizado"}), 403

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    role = str(data.get("role") or "vendedor")
    if not isinstance(user_id, int) or user_id <= 0:
        return jsonify({"ok": False, "error": "user_id inválido"}), 400
    if role not in {"admin", "vendedor", "cajero", "almacen"}:
        return jsonify({"ok": False, "error": "rol inválido"}), 400

    conn = get_db()
    try:
        user = conn.execute("SELECT id, rol, activo FROM usuarios WHERE id=?", (user_id,)).fetchone()
        if user is None or not bool(user["activo"]) or str(user["rol"]) != role:
            return jsonify({"ok": False, "error": "Usuario no autorizado"}), 403
    finally:
        conn.close()

    session.clear()
    session["user_id"] = user_id
    session["role"] = role
    session.permanent = True
    return jsonify({"ok": True, "authenticated": True, "user_id": user_id, "role": role})


@auth_api.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})
