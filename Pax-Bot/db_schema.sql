-- Discord Chi Bot - PostgreSQL Schema
-- Phase 1: Critical Data (Chi, Teams, Gardens)

-- ============================================
-- USERS TABLE (Chi & Rebirths)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    chi INTEGER DEFAULT 0,
    rebirths INTEGER DEFAULT 0,
    milestones_claimed TEXT[] DEFAULT '{}',
    mini_quests TEXT[] DEFAULT '{}',
    active_pet TEXT DEFAULT NULL,
    mining_cooldown BIGINT DEFAULT 0,
    garden_inventory JSONB DEFAULT '{}',
    fertilizer_uses INTEGER DEFAULT 0,
    chest JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_chi ON users(chi DESC);
CREATE INDEX IF NOT EXISTS idx_users_rebirths ON users(rebirths DESC);

-- ============================================
-- INVENTORIES TABLE (Purchased Items)
-- ============================================
CREATE TABLE IF NOT EXISTS inventories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    item_level INTEGER DEFAULT 0,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, item_name)
);

CREATE INDEX IF NOT EXISTS idx_inventories_user ON inventories(user_id);

-- ============================================
-- ARTIFACTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    tier TEXT NOT NULL,
    emoji TEXT NOT NULL,
    name TEXT NOT NULL,
    claimed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_user ON artifacts(user_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_tier ON artifacts(tier);

-- ============================================
-- PETS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS pets (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    pet_id TEXT NOT NULL,
    name TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    health INTEGER DEFAULT 100,
    max_health INTEGER DEFAULT 100,
    attack INTEGER DEFAULT 25,
    hunger INTEGER DEFAULT 100,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pets_user ON pets(user_id);

-- ============================================
-- TEAMS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS teams (
    team_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    leader_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    base_tier TEXT DEFAULT 'solo',
    base_color TEXT DEFAULT 'white',
    gym_level INTEGER DEFAULT 0,
    arena_level INTEGER DEFAULT 0,
    team_chi INTEGER DEFAULT 0,
    team_score INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_leader ON teams(leader_id);
CREATE INDEX IF NOT EXISTS idx_teams_score ON teams(team_score DESC);
CREATE INDEX IF NOT EXISTS idx_teams_chi ON teams(team_chi DESC);

-- ============================================
-- TEAM MEMBERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);

-- ============================================
-- TEAM MODULES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS team_modules (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    level INTEGER DEFAULT 0,
    UNIQUE(team_id, module_name)
);

-- ============================================
-- TEAM DECORATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS team_decorations (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    decoration_name TEXT NOT NULL,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- TEAM EQUIPMENT TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS team_equipment (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    equipment_name TEXT NOT NULL,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- TEAM RELATIONS TABLE (Allies/Enemies)
-- ============================================
CREATE TABLE IF NOT EXISTS team_relations (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    related_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('ally', 'enemy')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, related_team_id)
);

-- ============================================
-- GARDENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS gardens (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    tier TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- GARDEN PLANTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS garden_plants (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES gardens(user_id) ON DELETE CASCADE,
    plant_name TEXT NOT NULL,
    planted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    harvested BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_garden_plants_user ON garden_plants(user_id);
CREATE INDEX IF NOT EXISTS idx_garden_plants_harvested ON garden_plants(user_id, harvested);

-- ============================================
-- GARDEN WATERING TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS garden_watering (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES gardens(user_id) ON DELETE CASCADE,
    plant_name TEXT NOT NULL,
    last_watered TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(user_id, plant_name)
);
