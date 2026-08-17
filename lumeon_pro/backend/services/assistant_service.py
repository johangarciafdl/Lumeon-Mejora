from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantIntent:
    name: str
    args: dict
    requires_confirmation: bool = False


class AssistantService:
    """Deterministic command layer; it never executes arbitrary SQL or code."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn

    def parse(self, text: str) -> AssistantIntent:
        value = " ".join(text.strip().split())
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
        """Execute read-only intents. Mutations remain behind explicit services/confirmation."""
        if self.conn is None:
            raise RuntimeError("AssistantService requiere una conexión para ejecutar consultas")

        if intent.name == "search_customer":
            q = f"%{intent.args['query']}%"
            rows = self.conn.execute(
                "SELECT id,nombre,documento,telefono,email,ciudad FROM clientes "
                "WHERE nombre LIKE ? OR documento LIKE ? OR telefono LIKE ? OR email LIKE ? "
                "ORDER BY nombre LIMIT 20", (q, q, q, q)
            ).fetchall()
            return {"intent": intent.name, "results": [dict(row) for row in rows]}

        if intent.name == "search_product":
            q = f"%{intent.args['query']}%"
            rows = self.conn.execute(
                "SELECT id,nombre,referencia,stock,stock_minimo,precio_venta FROM productos "
                "WHERE nombre LIKE ? OR referencia LIKE ? ORDER BY nombre LIMIT 20", (q, q)
            ).fetchall()
            return {"intent": intent.name, "results": [dict(row) for row in rows]}

        if intent.name in {"inventory_status", "low_stock"}:
            query = "SELECT id,nombre,referencia,stock,stock_minimo FROM productos"
            if intent.name == "low_stock":
                query += " WHERE stock <= stock_minimo"
            query += " ORDER BY stock ASC LIMIT 100"
            rows = self.conn.execute(query).fetchall()
            return {"intent": intent.name, "results": [dict(row) for row in rows]}

        raise ValueError("La operación requiere un service de escritura o confirmación")
