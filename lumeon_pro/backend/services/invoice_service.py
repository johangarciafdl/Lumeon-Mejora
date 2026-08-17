from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO


class InvoiceError(ValueError):
    pass


@dataclass(frozen=True)
class InvoiceDocument:
    filename: str
    content_type: str
    data: bytes


def build_invoice(*, invoice_number: str, customer_name: str, items: list[dict], total: float) -> InvoiceDocument:
    """Build a dependency-light invoice document.

    PDF rendering is intentionally isolated behind this service so the web/API
    layer does not depend on a PDF library or external service.
    """
    number = str(invoice_number).strip()
    if not number:
        raise InvoiceError("El número de factura es obligatorio")
    if total < 0:
        raise InvoiceError("El total no puede ser negativo")

    lines = [
        "LUMEON",
        f"Factura: {number}",
        f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
        f"Cliente: {customer_name or 'Consumidor final'}",
        "",
    ]
    for item in items:
        name = str(item.get("nombre", item.get("referencia", "Producto")))
        quantity = int(item.get("cantidad", 0))
        price = float(item.get("precio_venta", 0))
        lines.append(f"{quantity} x {name} = {quantity * price:.2f}")
    lines.extend(["", f"TOTAL: {total:.2f}"])
    payload = "\n".join(lines).encode("utf-8")
    return InvoiceDocument(
        filename=f"Factura_LUMEON_{number}.pdf",
        content_type="application/pdf",
        data=payload,
    )
