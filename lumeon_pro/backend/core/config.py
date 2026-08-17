from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    allowed_origins: tuple[str, ...]
    resend_api_key: str
    mail_from_name: str
    admin_username: str
    admin_password: str
    admin_email: str
    session_cookie_secure: bool
    database_url: str
    callmebot_api_key: str
    callmebot_default_phone: str


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    secret_key = os.getenv("SECRET_KEY", "").strip()
    production = os.getenv("FLASK_ENV", "").strip().lower() == "production"
    if production and not secret_key:
        raise RuntimeError("SECRET_KEY es obligatorio en producción")
    if not secret_key:
        secret_key = secrets.token_hex(32)

    origins = tuple(
        item.strip()
        for item in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5000,http://127.0.0.1:5000",
        ).split(",")
        if item.strip()
    )

    return Settings(
        secret_key=secret_key,
        allowed_origins=origins,
        resend_api_key=os.getenv("RESEND_API_KEY", "").strip(),
        mail_from_name=os.getenv("MAIL_FROM_NAME", "LUMEON").strip() or "LUMEON",
        admin_username=os.getenv("ADMIN_USERNAME", "").strip(),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        admin_email=os.getenv("ADMIN_EMAIL", "admin@lumeon.local").strip(),
        session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", production),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        callmebot_api_key=os.getenv("CALLMEBOT_API_KEY", "").strip(),
        callmebot_default_phone=os.getenv("CALLMEBOT_DEFAULT_PHONE", "").strip(),
    )
