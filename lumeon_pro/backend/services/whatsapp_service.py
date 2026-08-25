from __future__ import annotations

import json
import urllib.parse
import urllib.request


class WhatsAppError(RuntimeError):
    pass


class CallMeBotProvider:
    """Small provider adapter; credentials stay in environment variables."""

    def __init__(self, api_key: str, endpoint: str = "https://api.callmebot.com/whatsapp.php"):
        self.api_key = api_key.strip()
        self.endpoint = endpoint

    def send_message(self, phone: str, message: str) -> dict:
        if not self.api_key:
            raise WhatsAppError("CALLMEBOT_API_KEY no configurada")
        phone = phone.strip()
        if not phone:
            raise WhatsAppError("Teléfono de WhatsApp requerido")
        params = urllib.parse.urlencode({"phone": phone, "text": message, "apikey": self.api_key})
        request = urllib.request.Request(
            f"{self.endpoint}?{params}",
            headers={"User-Agent": "Lumeon/2"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8", errors="replace")
                return {"ok": 200 <= response.status < 300, "status": response.status, "response": body[:1000]}
        except Exception as exc:
            raise WhatsAppError(f"No se pudo enviar WhatsApp: {exc}") from exc


def build_invoice_message(
    customer_name: str,
    invoice: str,
    total: float,
    items: list[dict] | None = None,
) -> str:
    lines = [
        "*LUMEON - FACTURA*",
        f"Factura: *#{invoice}*",
        f"Cliente: {customer_name or 'Consumidor final'}",
        "",
    ]

    for item in items or []:
        name = str(
            item.get("nombre")
            or item.get("referencia")
            or "Producto"
        ).strip()

        quantity = int(item.get("cantidad") or 0)
        price = float(item.get("precio_venta") or 0)

        lines.append(
            f"{quantity} x {name} - ${quantity * price:,.0f}"
        )

    lines.extend([
        "",
        f"*TOTAL: ${total:,.2f}*",
        "",
        "Gracias por tu compra. 💛",
    ])

    return "\n".join(lines)
