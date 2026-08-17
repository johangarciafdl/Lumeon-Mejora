from __future__ import annotations

import os

from services.communication_service import DeliveryResult, can_retry, record_attempt
from services.invoice_service import build_invoice
from services.whatsapp_service import CallMeBotProvider, WhatsAppError, build_invoice_message


def deliver_invoice(conn, *, sale_id: int, invoice_number: str, customer_name: str,
                    phone: str, items: list[dict], total: float,
                    force_retry: bool = False) -> dict:
    sale = conn.execute("SELECT estado FROM ventas WHERE id=? LIMIT 1", (sale_id,)).fetchone()
    if not sale:
        return {"invoice": None, "whatsapp": DeliveryResult(channel="whatsapp", status="NOT_FOUND")}
    if str(sale["estado"] or "").strip().lower() in {"devuelta", "anulada", "cancelada"}:
        return {"invoice": None, "whatsapp": DeliveryResult(channel="whatsapp", status="BLOCKED", error="La venta no admite entrega")}

    invoice = build_invoice(invoice_number=invoice_number, customer_name=customer_name, items=items, total=total)
    result = {"invoice": invoice, "whatsapp": None}
    phone = str(phone or "").strip()
    if not phone:
        return result

    allowed = can_retry(conn, venta_id=sale_id, channel="whatsapp", recipient=phone)
    if not allowed:
        status = "RETRY_NOT_ALLOWED" if force_retry else "ALREADY_SENT"
        return {**result, "whatsapp": DeliveryResult(channel="whatsapp", status=status)}

    api_key = os.getenv("CALLMEBOT_API_KEY", "").strip()
    if not api_key:
        delivery = DeliveryResult(channel="whatsapp", status="SKIPPED", error="CALLMEBOT_API_KEY no configurada")
        record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=delivery)
        return {**result, "whatsapp": delivery}

    try:
        response = CallMeBotProvider(api_key).send_message(
            phone, build_invoice_message(customer_name, invoice_number, total)
        )
        delivery = DeliveryResult(
            channel="whatsapp",
            status="SENT" if response.get("ok") else "FAILED",
            provider_message_id=str(response.get("message_id")) if response.get("message_id") else None,
            error=None if response.get("ok") else str(response.get("response", ""))[:500],
        )
    except WhatsAppError as exc:
        delivery = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc)[:500])

    record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=delivery)
    return {**result, "whatsapp": delivery}
