from __future__ import annotations

import os

from services.communication_service import DeliveryResult, can_retry, record_attempt
from services.invoice_service import build_invoice
from services.whatsapp_provider import WhatsAppError, get_whatsapp_provider
from services.whatsapp_service import build_invoice_message

BLOCKED_STATES = {"devuelta", "devuelto", "anulada", "anulado", "cancelada", "cancelado"}


def can_send_invoice(conn, sale_id: int, channel: str = "whatsapp") -> tuple[bool, str | None]:
    """Return whether an invoice may be delivered for a sale."""
    if channel.strip().lower() != "whatsapp":
        return True, None

    sale = conn.execute(
        "SELECT estado, cliente_telefono FROM ventas WHERE id=? LIMIT 1",
        (sale_id,),
    ).fetchone()
    if not sale:
        return False, "La venta no existe"

    state = str(sale["estado"] or "").strip().lower()
    if state in BLOCKED_STATES:
        return False, "La venta no admite entrega de factura"

    if not str(sale["cliente_telefono"] or "").strip():
        return False, "La venta no tiene teléfono del cliente"

    return True, None


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

    if not can_retry(conn, venta_id=sale_id, channel="whatsapp", recipient=phone):
        status = "ALREADY_SENT" if not force_retry else "RETRY_NOT_ALLOWED"
        return {**result, "whatsapp": DeliveryResult(channel="whatsapp", status=status)}

    try:
        provider = get_whatsapp_provider()

        delivery_recipient = phone
        if os.getenv("WHATSAPP_PROVIDER", "callmebot").strip().lower() == "callmebot":
            delivery_recipient = (
                os.getenv("CALLMEBOT_DEFAULT_PHONE", "").strip()
                or phone
            )

        provider.send(
            phone=delivery_recipient,
            message=build_invoice_message(
                customer_name,
                invoice_number,
                total,
                items,
            ),
        )
        delivery = DeliveryResult(channel="whatsapp", status="SENT")
    except WhatsAppError as exc:
        delivery = DeliveryResult(channel="whatsapp", status="FAILED", error=str(exc)[:500])

    record_attempt(
        conn,
        venta_id=sale_id,
        channel="whatsapp",
        provider=os.getenv("WHATSAPP_PROVIDER", "callmebot").strip().lower(),
        recipient=delivery_recipient,
        result=delivery,
    )
    return {**result, "whatsapp": delivery}
