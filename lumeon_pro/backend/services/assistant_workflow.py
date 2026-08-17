from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


WRITE_INTENTS = {
    "create_customer",
    "create_product",
    "create_sale",
    "send_invoice",
}


@dataclass
class AssistantSession:
    """In-memory conversation state; persistent storage can be added later."""
    pending_intent: str | None = None
    pending_payload: dict[str, Any] = field(default_factory=dict)

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

    def confirm(self) -> tuple[str, dict[str, Any]] | None:
        if not self.pending_intent:
            return None
        result = (self.pending_intent, dict(self.pending_payload))
        self.pending_intent = None
        self.pending_payload = {}
        return result

    def cancel(self) -> bool:
        had_pending = self.pending_intent is not None
        self.pending_intent = None
        self.pending_payload = {}
        return had_pending


def is_confirmation(text: str) -> bool:
    return text.strip().lower() in {"si", "sí", "confirmo", "confirmar", "ok", "acepto"}


def is_cancellation(text: str) -> bool:
    return text.strip().lower() in {"no", "cancelar", "cancela", "cancelado"}
