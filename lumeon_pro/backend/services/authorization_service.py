from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    id: int | None
    role: str


READ_ACTIONS = {"search_customer", "search_product", "view_inventory", "view_sales"}
WRITE_ACTIONS = {"create_customer", "create_product", "create_sale", "send_invoice"}
ADMIN_ACTIONS = {"delete_customer", "delete_product", "refund_sale", "manage_users"}


def can(actor: Actor, action: str) -> bool:
    if actor.role == "admin":
        return action in READ_ACTIONS | WRITE_ACTIONS | ADMIN_ACTIONS
    if actor.role in {"manager", "vendedor"}:
        return action in READ_ACTIONS | WRITE_ACTIONS
    return action in READ_ACTIONS


def require(actor: Actor, action: str) -> None:
    if not can(actor, action):
        raise PermissionError("No tienes permisos para realizar esta acción")
