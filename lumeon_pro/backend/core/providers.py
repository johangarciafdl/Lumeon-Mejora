from __future__ import annotations

import os

from services.whatsapp_service import CallMeBotProvider


def get_whatsapp_provider():
    provider = os.getenv("WHATSAPP_PROVIDER", "callmebot").strip().lower()
    if provider in {"", "callmebot"}:
        return CallMeBotProvider(os.getenv("CALLMEBOT_API_KEY", ""))
    raise RuntimeError(f"Proveedor WhatsApp no soportado: {provider}")
