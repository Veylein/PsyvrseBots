"""
Database Service Layer for Discord Chi Bot
Provides async PostgreSQL operations for persistent data storage
"""

import os
import asyncpg
import json
from typing import Optional, Dict, List, Any
from datetime import datetime

class DatabaseService:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.environ.get("DATABASE_URL")
        
    async def connect(self):
        """Initialize database connection pool"""
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        
        # Initialize schema
        await self.init_schema()
        
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def init_schema(self):
        """Create database tables if they don't exist"""
        with open('db_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
    
    # ============================================
    # USER OPERATIONS
    # ============================================
    
    PSY_USER_ID = 1382187068373074001  # PSY has cross-guild admin access (uses guild_id=0)
    
    def _normalize_guild_id(self, user_id: int, guild_id: int) -> int:
        """Normalize guild_id: PSY user always uses sentinel guild_id=0"""
        return 0 if user_id == self.PSY_USER_ID else guild_id
    
    async def get_user(self, user_id: int, *, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get user data by ID (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            if row:
                return dict(row)
            return None
    
    async def create_or_update_user(self, user_id: int, *, guild_id: int, chi: int = 0, rebirths: int = 0,
                                   milestones_claimed: List[str] = None,
                                   mini_quests: List[str] = None,
                                   active_pet: str = None) -> Dict[str, Any]:
        """Create or update user data (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO users (user_id, guild_id, chi, rebirths, milestones_claimed, mini_quests, active_pet, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    chi = EXCLUDED.chi,
                    rebirths = EXCLUDED.rebirths,
                    milestones_claimed = EXCLUDED.milestones_claimed,
                    mini_quests = EXCLUDED.mini_quests,
                    active_pet = EXCLUDED.active_pet,
                    updated_at = NOW()
                RETURNING *
            """, user_id, guild_id, chi, rebirths, 
            milestones_claimed or [], 
            mini_quests or [], 
            active_pet)
            return dict(row)
    
    async def update_user_chi(self, user_id: int, chi: int, *, guild_id: int) -> None:
        """Update user's chi value (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, guild_id, chi, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    chi = EXCLUDED.chi,
                    updated_at = NOW()
            """, user_id, guild_id, chi)
    
    async def update_user_rebirths(self, user_id: int, rebirths: int, *, guild_id: int) -> None:
        """Update user's rebirth count (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, guild_id, rebirths, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    rebirths = EXCLUDED.rebirths,
                    updated_at = NOW()
            """, user_id, guild_id, rebirths)
    
    async def get_all_users(self, *, guild_id: int) -> Dict[int, Dict[str, Any]]:
        """Get all users for a specific guild"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users WHERE guild_id = $1", guild_id)
            return {row['user_id']: dict(row) for row in rows}
    
    # ============================================
    # INVENTORY OPERATIONS
    # ============================================
    
    async def get_user_inventory(self, user_id: int, *, guild_id: int) -> List[Dict[str, Any]]:
        """Get user's inventory items (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM inventories WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            return [dict(row) for row in rows]
    
    async def add_inventory_item(self, user_id: int, item_name: str, *, guild_id: int, quantity: int = 1, item_level: int = 0) -> None:
        """Add or update inventory item (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            # Ensure user exists first with guild_id
            await conn.execute("""
                INSERT INTO users (user_id, guild_id) VALUES ($1, $2)
                ON CONFLICT (guild_id, user_id) DO NOTHING
            """, user_id, guild_id)
            
            # Add or update inventory
            await conn.execute("""
                INSERT INTO inventories (user_id, guild_id, item_name, quantity, item_level)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id, user_id, item_name) DO UPDATE SET
                    quantity = inventories.quantity + EXCLUDED.quantity,
                    item_level = GREATEST(inventories.item_level, EXCLUDED.item_level)
            """, user_id, guild_id, item_name, quantity, item_level)
    
    async def update_item_level(self, user_id: int, item_name: str, level: int, *, guild_id: int) -> None:
        """Update item level (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE inventories 
                SET item_level = $4
                WHERE user_id = $1 AND guild_id = $2 AND item_name = $3
            """, user_id, guild_id, item_name, level)
    
    # ============================================
    # ARTIFACT OPERATIONS
    # ============================================
    
    async def get_user_artifacts(self, user_id: int, *, guild_id: int) -> List[Dict[str, Any]]:
        """Get user's artifacts (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM artifacts WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            return [dict(row) for row in rows]
    
    async def add_artifact(self, artifact_id: str, user_id: int, tier: str, emoji: str, name: str, *, guild_id: int) -> None:
        """Add artifact to user (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            # Ensure user exists with guild_id
            await conn.execute("""
                INSERT INTO users (user_id, guild_id) VALUES ($1, $2)
                ON CONFLICT (guild_id, user_id) DO NOTHING
            """, user_id, guild_id)
            
            await conn.execute("""
                INSERT INTO artifacts (id, user_id, guild_id, tier, emoji, name)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
            """, artifact_id, user_id, guild_id, tier, emoji, name)
    
    async def remove_artifact(self, artifact_id: str, *, guild_id: int) -> None:
        """Remove artifact (guild-isolated)"""
        # Note: artifacts are global by ID, no user_id to normalize
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM artifacts WHERE id = $1 AND guild_id = $2", artifact_id, guild_id)
    
    # ============================================
    # PET OPERATIONS
    # ============================================
    
    async def get_user_pets(self, user_id: int, *, guild_id: int) -> List[Dict[str, Any]]:
        """Get user's pets (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM pets WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            return [dict(row) for row in rows]
    
    async def add_pet(self, user_id: int, pet_data: Dict[str, Any], *, guild_id: int) -> None:
        """Add pet to user (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            # Ensure user exists
            await conn.execute("""
                INSERT INTO users (user_id, guild_id) VALUES ($1, $2)
                ON CONFLICT (guild_id, user_id) DO NOTHING
            """, user_id, guild_id)
            
            pet_id_str = f"{user_id}_{pet_data['id']}"
            await conn.execute("""
                INSERT INTO pets (id, user_id, guild_id, pet_id, name, nickname, health, max_health, attack, hunger)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    health = EXCLUDED.health,
                    hunger = EXCLUDED.hunger,
                    nickname = EXCLUDED.nickname
            """, pet_id_str, user_id, guild_id, pet_data['id'], pet_data['name'],
            pet_data.get('nickname'), pet_data.get('health', 100),
            pet_data.get('max_health', 100), pet_data.get('attack', 25),
            pet_data.get('hunger', 100))
    
    # ============================================
    # TEAM OPERATIONS
    # ============================================
    
    async def get_team(self, team_id: int, *, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get team data with all related info (guild-isolated)"""
        async with self.pool.acquire() as conn:
            # Get team base data
            team = await conn.fetchrow(
                "SELECT * FROM teams WHERE team_id = $1 AND guild_id = $2",
                team_id, guild_id
            )
            if not team:
                return None
            
            team_dict = dict(team)
            
            # Get members
            members = await conn.fetch(
                "SELECT user_id FROM team_members WHERE team_id = $1 AND guild_id = $2",
                team_id, guild_id
            )
            team_dict['members'] = [m['user_id'] for m in members]
            
            # Get modules
            modules = await conn.fetch(
                "SELECT module_name, level FROM team_modules WHERE team_id = $1 AND guild_id = $2",
                team_id, guild_id
            )
            team_dict['base_modules'] = {m['module_name']: m['level'] for m in modules}
            
            # Get decorations
            decorations = await conn.fetch(
                "SELECT decoration_name FROM team_decorations WHERE team_id = $1 AND guild_id = $2",
                team_id, guild_id
            )
            team_dict['decorations'] = [d['decoration_name'] for d in decorations]
            
            # Get equipment
            equipment = await conn.fetch(
                "SELECT equipment_name FROM team_equipment WHERE team_id = $1 AND guild_id = $2",
                team_id, guild_id
            )
            team_dict['gym_equipment'] = [e['equipment_name'] for e in equipment]
            
            # Get relations
            allies = await conn.fetch("""
                SELECT related_team_id FROM team_relations 
                WHERE team_id = $1 AND guild_id = $2 AND relation_type = 'ally'
            """, team_id, guild_id)
            team_dict['allies'] = [a['related_team_id'] for a in allies]
            
            enemies = await conn.fetch("""
                SELECT related_team_id FROM team_relations 
                WHERE team_id = $1 AND guild_id = $2 AND relation_type = 'enemy'
            """, team_id, guild_id)
            team_dict['enemies'] = [e['related_team_id'] for e in enemies]
            
            # Add duel_stats
            team_dict['duel_stats'] = {
                'wins': team_dict.get('wins', 0),
                'losses': team_dict.get('losses', 0),
                'ties': team_dict.get('ties', 0)
            }
            
            # Normalize field names for consistency with in-memory structure
            if 'leader_id' in team_dict:
                team_dict['leader'] = str(team_dict['leader_id'])
            
            # Convert members to strings for consistency
            team_dict['members'] = [str(m) for m in team_dict.get('members', [])]
            
            return team_dict
    
    async def get_all_teams(self, *, guild_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all teams for a specific guild"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT team_id FROM teams WHERE guild_id = $1", guild_id)
            teams = {}
            for row in rows:
                team_id = row['team_id']
                team_data = await self.get_team(team_id, guild_id=guild_id)
                teams[str(team_id)] = team_data
            return teams
    
    async def create_team(self, team_id: int, name: str, leader_id: int, *, guild_id: int, **kwargs) -> None:
        """Create a new team (guild-isolated)"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO teams (team_id, name, leader_id, guild_id, base_tier, base_color, 
                                  gym_level, arena_level, team_chi, team_score, wins, losses, ties)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (guild_id, team_id) DO NOTHING
            """, team_id, name, leader_id, guild_id,
            kwargs.get('base_tier', 'solo'),
            kwargs.get('base_color', 'white'),
            kwargs.get('gym_level', 0),
            kwargs.get('arena_level', 0),
            kwargs.get('team_chi', 0),
            kwargs.get('team_score', 0),
            kwargs.get('wins', 0),
            kwargs.get('losses', 0),
            kwargs.get('ties', 0))
    
    async def add_team_member(self, team_id: int, user_id: int, *, guild_id: int) -> None:
        """Add member to team (guild-isolated)"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO team_members (team_id, user_id, guild_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, team_id, user_id) DO NOTHING
            """, team_id, user_id, guild_id)
    
    async def update_team_chi(self, team_id: int, chi: int, *, guild_id: int) -> None:
        """Update team's chi value (guild-isolated)"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE teams SET team_chi = $3, updated_at = NOW()
                WHERE team_id = $1 AND guild_id = $2
            """, team_id, guild_id, chi)
    
    # ============================================
    # GARDEN OPERATIONS
    # ============================================
    
    async def get_garden(self, user_id: int, *, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get user's garden data (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            garden = await conn.fetchrow(
                "SELECT * FROM gardens WHERE user_id = $1 AND guild_id = $2",
                user_id, guild_id
            )
            if not garden:
                return None
            
            garden_dict = dict(garden)
            
            # Get plants
            plants = await conn.fetch("""
                SELECT plant_name, planted_at FROM garden_plants 
                WHERE user_id = $1 AND guild_id = $2 AND harvested = FALSE
            """, user_id, guild_id)
            garden_dict['plants'] = [
                {'name': p['plant_name'], 'planted_at': p['planted_at'].timestamp()}
                for p in plants
            ]
            
            # Get watering info
            watering = await conn.fetch("""
                SELECT plant_name, last_watered FROM garden_watering
                WHERE user_id = $1 AND guild_id = $2
            """, user_id, guild_id)
            garden_dict['last_watered'] = {
                w['plant_name']: w['last_watered'].timestamp()
                for w in watering
            }
            
            return garden_dict
    
    async def get_all_gardens(self, *, guild_id: int) -> Dict[int, Dict[str, Any]]:
        """Get all gardens for a specific guild"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM gardens WHERE guild_id = $1", guild_id)
            gardens = {}
            for row in rows:
                user_id = row['user_id']
                garden_data = await self.get_garden(user_id, guild_id=guild_id)
                gardens[user_id] = garden_data
            return gardens
    
    async def create_garden(self, user_id: int, tier: str, *, guild_id: int, level: int = 1) -> None:
        """Create a garden for user (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            # Ensure user exists
            await conn.execute("""
                INSERT INTO users (user_id, guild_id) VALUES ($1, $2)
                ON CONFLICT (guild_id, user_id) DO NOTHING
            """, user_id, guild_id)
            
            await conn.execute("""
                INSERT INTO gardens (user_id, guild_id, tier, level)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    tier = EXCLUDED.tier,
                    level = EXCLUDED.level,
                    updated_at = NOW()
            """, user_id, guild_id, tier, level)
    
    async def create_or_update_garden(self, user_id: int, tier: str, *, guild_id: int, level: int = 1, plants: list = None) -> None:
        """Create or update garden with plants data (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Ensure user exists
                await conn.execute("""
                    INSERT INTO users (user_id, guild_id) VALUES ($1, $2)
                    ON CONFLICT (guild_id, user_id) DO NOTHING
                """, user_id, guild_id)
                
                # Create/update garden
                await conn.execute("""
                    INSERT INTO gardens (user_id, guild_id, tier, level)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET
                        tier = EXCLUDED.tier,
                        level = EXCLUDED.level,
                        updated_at = NOW()
                """, user_id, guild_id, tier, level)
                
                # Clear existing plants and re-add them
                if plants is not None:
                    await conn.execute("DELETE FROM garden_plants WHERE user_id = $1 AND guild_id = $2 AND harvested = FALSE", user_id, guild_id)
                    
                    for plant in plants:
                        if isinstance(plant, dict) and ('name' in plant or 'seed' in plant):
                            plant_name = plant.get('name') or plant.get('seed')
                            planted_at = plant.get('planted_at', plant.get('mature_at', 0))
                            
                            if plant_name and planted_at:
                                try:
                                    planted_time = datetime.fromtimestamp(float(planted_at))
                                    await conn.execute("""
                                        INSERT INTO garden_plants (user_id, guild_id, plant_name, planted_at)
                                        VALUES ($1, $2, $3, $4)
                                    """, user_id, guild_id, plant_name, planted_time)
                                except Exception as e:
                                    print(f"Error adding plant {plant_name} for user {user_id}: {e}")
    
    async def add_garden_plant(self, user_id: int, plant_name: str, planted_at: float, *, guild_id: int) -> None:
        """Add plant to garden (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            planted_time = datetime.fromtimestamp(planted_at)
            await conn.execute("""
                INSERT INTO garden_plants (user_id, guild_id, plant_name, planted_at)
                VALUES ($1, $2, $3, $4)
            """, user_id, guild_id, plant_name, planted_time)
    
    async def harvest_plants(self, user_id: int, *, guild_id: int, plant_name: str = None) -> int:
        """Mark plants as harvested, return count (guild-isolated, PSY uses guild_id=0)"""
        guild_id = self._normalize_guild_id(user_id, guild_id)
        async with self.pool.acquire() as conn:
            if plant_name:
                result = await conn.execute("""
                    UPDATE garden_plants 
                    SET harvested = TRUE
                    WHERE user_id = $1 AND guild_id = $2 AND plant_name = $3 AND harvested = FALSE
                """, user_id, guild_id, plant_name)
            else:
                result = await conn.execute("""
                    UPDATE garden_plants 
                    SET harvested = TRUE
                    WHERE user_id = $1 AND guild_id = $2 AND harvested = FALSE
                """, user_id, guild_id)
            
            return int(result.split()[-1])
    
    # ============================================
    # COMPREHENSIVE DATA SAVE OPERATIONS (DEPRECATED - Use guild-aware methods)
    # ============================================
    
    async def save_all_user_data(self, chi_data: Dict[str, Any]) -> int:
        """DEPRECATED: Use guild-aware methods instead. This ignores guild isolation."""
        raise NotImplementedError("save_all_user_data is deprecated - use guild-aware methods")
        saved_count = 0
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for user_id_str, user_data in chi_data.items():
                    try:
                        user_id = int(user_id_str)
                        
                        # Save main user data
                        await conn.execute("""
                            INSERT INTO users (
                                user_id, chi, rebirths, milestones_claimed, mini_quests, 
                                active_pet, mining_cooldown, garden_inventory, fertilizer_uses, chest, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                            ON CONFLICT (user_id) DO UPDATE SET
                                chi = EXCLUDED.chi,
                                rebirths = EXCLUDED.rebirths,
                                milestones_claimed = EXCLUDED.milestones_claimed,
                                mini_quests = EXCLUDED.mini_quests,
                                active_pet = EXCLUDED.active_pet,
                                mining_cooldown = EXCLUDED.mining_cooldown,
                                garden_inventory = EXCLUDED.garden_inventory,
                                fertilizer_uses = EXCLUDED.fertilizer_uses,
                                chest = EXCLUDED.chest,
                                updated_at = NOW()
                        """, 
                        user_id,
                        user_data.get("chi", 0),
                        user_data.get("rebirths", 0),
                        user_data.get("milestones_claimed", []),
                        user_data.get("mini_quests", []),
                        user_data.get("active_pet"),
                        int(user_data.get("mining_cooldown", 0)),
                        json.dumps(user_data.get("garden_inventory", {})),
                        user_data.get("fertilizer_uses", 0),
                        user_data.get("chest", [])  # JSONB handles list directly
                        )
                        
                        # Clear and save inventory items
                        await conn.execute("DELETE FROM inventories WHERE user_id = $1", user_id)
                        purchased_items = user_data.get("purchased_items", [])
                        item_levels = user_data.get("item_levels", {})
                        
                        for item_name in purchased_items:
                            item_level = item_levels.get(item_name, 0)
                            await conn.execute("""
                                INSERT INTO inventories (user_id, item_name, quantity, item_level)
                                VALUES ($1, $2, 1, $3)
                            """, user_id, item_name, item_level)
                        
                        # Save artifacts
                        if "artifacts" in user_data:
                            await conn.execute("DELETE FROM artifacts WHERE user_id = $1", user_id)
                            for artifact_data in user_data["artifacts"]:
                                await conn.execute("""
                                    INSERT INTO artifacts (id, user_id, tier, emoji, name)
                                    VALUES ($1, $2, $3, $4, $5)
                                    ON CONFLICT (id) DO NOTHING
                                """, 
                                artifact_data["id"],
                                user_id,
                                artifact_data["tier"],
                                artifact_data["emoji"],
                                artifact_data["name"]
                                )
                        
                        # Save pets
                        if "pets" in user_data:
                            await conn.execute("DELETE FROM pets WHERE user_id = $1", user_id)
                            for pet_data in user_data["pets"]:
                                pet_id_str = f"{user_id}_{pet_data['id']}"
                                await conn.execute("""
                                    INSERT INTO pets (id, user_id, pet_id, name, nickname, health, max_health, attack, hunger)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                                """, 
                                pet_id_str,
                                user_id,
                                pet_data["id"],
                                pet_data["name"],
                                pet_data.get("nickname"),
                                pet_data.get("health", 100),
                                pet_data.get("max_health", 100),
                                pet_data.get("attack", 25),
                                pet_data.get("hunger", 100)
                                )
                        
                        saved_count += 1
                    except Exception as e:
                        print(f"Error saving user {user_id_str}: {e}")
                        continue
        
        return saved_count
    
    async def save_all_teams_data(self, teams_data: Dict[str, Any]) -> int:
        """DEPRECATED: Use guild-aware methods instead. This ignores guild isolation."""
        raise NotImplementedError("save_all_teams_data is deprecated - use guild-aware methods")
        saved_count = 0
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                teams = teams_data.get("teams", {})
                
                for team_id_str, team in teams.items():
                    try:
                        team_id = int(team_id_str)
                        
                        # Save team base data
                        await conn.execute("""
                            INSERT INTO teams (
                                team_id, name, leader_id, base_tier, base_color,
                                gym_level, arena_level, team_chi, team_score,
                                wins, losses, ties, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                            ON CONFLICT (team_id) DO UPDATE SET
                                name = EXCLUDED.name,
                                leader_id = EXCLUDED.leader_id,
                                base_tier = EXCLUDED.base_tier,
                                base_color = EXCLUDED.base_color,
                                gym_level = EXCLUDED.gym_level,
                                arena_level = EXCLUDED.arena_level,
                                team_chi = EXCLUDED.team_chi,
                                team_score = EXCLUDED.team_score,
                                wins = EXCLUDED.wins,
                                losses = EXCLUDED.losses,
                                ties = EXCLUDED.ties,
                                updated_at = NOW()
                        """,
                        team_id,
                        team["name"],
                        int(team.get("leader_id", team.get("leader", 0))),  # Handle both field names
                        team.get("base_tier", "solo"),
                        team.get("base_color", "white"),
                        team.get("gym_level", 0),
                        team.get("arena_level", 0),
                        team.get("team_chi", 0),
                        team.get("team_score", 0),
                        team.get("duel_stats", team.get("wins", 0)) if isinstance(team.get("duel_stats"), int) else team.get("duel_stats", {}).get("wins", 0),
                        team.get("duel_stats", team.get("losses", 0)) if isinstance(team.get("duel_stats"), int) else team.get("duel_stats", {}).get("losses", 0),
                        team.get("duel_stats", team.get("ties", 0)) if isinstance(team.get("duel_stats"), int) else team.get("duel_stats", {}).get("ties", 0)
                        )
                        
                        # Clear and save members
                        await conn.execute("DELETE FROM team_members WHERE team_id = $1", team_id)
                        for member_id_str in team.get("members", []):
                            await conn.execute("""
                                INSERT INTO team_members (team_id, user_id)
                                VALUES ($1, $2)
                            """, team_id, int(member_id_str))
                        
                        # Clear and save modules
                        await conn.execute("DELETE FROM team_modules WHERE team_id = $1", team_id)
                        for module_name, level in team.get("base_modules", {}).items():
                            await conn.execute("""
                                INSERT INTO team_modules (team_id, module_name, level)
                                VALUES ($1, $2, $3)
                            """, team_id, module_name, level)
                        
                        # Clear and save decorations
                        await conn.execute("DELETE FROM team_decorations WHERE team_id = $1", team_id)
                        for decoration in team.get("decorations", []):
                            await conn.execute("""
                                INSERT INTO team_decorations (team_id, decoration_name)
                                VALUES ($1, $2)
                            """, team_id, decoration)
                        
                        # Clear and save equipment
                        await conn.execute("DELETE FROM team_equipment WHERE team_id = $1", team_id)
                        for equipment in team.get("gym_equipment", []):
                            await conn.execute("""
                                INSERT INTO team_equipment (team_id, equipment_name)
                                VALUES ($1, $2)
                            """, team_id, equipment)
                        
                        # Clear and save relations
                        await conn.execute("DELETE FROM team_relations WHERE team_id = $1", team_id)
                        for ally_id in team.get("allies", []):
                            await conn.execute("""
                                INSERT INTO team_relations (team_id, related_team_id, relation_type)
                                VALUES ($1, $2, 'ally')
                            """, team_id, ally_id)
                        
                        for enemy_id in team.get("enemies", []):
                            await conn.execute("""
                                INSERT INTO team_relations (team_id, related_team_id, relation_type)
                                VALUES ($1, $2, 'enemy')
                            """, team_id, enemy_id)
                        
                        saved_count += 1
                    except Exception as e:
                        print(f"Error saving team {team_id_str}: {e}")
                        continue
        
        return saved_count
    
    async def save_all_gardens_data(self, gardens_data: Dict[str, Any]) -> int:
        """DEPRECATED: Use guild-aware methods instead. This ignores guild isolation."""
        raise NotImplementedError("save_all_gardens_data is deprecated - use guild-aware methods")
        saved_count = 0
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for user_id_str, garden in gardens_data.items():
                    # Skip non-user-ID keys (like "gardens", "garden_event")
                    if not user_id_str.isdigit():
                        continue
                    
                    try:
                        user_id = int(user_id_str)
                        
                        # Ensure user exists
                        await conn.execute("""
                            INSERT INTO users (user_id) VALUES ($1)
                            ON CONFLICT (user_id) DO NOTHING
                        """, user_id)
                        
                        # Save garden
                        await conn.execute("""
                            INSERT INTO gardens (user_id, tier, level, updated_at)
                            VALUES ($1, $2, $3, NOW())
                            ON CONFLICT (user_id) DO UPDATE SET
                                tier = EXCLUDED.tier,
                                level = EXCLUDED.level,
                                updated_at = NOW()
                        """, user_id, garden["tier"], garden.get("level", 1))
                        
                        # Clear and save plants
                        await conn.execute("DELETE FROM garden_plants WHERE user_id = $1", user_id)
                        for plant in garden.get("plants", []):
                            planted_time = datetime.fromtimestamp(plant["planted_at"])
                            await conn.execute("""
                                INSERT INTO garden_plants (user_id, plant_name, planted_at, harvested)
                                VALUES ($1, $2, $3, FALSE)
                            """, user_id, plant["name"], planted_time)
                        
                        # Clear and save watering data
                        await conn.execute("DELETE FROM garden_watering WHERE user_id = $1", user_id)
                        for plant_name, last_watered in garden.get("last_watered", {}).items():
                            watered_time = datetime.fromtimestamp(last_watered)
                            await conn.execute("""
                                INSERT INTO garden_watering (user_id, plant_name, last_watered)
                                VALUES ($1, $2, $3)
                            """, user_id, plant_name, watered_time)
                        
                        saved_count += 1
                    except Exception as e:
                        print(f"Error saving garden for user {user_id_str}: {e}")
                        continue
        
        return saved_count
    
    async def sync_all_data(self, chi_data: Dict, teams_data: Dict, gardens_data: Dict) -> None:
        """DEPRECATED: Use guild-aware methods instead. This ignores guild isolation."""
        raise NotImplementedError("sync_all_data is deprecated - use guild-aware methods")
        try:
            user_count = await self.save_all_user_data(chi_data)
            team_count = await self.save_all_teams_data(teams_data)
            garden_count = await self.save_all_gardens_data(gardens_data.get("gardens", {}))
            print(f"✅ Synced {user_count} users, {team_count} teams, {garden_count} gardens to database")
        except Exception as e:
            print(f"⚠️ Error syncing all data to database: {e}")
    
    # ============================================
    # SERVER CONFIG OPERATIONS (Multi-Server Support)
    # ============================================
    
    async def get_server_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get server configuration for a guild"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM server_configs WHERE guild_id = $1",
                guild_id
            )
            if row:
                return dict(row)
            return None
    
    async def create_or_update_server_config(self, guild_id: int, **config) -> Dict[str, Any]:
        """Create or update server configuration"""
        async with self.pool.acquire() as conn:
            # Build dynamic UPDATE clause
            set_clauses = []
            params = [guild_id]
            param_num = 2
            
            for key, value in config.items():
                if key in ['admin_role_id', 'log_channel_id', 'garden_channels', 
                          'duel_channels', 'pet_channels', 'world_channels', 
                          'world_roles', 'setup_complete']:
                    set_clauses.append(f"{key} = ${param_num}")
                    params.append(value)
                    param_num += 1
            
            if not set_clauses:
                # No valid config provided, just return existing or create default
                return await self.get_server_config(guild_id) or {}
            
            query = f"""
                INSERT INTO server_configs (guild_id, {', '.join(config.keys())}, updated_at)
                VALUES ($1, {', '.join([f'${i}' for i in range(2, param_num)])}, NOW())
                ON CONFLICT (guild_id) DO UPDATE SET
                    {', '.join(set_clauses)},
                    updated_at = NOW()
                RETURNING *
            """
            
            row = await conn.fetchrow(query, *params)
            return dict(row)
    
    async def is_admin(self, guild_id: int, member) -> bool:
        """Check if member is admin (has admin role or is server administrator)"""
        # Check Discord administrator permission
        if member.guild_permissions.administrator:
            return True
        
        # Check configured admin role
        config = await self.get_server_config(guild_id)
        if config and config.get('admin_role_id'):
            admin_role_id = config['admin_role_id']
            return any(role.id == admin_role_id for role in member.roles)
        
        return False
    
    async def get_guild_user(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data scoped to a specific guild"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE guild_id = $1 AND user_id = $2",
                guild_id, user_id
            )
            if row:
                return dict(row)
            return None
    
    async def get_guild_teams(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all teams for a specific guild"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM teams WHERE guild_id = $1",
                guild_id
            )
            teams = []
            for row in rows:
                team_dict = dict(row)
                # Get full team data
                full_team = await self.get_team(row['team_id'])
                if full_team:
                    teams.append(full_team)
            return teams
    
    async def get_guild_gardens(self, guild_id: int) -> Dict[int, Dict[str, Any]]:
        """Get all gardens for a specific guild"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id FROM gardens WHERE guild_id = $1",
                guild_id
            )
            gardens = {}
            for row in rows:
                user_id = row['user_id']
                garden_data = await self.get_garden(user_id)
                if garden_data:
                    gardens[user_id] = garden_data
            return gardens
    
    async def delete_guild_data(self, guild_id: int) -> Dict[str, int]:
        """
        Delete ALL data for a guild when bot leaves that server.
        Protects PSY admin data (user_id 1382187068373074001).
        Returns stats of deleted rows per table.
        """
        if not guild_id or guild_id == 0:
            print(f"⚠️ Cannot delete data for invalid guild_id: {guild_id}")
            return {}
        
        PSY_USER_ID = 1382187068373074001
        stats = {}
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Delete in reverse dependency order to avoid FK violations
                    
                    # 1. Team-related tables (depend on teams)
                    stats['team_relations'] = int((await conn.execute(
                        "DELETE FROM team_relations WHERE team_id IN (SELECT team_id FROM teams WHERE guild_id = $1)",
                        guild_id
                    )).split()[-1])
                    
                    stats['team_equipment'] = int((await conn.execute(
                        "DELETE FROM team_equipment WHERE team_id IN (SELECT team_id FROM teams WHERE guild_id = $1)",
                        guild_id
                    )).split()[-1])
                    
                    stats['team_decorations'] = int((await conn.execute(
                        "DELETE FROM team_decorations WHERE team_id IN (SELECT team_id FROM teams WHERE guild_id = $1)",
                        guild_id
                    )).split()[-1])
                    
                    stats['team_modules'] = int((await conn.execute(
                        "DELETE FROM team_modules WHERE team_id IN (SELECT team_id FROM teams WHERE guild_id = $1)",
                        guild_id
                    )).split()[-1])
                    
                    stats['team_members'] = int((await conn.execute(
                        "DELETE FROM team_members WHERE team_id IN (SELECT team_id FROM teams WHERE guild_id = $1)",
                        guild_id
                    )).split()[-1])
                    
                    # 2. Teams table
                    stats['teams'] = int((await conn.execute(
                        "DELETE FROM teams WHERE guild_id = $1",
                        guild_id
                    )).split()[-1])
                    
                    # 3. Garden-related tables (depend on gardens)
                    stats['garden_watering'] = int((await conn.execute(
                        "DELETE FROM garden_watering WHERE user_id IN (SELECT user_id FROM gardens WHERE guild_id = $1 AND user_id != $2)",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    stats['garden_plants'] = int((await conn.execute(
                        "DELETE FROM garden_plants WHERE user_id IN (SELECT user_id FROM gardens WHERE guild_id = $1 AND user_id != $2)",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    # 4. Gardens table
                    stats['gardens'] = int((await conn.execute(
                        "DELETE FROM gardens WHERE guild_id = $1 AND user_id != $2",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    # 5. User-dependent tables (depend on users)
                    stats['pets'] = int((await conn.execute(
                        "DELETE FROM pets WHERE user_id IN (SELECT user_id FROM users WHERE guild_id = $1 AND user_id != $2)",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    stats['artifacts'] = int((await conn.execute(
                        "DELETE FROM artifacts WHERE user_id IN (SELECT user_id FROM users WHERE guild_id = $1 AND user_id != $2)",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    stats['inventories'] = int((await conn.execute(
                        "DELETE FROM inventories WHERE user_id IN (SELECT user_id FROM users WHERE guild_id = $1 AND user_id != $2)",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    # 6. Users table (protect PSY!)
                    stats['users'] = int((await conn.execute(
                        "DELETE FROM users WHERE guild_id = $1 AND user_id != $2",
                        guild_id, PSY_USER_ID
                    )).split()[-1])
                    
                    # 7. Server config
                    stats['server_configs'] = int((await conn.execute(
                        "DELETE FROM server_configs WHERE guild_id = $1",
                        guild_id
                    )).split()[-1])
            
            # Log audit trail
            total_deleted = sum(stats.values())
            print(f"🗑️ Guild {guild_id} data deleted: {total_deleted} total rows")
            for table, count in stats.items():
                if count > 0:
                    print(f"   - {table}: {count} rows")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error deleting guild {guild_id} data: {e}")
            raise


# Global instance
db = DatabaseService()
