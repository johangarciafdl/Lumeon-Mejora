from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantIntent:
    name: str
    args: dict
    requires_confirmation: bool = False


class AssistantService:
    """Deterministic command layer; an LLM can be added later without granting SQL access."""

    def parse(self, text: str) -> AssistantIntent:
        value = text.strip()
        lowered = value.lower()

        if any(word in lowered for word in ("buscar cliente", "busca cliente", "cliente")) and "buscar" in lowered:
            query = re.sub(r".*?buscar\s+cliente\s*", "", lowered, count=1).strip()
            return AssistantIntent("search_customer", {"query": query})
        if any(word in lowered for word in ("buscar producto", "busca producto")):
            query = re.sub(r".*?buscar\s+producto\s*", "", lowered, count=1).strip()
            return AssistantIntent("search_product", {"query": query})
        if "registrar cliente" in lowered or "crear cliente" in lowered:
            return AssistantIntent("create_customer", {}, True)
        if "registrar producto" in lowered or "crear producto" in lowered:
            return AssistantIntent("create_product", {}, True)
        if "inventario" in lowered or "stock" in lowered:
            return AssistantIntent("inventory_status", {})
        if "ventas de hoy" in lowered or "ventas hoy" in lowered:
            return AssistantIntent("today_sales", {})
        return AssistantIntent("unknown", {"text": value})
