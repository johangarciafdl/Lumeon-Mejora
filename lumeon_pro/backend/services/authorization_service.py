from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    id: int | None
    role: str


# Keep both the original semantic names and the route-level names used by
# the V2 blueprints. This avoids denying valid authenticated users simply
# because one layer calls the permission "read_product" while another uses
# "search_product".
READ_ACTIONS = {
    "search_customer",
    "search_product",
    "view_inventory",
    "view_sales",
    "read_customer",
    "read_product",
    "read_sale",
}
WRITE_ACTIONS = {
    "create_customer",
    "create_product",
    "create_sale",
    "send_invoice",
    "update_inventory",
    "update_sale",
    "update_product",
    "update_customer",
    "record_payment",
}
ADMIN_ACTIONS = {"delete_customer", "delete_product", "delete_sale", "refund_sale", "manage_users", "view_audit_log"}


def can(actor: Actor, action: str) -> bool:
    if actor.role == "admin":
        return action in READ_ACTIONS | WRITE_ACTIONS | ADMIN_ACTIONS
    if actor.role in {"manager", "vendedor"}:
        return action in READ_ACTIONS | WRITE_ACTIONS
    return action in READ_ACTIONS


def require(actor: Actor, action: str) -> None:
    if not can(actor, action):
        raise PermissionError("No tienes permisos para realizar esta acción")
