from __future__ import annotations

from services.communication_service import DeliveryResult, can_retry, record_attempt
from services.invoice_service import build_invoice
from services.whatsapp_provider import WhatsAppError, get_whatsapp_provider
from services.whatsapp_service import build_invoice_message


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

    try:
        provider = get_whatsapp_provider()
        provider.send(phone=phone, message=build_invoice_message(customer_name, invoice_number, total))
        delivery = DeliveryResult(channel="whatsapp", status="SENT")
    except WhatsAppError as exc:
        delivery = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc)[:500])

    record_attempt(conn, venta_id=sale_id, channel="whatsapp", provider="callmebot", recipient=phone, result=delivery)
    return {**result, "whatsapp": delivery}
