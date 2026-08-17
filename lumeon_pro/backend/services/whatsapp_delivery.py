from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol


class WhatsAppProvider(Protocol):
    def send_message(self, phone: str, message: str) -> dict: ...


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    phone: str
    provider: str
    response: dict | None = None
    error: str | None = None


def normalize_colombian_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("57") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10 and digits.startswith("3"):
        return f"+57{digits}"
    raise ValueError("Número de WhatsApp colombiano inválido")


class WhatsAppDeliveryService:
    def __init__(self, provider: WhatsAppProvider):
        self.provider = provider

    def send_invoice(self, *, phone: str, customer_name: str, invoice: str, total: float, url: str | None = None) -> DeliveryResult:
        normalized = normalize_colombian_phone(phone)
        message = f"Hola {customer_name or 'Cliente'} 👋\n\nLUMEON: factura #{invoice}\nTotal: ${total:,.2f}\n"
        if url:
            message += f"\nConsulta tu factura: {url}\n"
        message += "\nGracias por tu compra."
        try:
            response = self.provider.send_message(normalized, message)
            if response.get("ok"):
                return DeliveryResult("SENT", normalized, type(self.provider).__name__, response)
            return DeliveryResult("FAILED", normalized, type(self.provider).__name__, response, "Proveedor rechazó el mensaje")
        except Exception as exc:
            return DeliveryResult("FAILED", normalized, type(self.provider).__name__, error=str(exc))
