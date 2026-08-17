from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


class InvoiceError(ValueError):
    pass


@dataclass(frozen=True)
class InvoiceDocument:
    filename: str
    content_type: str
    data: bytes


def build_invoice(*, invoice_number: str, customer_name: str, items: list[dict], total: float) -> InvoiceDocument:
    number = str(invoice_number).strip()
    if not number:
        raise InvoiceError("El número de factura es obligatorio")
    if total < 0:
        raise InvoiceError("El total no puede ser negativo")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    y = height - 60
    pdf.setTitle(f"Factura LUMEON {number}")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "LUMEON")
    y -= 28
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, f"Factura: {number}")
    y -= 16
    pdf.drawString(50, y, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 16
    pdf.drawString(50, y, f"Cliente: {customer_name or 'Consumidor final'}")
    y -= 30

    for item in items:
        name = str(item.get("nombre", item.get("referencia", "Producto")))[:70]
        quantity = int(item.get("cantidad", 0))
        price = float(item.get("precio_venta", 0))
        pdf.drawString(50, y, f"{quantity} x {name}")
        pdf.drawRightString(width - 50, y, f"{quantity * price:.2f}")
        y -= 16
        if y < 60:
            pdf.showPage()
            y = height - 60
            pdf.setFont("Helvetica", 10)

    y -= 12
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 50, y, f"TOTAL: {total:.2f}")
    pdf.save()
    return InvoiceDocument(
        filename=f"Factura_LUMEON_{number}.pdf",
        content_type="application/pdf",
        data=buffer.getvalue(),
    )
