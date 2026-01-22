-- Migration 006: add topic_templates table to support per-guild and global topic templates
CREATE TABLE IF NOT EXISTS topic_templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER DEFAULT NULL,
    category TEXT NOT NULL,
    template_text TEXT NOT NULL
);
-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_topic_templates_guild_cat ON topic_templates (guild_id, category);
