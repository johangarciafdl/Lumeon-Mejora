from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from core.config import Settings


class EmailServiceError(RuntimeError):
    pass


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def valid_email(email: str) -> bool:
        import re
        return bool(re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", email.strip()))

    def send_receipt(self, *, recipient: str, customer_name: str, invoice: str, pdf_bytes: bytes) -> str:
        recipient = recipient.strip()
        if not self.settings.resend_api_key:
            raise EmailServiceError("RESEND_API_KEY no configurada")
        if not self.valid_email(recipient):
            raise EmailServiceError("Email de cliente inválido")

        payload = {
            "from": f"{self.settings.mail_from_name} <onboarding@resend.dev>",
            "to": [recipient],
            "subject": f"Tu Recibo LUMEON #{invoice}",
            "html": (
                f"<p>Hola {customer_name or 'Cliente'},</p>"
                f"<p>Adjuntamos tu recibo LUMEON <strong>#{invoice}</strong>.</p>"
                "<p>Gracias por tu confianza.</p>"
            ),
            "attachments": [{
                "filename": f"Recibo_LUMEON_{invoice}.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }],
        }
        request = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Lumeon/2",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise EmailServiceError(f"Resend rechazó el email ({exc.code}): {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise EmailServiceError(f"No se pudo conectar con Resend: {exc.reason}") from exc

        return str(body.get("id", ""))
