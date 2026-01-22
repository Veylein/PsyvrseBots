-- Migration: add messages, pings, rewards and migrations table
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS migrations (
    filename TEXT PRIMARY KEY,
    applied_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    author_id INTEGER,
    created_at TEXT,
    content TEXT
);

CREATE TABLE IF NOT EXISTS pings (
    ping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    interval_minutes INTEGER DEFAULT 60,
    top_n INTEGER DEFAULT 3,
    last_sent TEXT,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rewards (
    reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    role_id INTEGER,
    criteria TEXT,
    tier INTEGER DEFAULT 0,
    last_applied TEXT
);

COMMIT;
