-- Migration: announcement templates per-guild
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS announcement_templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    name TEXT,
    content TEXT,
    created_at TEXT
);

COMMIT;
