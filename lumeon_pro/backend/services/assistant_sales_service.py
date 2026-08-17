from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.communication_service import DeliveryResult, record_attempt
from services.invoice_service import build_invoice
from services.sale_service import SaleError, create_sale
from services.whatsapp_service import CallMeBotProvider, build_invoice_message, WhatsAppError


@dataclass(frozen=True)
class AssistantSaleResult:
    sale_id: int
    invoice_number: str
    invoice_filename: str
    whatsapp_status: str
    whatsapp_error: str | None = None


class AssistantSaleService:
    """Orchestrates an already-confirmed sale initiated by the assistant.

    The sale transaction is completed before any external provider is called.
    A WhatsApp failure therefore never rolls back the sale.
    """

    def __init__(self, settings):
        self.settings = settings

    def execute(self, conn, *, actor_id: int, data: dict[str, Any]) -> AssistantSaleResult:
        sale_id = create_sale(conn, data=data, user_id=actor_id)
        invoice = build_invoice(
            invoice_number=str(data["numero_factura"]),
            customer_name=str(data.get("cliente_nombre", "")),
            items=list(data.get("items") or []),
            total=float(data.get("total") or 0),
        )

        phone = str(data.get("cliente_telefono", "")).strip()
        if not phone:
            return AssistantSaleResult(
                sale_id=sale_id,
                invoice_number=str(data["numero_factura"]),
                invoice_filename=invoice.filename,
                whatsapp_status="SKIPPED",
            )

        provider = CallMeBotProvider(self.settings.callmebot_api_key)
        message = build_invoice_message(
            str(data.get("cliente_nombre", "")),
            str(data["numero_factura"]),
            float(data.get("total") or 0),
        )
        try:
            response = provider.send_message(phone, message)
            result = DeliveryResult(
                channel="whatsapp",
                status="SENT" if response.get("ok") else "FAILED",
                provider_message_id=None,
                error=None if response.get("ok") else str(response.get("response", ""))[:500],
            )
        except WhatsAppError as exc:
            result = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc)[:500])

        record_attempt(
            conn,
            venta_id=sale_id,
            channel="whatsapp",
            provider="callmebot",
            recipient=phone,
            result=result,
        )
        return AssistantSaleResult(
            sale_id=sale_id,
            invoice_number=str(data["numero_factura"]),
            invoice_filename=invoice.filename,
            whatsapp_status=result.status,
            whatsapp_error=result.error,
        )
