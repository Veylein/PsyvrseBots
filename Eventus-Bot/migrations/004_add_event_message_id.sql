-- Migration: add message_id column to events
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

ALTER TABLE events ADD COLUMN message_id INTEGER;

COMMIT;
