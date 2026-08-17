import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from lumeon_pro.backend.app import app, email_valido


def test_email_validation():
    assert email_valido("cliente@example.com")
    assert not email_valido("cliente@")
    assert not email_valido("cliente.example.com")


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_protected_dashboard_requires_authentication():
    client = app.test_client()
    response = client.get("/api/dashboard")
    assert response.status_code in (302, 401)
