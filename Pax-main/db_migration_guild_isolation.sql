-- Guild Isolation Migration
-- Adds composite unique constraints and indexes for guild-level data isolation
-- Non-destructive: keeps existing PRIMARY KEYs intact

-- ============================================
-- USERS TABLE
-- ============================================
-- Drop existing constraint if it exists, then add composite unique constraint
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_guild_user_unique;
ALTER TABLE users ADD CONSTRAINT users_guild_user_unique UNIQUE (guild_id, user_id);

-- Add performance index
CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id);
CREATE INDEX IF NOT EXISTS idx_users_guild_chi ON users(guild_id, chi DESC);

-- ============================================
-- INVENTORIES TABLE
-- ============================================
-- Update unique constraint to include guild_id
ALTER TABLE inventories DROP CONSTRAINT IF EXISTS inventories_user_id_item_name_key;
ALTER TABLE inventories DROP CONSTRAINT IF EXISTS inventories_guild_user_item_unique;
ALTER TABLE inventories ADD CONSTRAINT inventories_guild_user_item_unique UNIQUE (guild_id, user_id, item_name);

CREATE INDEX IF NOT EXISTS idx_inventories_guild_user ON inventories(guild_id, user_id);

-- ============================================
-- ARTIFACTS TABLE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_artifacts_guild_user ON artifacts(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_guild ON artifacts(guild_id);

-- ============================================
-- PETS TABLE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_pets_guild_user ON pets(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_pets_guild ON pets(guild_id);

-- ============================================
-- TEAMS TABLE
-- ============================================
-- Update name uniqueness to be per-guild
ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_name_key;
ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_guild_name_unique;
ALTER TABLE teams ADD CONSTRAINT teams_guild_name_unique UNIQUE (guild_id, name);

CREATE INDEX IF NOT EXISTS idx_teams_guild ON teams(guild_id);
CREATE INDEX IF NOT EXISTS idx_teams_guild_score ON teams(guild_id, team_score DESC);

-- ============================================
-- TEAM MEMBERS TABLE
-- ============================================
-- Update unique constraint to include guild_id
ALTER TABLE team_members DROP CONSTRAINT IF EXISTS team_members_team_id_user_id_key;
ALTER TABLE team_members DROP CONSTRAINT IF EXISTS team_members_guild_team_user_unique;
ALTER TABLE team_members ADD CONSTRAINT team_members_guild_team_user_unique UNIQUE (guild_id, team_id, user_id);

CREATE INDEX IF NOT EXISTS idx_team_members_guild ON team_members(guild_id);
CREATE INDEX IF NOT EXISTS idx_team_members_guild_user ON team_members(guild_id, user_id);

-- ============================================
-- GARDENS TABLE
-- ============================================
-- Gardens already uses user_id as PRIMARY KEY, add guild index
CREATE INDEX IF NOT EXISTS idx_gardens_guild ON gardens(guild_id);
CREATE INDEX IF NOT EXISTS idx_gardens_guild_user ON gardens(guild_id, user_id);

-- ============================================
-- GARDEN PLANTS TABLE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_garden_plants_guild ON garden_plants(guild_id);
CREATE INDEX IF NOT EXISTS idx_garden_plants_guild_user ON garden_plants(guild_id, user_id);

-- ============================================
-- PSY USER HANDLING
-- ============================================
-- PSY user (1382187068373074001) will have guild_id = 0 as a sentinel value
-- This allows cross-guild admin access while maintaining data isolation
-- The db_service will check: if user_id == PSY_ID, ignore guild_id filter
