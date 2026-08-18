from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.assistant_sale_builder import SaleDraft


WRITE_INTENTS = {
    "create_customer",
    "create_product",
    "create_sale",
    "send_invoice",
    "refund_sale",
}


@dataclass
class AssistantSession:
    """Conversation state that can be serialized to the persistent session store."""
    pending_intent: str | None = None
    pending_payload: dict[str, Any] = field(default_factory=dict)
    sale_draft: SaleDraft | None = None

    def propose(self, intent: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.pending_intent = intent
        self.pending_payload = dict(payload)
        if intent in WRITE_INTENTS:
            return {
                "status": "confirmation_required",
                "intent": intent,
                "payload": self.pending_payload,
                "message": "Esta operación modifica datos o envía una factura. Confirma para continuar.",
            }
        return {"status": "ready", "intent": intent, "payload": self.pending_payload}

    def start_sale(self, customer: dict[str, Any]) -> dict[str, Any]:
        customer_id = customer.get("id")
        if not customer_id:
            raise ValueError("Selecciona un cliente válido para iniciar la venta")
        self.sale_draft = SaleDraft(customer_id=int(customer_id), customer_name=str(customer.get("nombre", "")))
        return self.sale_summary()

    def add_sale_item(self, product: dict[str, Any], quantity: int) -> dict[str, Any]:
        if self.sale_draft is None:
            raise ValueError("Primero debes seleccionar un cliente para la venta")
        self.sale_draft.add_item(product, quantity)
        return self.sale_summary()

    def sale_summary(self) -> dict[str, Any]:
        if self.sale_draft is None:
            return {"status": "idle"}
        return {"status": "sale_draft", **self.sale_draft.summary()}

    def propose_sale(self) -> dict[str, Any]:
        if self.sale_draft is None:
            raise ValueError("No hay una venta en construcción")
        self.sale_draft.validate()
        return self.propose("create_sale", self.sale_draft.summary())

    def propose_refund(self, *, sale_id: int, idempotency_key: str, reason: str = "") -> dict[str, Any]:
        if int(sale_id) <= 0:
            raise ValueError("Selecciona una venta válida para devolver")
        if not str(idempotency_key or "").strip():
            raise ValueError("La devolución requiere una clave de idempotencia")
        return self.propose("refund_sale", {
            "sale_id": int(sale_id),
            "idempotency_key": str(idempotency_key).strip(),
            "motivo": str(reason or "").strip()[:500],
        })

    def confirm(self) -> tuple[str, dict[str, Any]] | None:
        if not self.pending_intent:
            return None
        result = (self.pending_intent, dict(self.pending_payload))
        self.pending_intent = None
        self.pending_payload = {}
        return result

    def cancel(self) -> bool:
        had_pending = self.pending_intent is not None or self.sale_draft is not None
        self.pending_intent = None
        self.pending_payload = {}
        self.sale_draft = None
        return had_pending


def is_confirmation(text: str) -> bool:
    return text.strip().lower() in {"si", "sí", "confirmo", "confirmar", "ok", "acepto"}


def is_cancellation(text: str) -> bool:
    return text.strip().lower() in {"no", "cancelar", "cancela", "cancelado"}
