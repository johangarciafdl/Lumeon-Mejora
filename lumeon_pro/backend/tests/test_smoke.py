import os
import sys
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FLASK_ENV", "testing")

from app_v2 import app  # noqa: E402
from api.auth_api import _is_password_match  # noqa: E402
from services.assistant_workflow import AssistantSession, is_cancellation, is_confirmation  # noqa: E402
from wsgi import application  # noqa: E402


class SmokeTests(unittest.TestCase):
    def test_wsgi_exposes_flask_application(self):
        self.assertIs(application, app)

    def test_health_endpoint(self):
        client = app.test_client()
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_refund_requires_confirmation_and_idempotency(self):
        session = AssistantSession()
        with self.assertRaises(ValueError):
            session.propose_refund(sale_id=123, idempotency_key="")
        proposal = session.propose_refund(
            sale_id=123,
            idempotency_key="test-refund-123",
            reason="Prueba de humo",
        )
        self.assertEqual(proposal["status"], "confirmation_required")
        self.assertEqual(proposal["intent"], "refund_sale")
        self.assertEqual(proposal["payload"]["sale_id"], 123)
        self.assertEqual(session.confirm()[0], "refund_sale")

    def test_confirmation_and_cancellation_words(self):
        self.assertTrue(is_confirmation("sí"))
        self.assertTrue(is_confirmation("CONFIRMO"))
        self.assertTrue(is_cancellation("cancelar"))
        self.assertTrue(is_cancellation("NO"))

    def test_password_verification_supports_hashes_and_legacy_plaintext(self):
        password = "test-password"
        hashed = generate_password_hash(password)
        self.assertTrue(_is_password_match(hashed, password))
        self.assertFalse(_is_password_match(hashed, "wrong"))
        self.assertTrue(_is_password_match(password, password))
        self.assertFalse(_is_password_match(password, "wrong"))


if __name__ == "__main__":
    unittest.main()
