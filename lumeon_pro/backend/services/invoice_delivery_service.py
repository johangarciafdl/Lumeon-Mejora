from __future__ import annotations

import os

from services.communication_service import DeliveryResult, record_attempt
from services.invoice_service import build_invoice
from services.whatsapp_service import CallMeBotProvider, WhatsAppError, build_invoice_message


def deliver_invoice(conn, *, sale_id: int, invoice_number: str, customer_name: str, phone: str, items: list[dict], total: float) -> dict:
    invoice = build_invoice(invoice_number=invoice_number, customer_name=customer_name, items=items, total=total)
    result = {"invoice": invoice, "whatsapp": None}
    if not phone:
        return result

    api_key = os.getenv("CALLMEBOT_API_KEY", "")
    if not api_key:
        delivery = DeliveryResult(channel="whatsapp", status="SKIPPED", error="CALLMEBOT_API_KEY no configurada")
        record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=delivery)
        result["whatsapp"] = delivery
        return result

    provider = CallMeBotProvider(api_key)
    try:
        response = provider.send_message(phone, build_invoice_message(customer_name, invoice_number, total))
        delivery = DeliveryResult(channel="whatsapp", status="SENT" if response.get("ok") else "FAILED", provider_message_id=None, error=None if response.get("ok") else response.get("response"))
    except WhatsAppError as exc:
        delivery = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc))
    record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=delivery)
    result["whatsapp"] = delivery
    return result
