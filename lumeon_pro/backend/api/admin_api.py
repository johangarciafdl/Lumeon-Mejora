from __future__ import annotations

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from core.db import get_db
from services.auth_service import AuthenticationError, current_actor
from services.authorization_service import require
from services.sale_delete_service import SaleDeleteError, delete_sale

admin_api = Blueprint("admin_api", __name__, url_prefix="/api/v2/admin")


@admin_api.get("/logs")
def logs():
    try:
        actor = current_actor()
        require(actor, "view_audit_log")

        try:
            limit = min(max(int(request.args.get("limit", 100)), 1), 500)
        except (TypeError, ValueError):
            limit = 100

        conn = get_db()

        try:
            rows = conn.execute(
                """
                SELECT
                    a.id,
                    a.user_id,
                    COALESCE(u.username, 'sistema') AS username,
                    a.action,
                    a.entity_type,
                    a.entity_id,
                    a.metadata,
                    a.created_at
                FROM audit_log a
                LEFT JOIN usuarios u ON u.id = a.user_id
                ORDER BY a.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return jsonify({
                "ok": True,
                "results": [dict(r) for r in rows],
            })
        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@admin_api.post("/users")
def create_user():
    try:
        actor = current_actor()
        require(actor, "manage_users")

        data = request.get_json(silent=True) or {}

        username = str(data.get("username") or "").strip()
        password = str(data.get("password") or "")
        nombre = str(data.get("nombre") or username).strip()
        email = str(data.get("email") or "admin@lumeon.local").strip()
        role = str(data.get("role") or "admin").strip().lower()

        if not username or not password:
            return jsonify({
                "ok": False,
                "error": "Usuario y contraseña son obligatorios",
            }), 400

        if role not in {"admin", "vendedor", "cajero", "almacen"}:
            return jsonify({
                "ok": False,
                "error": "Rol inválido",
            }), 400

        conn = get_db()

        try:
            existing = conn.execute(
                "SELECT id FROM usuarios WHERE username=?",
                (username,),
            ).fetchone()

            if existing:
                return jsonify({
                    "ok": False,
                    "error": "El usuario ya existe",
                }), 409

            row = conn.execute(
                """
                INSERT INTO usuarios
                    (username, password, email, nombre, rol, activo)
                VALUES
                    (?, ?, ?, ?, ?, TRUE)
                RETURNING id, username, email, nombre, rol, activo
                """,
                (
                    username,
                    generate_password_hash(password),
                    email,
                    nombre,
                    role,
                ),
            ).fetchone()

            conn.commit()

            return jsonify({
                "ok": True,
                "user": dict(row),
            }), 201

        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403


@admin_api.delete("/ventas/<int:sale_id>")
def delete_sale_v2(sale_id: int):
    try:
        actor = current_actor()
        require(actor, "delete_sale")

        conn = get_db()

        try:
            result = delete_sale(
                conn,
                sale_id=sale_id,
                user_id=int(actor.id),
            )

            conn.commit()

            return jsonify({
                "ok": True,
                **result,
            }), 200

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    except (AuthenticationError, PermissionError) as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 403

    except SaleDeleteError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 400
