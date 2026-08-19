from __future__ import annotations

import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WhatsAppError(RuntimeError):
    pass


class WhatsAppProvider:
    name = "unknown"

    def send(self, *, phone: str, message: str) -> None:
        raise NotImplementedError


class CallMeBotProvider(WhatsAppProvider):
    name = "callmebot"
    endpoint = "https://api.callmebot.com/whatsapp.php"

    def __init__(self) -> None:
        self.api_key = (os.getenv("CALLMEBOT_API_KEY", "") or os.getenv("CALLMEBOT_KEY", "")).strip()
        self.country_code = os.getenv("CALLMEBOT_COUNTRY_CODE", "57").strip() or "57"
        if not self.api_key:
            raise WhatsAppError("CALLMEBOT_API_KEY no está configurada")

    @staticmethod
    def normalize_phone(phone: str) -> str:
        value = "".join(ch for ch in str(phone or "").strip() if ch.isdigit() or ch == "+")
        if value.startswith("00"):
            value = "+" + value[2:]
        elif value.startswith("57") and len(value) == 12:
            value = "+" + value
        elif value.startswith("3") and len(value) == 10:
            value = "+57" + value
        return value

    def send(self, *, phone: str, message: str) -> None:
        phone = self.normalize_phone(phone)
        if not phone.startswith("+"):
            raise WhatsAppError("El teléfono debe incluir código internacional")
        payload = urlencode({"phone": phone, "text": message, "apikey": self.api_key}).encode()
        request = Request(self.endpoint, data=payload, method="POST")
        try:
            with urlopen(request, timeout=float(os.getenv("WHATSAPP_TIMEOUT", "15"))) as response:
                if response.status < 200 or response.status >= 300:
                    raise WhatsAppError(f"CallMeBot HTTP {response.status}")
        except WhatsAppError:
            raise
        except Exception as exc:
            raise WhatsAppError("No fue posible contactar CallMeBot") from exc


def get_whatsapp_provider() -> WhatsAppProvider:
    provider = os.getenv("WHATSAPP_PROVIDER", "callmebot").strip().lower()
    if provider == "callmebot":
        return CallMeBotProvider()
    if provider == "meta":
        from services.meta_whatsapp_provider import MetaWhatsAppProvider
        return MetaWhatsAppProvider()
    raise WhatsAppError(f"Proveedor WhatsApp no soportado: {provider}")
