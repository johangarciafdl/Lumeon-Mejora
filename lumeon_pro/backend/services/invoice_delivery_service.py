from __future__ import annotations

from services.communication_service import DeliveryResult, can_retry, record_attempt
from services.invoice_service import build_invoice
from services.whatsapp_provider import WhatsAppError, get_whatsapp_provider
from services.whatsapp_service import build_invoice_message

BLOCKED_STATES = {"devuelta", "devuelto", "anulada", "anulado", "cancelada", "cancelado"}


def deliver_invoice(conn, *, sale_id: int, invoice_number: str, customer_name: str,
                    phone: str, items: list[dict], total: float,
                    force_retry: bool = False) -> dict:
    sale = conn.execute("SELECT estado FROM ventas WHERE id=? LIMIT 1", (sale_id,)).fetchone()
    if not sale:
        return {"invoice": None, "whatsapp": DeliveryResult(channel="whatsapp", status="NOT_FOUND")}

    state = str(sale["estado"] or "").strip().lower()
    if state in BLOCKED_STATES:
        return {"invoice": None, "whatsapp": DeliveryResult(channel="whatsapp", status="BLOCKED", error="La venta no admite entrega")}

    invoice = build_invoice(invoice_number=invoice_number, customer_name=customer_name, items=items, total=total)
    result = {"invoice": invoice, "whatsapp": None}
    phone = str(phone or "").strip()
    if not phone:
        return result

    # force_retry means the caller explicitly asked for another attempt; it does
    # not bypass the safety cap or resend a successful delivery.
    if not can_retry(conn, venta_id=sale_id, channel="whatsapp", recipient=phone):
        status = "ALREADY_SENT" if not force_retry else "RETRY_NOT_ALLOWED"
        return {**result, "whatsapp": DeliveryResult(channel="whatsapp", status=status)}

    try:
        provider = get_whatsapp_provider()
        provider.send(phone=phone, message=build_invoice_message(customer_name, invoice_number, total))
        delivery = DeliveryResult(channel="whatsapp", status="SENT")
    except WhatsAppError as exc:
        delivery = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc)[:500])

    record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=delivery)
    return {**result, "whatsapp": delivery}
