import sqlite3

from services.idempotency_service import claim, key_for


def test_claim_is_atomic_and_repeatable():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE idempotency_keys (key TEXT PRIMARY KEY, operation TEXT NOT NULL)")
    key = key_for(1, "session", "create_sale", {"total": 100})
    assert claim(conn, key, "create_sale") is True
    assert claim(conn, key, "create_sale") is False
