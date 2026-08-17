from __future__ import annotations

from functools import wraps
from typing import Callable, Any

from flask import jsonify
from flask_login import current_user


ROLE_RANK = {"viewer": 10, "seller": 20, "manager": 30, "admin": 40}


def login_required_api(fn: Callable[..., Any]):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"ok": False, "error": "Autenticación requerida"}), 401
        return fn(*args, **kwargs)
    return wrapper


def role_required(minimum: str):
    if minimum not in ROLE_RANK:
        raise ValueError(f"Rol desconocido: {minimum}")

    def decorator(fn: Callable[..., Any]):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"ok": False, "error": "Autenticación requerida"}), 401
            role = getattr(current_user, "role", "viewer")
            if ROLE_RANK.get(role, 0) < ROLE_RANK[minimum]:
                return jsonify({"ok": False, "error": "Permisos insuficientes"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
