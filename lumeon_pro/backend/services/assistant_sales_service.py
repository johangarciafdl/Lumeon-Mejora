from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from services.communication_service import DeliveryResult, record_attempt
from services.invoice_service import build_invoice
from services.sale_service import create_sale
from services.whatsapp_service import CallMeBotProvider, build_invoice_message, WhatsAppError


@dataclass(frozen=True)
class AssistantSaleResult:
    sale_id: int
    invoice_number: str
    invoice_filename: str
    whatsapp_status: str
    whatsapp_error: str | None = None


class AssistantSaleService:
    """Execute a confirmed assistant sale; WhatsApp delivery is best-effort."""

    @staticmethod
    def _total(data: dict[str, Any]) -> float:
        if data.get("total") is not None:
            return float(data["total"])
        return round(sum(
            int(item.get("cantidad", 0)) * float(item.get("precio_venta", 0))
            for item in (data.get("items") or [])
        ), 2)

    @staticmethod
    def _callmebot_key() -> str:
        return os.getenv("CALLMEBOT_API_KEY", "").strip()

    def execute(self, conn, *, actor_id: int, data: dict[str, Any]) -> AssistantSaleResult:
        total = self._total(data)
        invoice_number = str(data["numero_factura"])
        sale_id = create_sale(conn, data={**data, "total": total}, user_id=actor_id)
        invoice = build_invoice(
            invoice_number=invoice_number,
            customer_name=str(data.get("cliente_nombre", "")),
            items=list(data.get("items") or []),
            total=total,
        )

        phone = str(data.get("cliente_telefono", "")).strip()
        if not phone:
            return AssistantSaleResult(sale_id, invoice_number, invoice.filename, "SKIPPED")

        api_key = self._callmebot_key()
        if not api_key:
            result = DeliveryResult(channel="whatsapp", status="SKIPPED", error="CALLMEBOT_API_KEY no configurada")
            record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=result)
            return AssistantSaleResult(sale_id, invoice_number, invoice.filename, result.status, result.error)

        message = build_invoice_message(str(data.get("cliente_nombre", "")), invoice_number, total)
        try:
            response = CallMeBotProvider(api_key).send_message(phone, message)
            result = DeliveryResult(
                channel="whatsapp",
                status="SENT" if response.get("ok") else "FAILED",
                error=None if response.get("ok") else str(response.get("response", ""))[:500],
            )
        except WhatsAppError as exc:
            result = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc)[:500])

        record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=result)
        return AssistantSaleResult(sale_id, invoice_number, invoice.filename, result.status, result.error)
