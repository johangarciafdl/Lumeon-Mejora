from __future__ import annotations

import os

from services.communication_service import DeliveryResult, get_delivery if False else None

MAX_RETRIES = 3


def retry_allowed(delivery, max_retries: int = MAX_RETRIES) -> bool:
    if not delivery:
        return False
    status = str(delivery["status"] or "").upper()
    attempts = int(delivery["attempts"] or 0)
    return status in {"FAILED", "SKIPPED"} and attempts < max_retries


def retry_limit() -> int:
    raw = os.getenv("WHATSAPP_MAX_RETRIES", str(MAX_RETRIES))
    try:
        return max(1, min(int(raw), 10))
    except ValueError:
        return MAX_RETRIES
