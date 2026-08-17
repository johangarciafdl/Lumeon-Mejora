from services.audit_service import record


def test_record_uses_canonical_audit_log(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'audit.db'}")
    from core.db import get_db
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)
        record(conn, actor_id=7, action="test.event", entity="test", entity_id=3, details={"ok": True})
        row = conn.execute("SELECT user_id, action, entity_type, entity_id, metadata FROM audit_log").fetchone()
        assert row["user_id"] == 7
        assert row["action"] == "test.event"
        assert row["entity_type"] == "test"
        assert row["entity_id"] == "3"
        assert '"ok": true' in row["metadata"]
    finally:
        conn.close()
