-- ============================================
-- DISCORD CHI BOT - MULTI-SERVER MIGRATION
-- ============================================
-- This migration adds guild_id to all tables to enable per-server data isolation
-- Phase 1: Add nullable guild_id columns
-- Phase 2: Backfill with default guild
-- Phase 3: Update constraints and make NOT NULL
-- Phase 4: Create server_configs table

-- ============================================
-- PHASE 1: ADD NULLABLE GUILD_ID COLUMNS
-- ============================================

-- Add guild_id to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to inventories table
ALTER TABLE inventories ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to artifacts table
ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to pets table
ALTER TABLE pets ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to teams table
ALTER TABLE teams ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to team_members table
ALTER TABLE team_members ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to team_modules table
ALTER TABLE team_modules ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to team_decorations table
ALTER TABLE team_decorations ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to team_equipment table
ALTER TABLE team_equipment ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to team_relations table
ALTER TABLE team_relations ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to gardens table
ALTER TABLE gardens ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to garden_plants table
ALTER TABLE garden_plants ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- Add guild_id to garden_watering table
ALTER TABLE garden_watering ADD COLUMN IF NOT EXISTS guild_id BIGINT;

-- ============================================
-- PHASE 2: BACKFILL WITH DEFAULT GUILD
-- ============================================
-- Use 1382187068373074001 as default guild ID (PSY's main server)

UPDATE users SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE inventories SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE artifacts SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE pets SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE teams SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE team_members SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE team_modules SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE team_decorations SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE team_equipment SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE team_relations SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE gardens SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE garden_plants SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;
UPDATE garden_watering SET guild_id = 1382187068373074001 WHERE guild_id IS NULL;

-- ============================================
-- PHASE 3: MAKE GUILD_ID NOT NULL & UPDATE CONSTRAINTS
-- ============================================

-- Make guild_id NOT NULL
ALTER TABLE users ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE inventories ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE artifacts ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE pets ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE teams ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE team_members ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE team_modules ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE team_decorations ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE team_equipment ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE team_relations ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE gardens ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE garden_plants ALTER COLUMN guild_id SET NOT NULL;
ALTER TABLE garden_watering ALTER COLUMN guild_id SET NOT NULL;

-- Drop old unique constraints (PRESERVE ALL PRIMARY KEYS!)
ALTER TABLE inventories DROP CONSTRAINT IF EXISTS inventories_user_id_item_name_key;
ALTER TABLE team_members DROP CONSTRAINT IF EXISTS team_members_team_id_user_id_key;
ALTER TABLE team_modules DROP CONSTRAINT IF EXISTS team_modules_team_id_module_name_key;
ALTER TABLE team_relations DROP CONSTRAINT IF EXISTS team_relations_team_id_related_team_id_key;
ALTER TABLE garden_watering DROP CONSTRAINT IF EXISTS garden_watering_user_id_plant_name_key;
ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_name_key;

-- Add composite unique constraints for guild-scoped uniqueness
-- NOTE: Primary keys remain unchanged!
ALTER TABLE users ADD CONSTRAINT users_guild_user_unique UNIQUE (guild_id, user_id);
ALTER TABLE gardens ADD CONSTRAINT gardens_guild_user_unique UNIQUE (guild_id, user_id);
ALTER TABLE inventories ADD CONSTRAINT inventories_guild_user_item_unique UNIQUE (guild_id, user_id, item_name);
ALTER TABLE team_members ADD CONSTRAINT team_members_guild_team_user_unique UNIQUE (guild_id, team_id, user_id);
ALTER TABLE team_modules ADD CONSTRAINT team_modules_guild_team_module_unique UNIQUE (guild_id, team_id, module_name);
ALTER TABLE team_relations ADD CONSTRAINT team_relations_guild_team_related_unique UNIQUE (guild_id, team_id, related_team_id);
ALTER TABLE garden_watering ADD CONSTRAINT garden_watering_guild_user_plant_unique UNIQUE (guild_id, user_id, plant_name);
ALTER TABLE teams ADD CONSTRAINT teams_guild_name_unique UNIQUE (guild_id, name);

-- Create indexes for guild_id lookups
CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id);
CREATE INDEX IF NOT EXISTS idx_inventories_guild ON inventories(guild_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_guild ON artifacts(guild_id);
CREATE INDEX IF NOT EXISTS idx_pets_guild ON pets(guild_id);
CREATE INDEX IF NOT EXISTS idx_teams_guild ON teams(guild_id);
CREATE INDEX IF NOT EXISTS idx_team_members_guild ON team_members(guild_id);
CREATE INDEX IF NOT EXISTS idx_gardens_guild ON gardens(guild_id);
CREATE INDEX IF NOT EXISTS idx_garden_plants_guild ON garden_plants(guild_id);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_users_guild_user ON users(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_teams_guild_leader ON teams(guild_id, leader_id);
CREATE INDEX IF NOT EXISTS idx_gardens_guild_user ON gardens(guild_id, user_id);

-- ============================================
-- PHASE 4: CREATE SERVER_CONFIGS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS server_configs (
    guild_id BIGINT PRIMARY KEY,
    admin_role_id BIGINT DEFAULT NULL,
    log_channel_id BIGINT DEFAULT NULL,
    garden_channels BIGINT[] DEFAULT '{}',
    duel_channels BIGINT[] DEFAULT '{}',
    pet_channels BIGINT[] DEFAULT '{}',
    world_channels JSONB DEFAULT '{}',
    world_roles JSONB DEFAULT '{}',
    setup_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_server_configs_setup ON server_configs(setup_complete);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these to verify migration success:
-- SELECT guild_id, COUNT(*) FROM users GROUP BY guild_id;
-- SELECT guild_id, COUNT(*) FROM teams GROUP BY guild_id;
-- SELECT guild_id, COUNT(*) FROM gardens GROUP BY guild_id;
-- SELECT * FROM server_configs;
