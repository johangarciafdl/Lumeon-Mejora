from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    enabled: bool
    configured: bool
    description: str


def get_provider_status() -> list[ProviderStatus]:
    import os
    return [
        ProviderStatus("supabase", bool(os.getenv("DATABASE_URL")), bool(os.getenv("DATABASE_URL")), "PostgreSQL principal"),
        ProviderStatus("callmebot", bool(os.getenv("CALLMEBOT_ENABLED", "1")), bool(os.getenv("CALLMEBOT_API_KEY")), "WhatsApp opcional"),
        ProviderStatus("resend", bool(os.getenv("RESEND_ENABLED", "1")), bool(os.getenv("RESEND_API_KEY")), "Email opcional"),
    ]
