-- Migration: add per-guild topic settings and opt-out table
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS topic_settings (
    guild_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    enabled INTEGER DEFAULT 1,
    interval_minutes INTEGER DEFAULT 60,
    ping_top_n INTEGER DEFAULT 2,
    last_sent TEXT
);

CREATE TABLE IF NOT EXISTS topic_opt_out (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (guild_id, user_id)
);

COMMIT;
