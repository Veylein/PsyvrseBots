-- Migration: add event channel/role and winner role columns
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- Add columns to events table for channel_id, event_role_id, winner_role_id, winner_expires
ALTER TABLE events ADD COLUMN channel_id INTEGER;
ALTER TABLE events ADD COLUMN event_role_id INTEGER;
ALTER TABLE events ADD COLUMN winner_role_id INTEGER;
ALTER TABLE events ADD COLUMN winner_expires TEXT;

COMMIT;
