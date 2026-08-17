import pytest

from services.whatsapp_service import CallMeBotProvider, WhatsAppError, build_invoice_message


def test_provider_requires_key():
    with pytest.raises(WhatsAppError):
        CallMeBotProvider("").send_message("+573000000000", "hola")


def test_provider_requires_phone():
    with pytest.raises(WhatsAppError):
        CallMeBotProvider("test-key").send_message("", "hola")


def test_invoice_message_contains_safe_summary():
    message = build_invoice_message("Ana", "LUM-1", 12345.5)
    assert "LUM-1" in message
    assert "12,345.50" in message
    assert "Ana" in message
