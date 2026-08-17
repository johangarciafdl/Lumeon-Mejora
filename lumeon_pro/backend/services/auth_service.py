from __future__ import annotations

from flask import session

from services.authorization_service import Actor


class AuthenticationError(PermissionError):
    pass


def current_actor() -> Actor:
    user_id = session.get("user_id")
    if user_id is None:
        raise AuthenticationError("Debes iniciar sesión")
    try:
        actor_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Sesión inválida") from exc
    return Actor(id=actor_id, role=str(session.get("role", "vendedor")))
