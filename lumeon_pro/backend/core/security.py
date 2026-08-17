from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, Any

from flask import jsonify
from flask_login import current_user

F = TypeVar("F", bound=Callable[..., Any])


VALID_ROLES = {"admin", "manager", "seller"}


def require_role(*roles: str):
    allowed = set(roles) & VALID_ROLES
    if not allowed:
        raise ValueError("No se definieron roles válidos")

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"ok": False, "error": "Autenticación requerida"}), 401
            role = getattr(current_user, "rol", "admin")
            if role not in allowed:
                return jsonify({"ok": False, "error": "Permisos insuficientes"}), 403
            return view(*args, **kwargs)
        return wrapped  # type: ignore[return-value]
    return decorator
