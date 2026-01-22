-- Migration 007: add channel_id column to topic_templates for channel-scoped templates
ALTER TABLE topic_templates ADD COLUMN channel_id INTEGER DEFAULT NULL;

-- Create index to find channel/guild templates quickly
CREATE INDEX IF NOT EXISTS idx_topic_templates_guild_channel_cat ON topic_templates (guild_id, channel_id, category);
