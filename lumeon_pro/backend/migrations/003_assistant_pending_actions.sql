-- Safe, additive migration for Supabase/PostgreSQL and local SQLite.
CREATE TABLE IF NOT EXISTS assistant_pending_actions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    intent TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assistant_pending_user
    ON assistant_pending_actions(user_id, created_at);
