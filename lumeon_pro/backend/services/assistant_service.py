from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from services.customer_service import search_customers
from services.product_service import search_products, low_stock


@dataclass(frozen=True)
class AssistantIntent:
    name: str
    args: dict
    requires_confirmation: bool = False


class AssistantService:
    """Deterministic command layer; never executes arbitrary SQL or code."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn

    def parse(self, text: str) -> AssistantIntent:
        value = " ".join(str(text or "").strip().split())
        lowered = value.lower()
        if not value:
            return AssistantIntent("unknown", {"text": value})
        match = re.search(r"(?:buscar|busca)\s+cliente\s+(.+)$", lowered)
        if match:
            return AssistantIntent("search_customer", {"query": match.group(1).strip()})
        match = re.search(r"(?:buscar|busca)\s+producto\s+(.+)$", lowered)
        if match:
            return AssistantIntent("search_product", {"query": match.group(1).strip()})
        if lowered in {"inventario", "ver inventario", "stock"}:
            return AssistantIntent("inventory_status", {})
        if lowered in {"stock bajo", "productos con stock bajo"}:
            return AssistantIntent("low_stock", {})
        if lowered in {"ventas de hoy", "ventas hoy"}:
            return AssistantIntent("today_sales", {})
        if any(x in lowered for x in ("registrar cliente", "crear cliente", "nuevo cliente")):
            return AssistantIntent("create_customer", {}, True)
        if any(x in lowered for x in ("registrar producto", "crear producto", "nuevo producto")):
            return AssistantIntent("create_product", {}, True)
        if any(x in lowered for x in ("registrar venta", "crear venta", "nueva venta")):
            return AssistantIntent("create_sale", {}, True)
        if "enviar factura" in lowered or "mandar factura" in lowered:
            return AssistantIntent("send_invoice", {}, True)
        return AssistantIntent("unknown", {"text": value})

    def execute_read(self, intent: AssistantIntent) -> dict:
        if self.conn is None:
            raise RuntimeError("AssistantService requiere una conexión")
        if intent.requires_confirmation:
            return {"ok": False, "requires_confirmation": True, "intent": intent.name}
        if intent.name == "search_customer":
            return {"ok": True, "intent": intent.name, "results": search_customers(self.conn, intent.args["query"])}
        if intent.name == "search_product":
            return {"ok": True, "intent": intent.name, "results": search_products(self.conn, intent.args["query"])}
        if intent.name == "inventory_status":
            return {"ok": True, "intent": intent.name, "results": search_products(self.conn, "", 100)}
        if intent.name == "low_stock":
            return {"ok": True, "intent": intent.name, "results": low_stock(self.conn)}
        if intent.name == "today_sales":
            rows = self.conn.execute(
                "SELECT id,numero_factura,cliente_nombre,total,fecha,forma_pago FROM ventas "
                "WHERE date(fecha)=date('now','localtime') ORDER BY id DESC LIMIT 100"
            ).fetchall()
            return {"ok": True, "intent": intent.name, "results": [dict(row) for row in rows]}
        return {"ok": False, "error": "Operación no disponible"}
