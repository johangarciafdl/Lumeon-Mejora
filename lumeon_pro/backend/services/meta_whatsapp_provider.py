from __future__ import annotations

import os

import requests

from services.whatsapp_provider import WhatsAppError, WhatsAppProvider


class MetaWhatsAppProvider(WhatsAppProvider):
    name = "meta_cloud_api"

    def __init__(self) -> None:
        self.access_token = os.getenv("WHATSAPP_META_ACCESS_TOKEN", "").strip()
        self.phone_number_id = os.getenv("WHATSAPP_META_PHONE_NUMBER_ID", "").strip()
        self.api_version = os.getenv("WHATSAPP_META_API_VERSION", "v23.0").strip() or "v23.0"
        self.timeout = float(os.getenv("WHATSAPP_TIMEOUT", "20"))

        if not self.access_token:
            raise WhatsAppError("WHATSAPP_META_ACCESS_TOKEN no está configurado")
        if not self.phone_number_id:
            raise WhatsAppError("WHATSAPP_META_PHONE_NUMBER_ID no está configurado")

        self.endpoint = (
            f"https://graph.facebook.com/{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

    @staticmethod
    def normalize_phone(phone: str) -> str:
        value = "".join(ch for ch in str(phone or "").strip() if ch.isdigit() or ch == "+")
        if value.startswith("00"):
            value = "+" + value[2:]
        elif value.startswith("57") and len(value) == 12:
            value = "+" + value
        elif value.startswith("3") and len(value) == 10:
            value = "+57" + value

        digits = value.lstrip("+")
        if not digits.isdigit():
            raise WhatsAppError("El teléfono contiene caracteres inválidos")
        if not digits.startswith("57"):
            raise WhatsAppError("El teléfono debe incluir el código de país")
        return digits

    def send(self, *, phone: str, message: str) -> None:
        recipient = self.normalize_phone(phone)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": str(message or "").strip(),
            },
        }

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise WhatsAppError("No fue posible contactar Meta WhatsApp Cloud API") from exc

        if response.status_code < 200 or response.status_code >= 300:
            detail = response.text[:500]
            raise WhatsAppError(f"Meta WhatsApp HTTP {response.status_code}: {detail}")

    
