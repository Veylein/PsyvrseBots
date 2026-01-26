"""
Migration Script: JSON to PostgreSQL
Backfills existing JSON data into the database
"""

import asyncio
import json
import os
from datetime import datetime
from db_service import db

async def migrate_chi_data():
    """Migrate chi_data.json to database"""
    print("📊 Migrating user chi data...")
    
    try:
        with open('chi_data.json', 'r') as f:
            chi_data = json.load(f)
    except FileNotFoundError:
        print("⚠️  chi_data.json not found, skipping...")
        return
    
    user_count = 0
    item_count = 0
    artifact_count = 0
    pet_count = 0
    
    for user_id_str, user_data in chi_data.items():
        user_id = int(user_id_str)
        
        # Create/update user
        await db.create_or_update_user(
            user_id=user_id,
            chi=user_data.get('chi', 0),
            rebirths=user_data.get('rebirths', 0),
            milestones_claimed=user_data.get('milestones_claimed', []),
            mini_quests=user_data.get('mini_quests', []),
            active_pet=user_data.get('active_pet')
        )
        user_count += 1
        
        # Migrate purchased items
        for item_name in user_data.get('purchased_items', []):
            item_level = user_data.get('item_levels', {}).get(item_name, 0)
            await db.add_inventory_item(user_id, item_name, quantity=1, item_level=item_level)
            item_count += 1
        
        # Migrate artifacts
        for artifact in user_data.get('artifacts', []):
            await db.add_artifact(
                artifact_id=artifact['id'],
                user_id=user_id,
                tier=artifact['tier'],
                emoji=artifact['emoji'],
                name=artifact['name']
            )
            artifact_count += 1
        
        # Migrate pets
        for pet in user_data.get('pets', []):
            await db.add_pet(user_id, pet)
            pet_count += 1
    
    print(f"✅ Migrated {user_count} users")
    print(f"✅ Migrated {item_count} inventory items")
    print(f"✅ Migrated {artifact_count} artifacts")
    print(f"✅ Migrated {pet_count} pets")


async def migrate_teams_data():
    """Migrate teams_data.json to database"""
    print("\n👥 Migrating teams data...")
    
    try:
        with open('teams_data.json', 'r') as f:
            teams_data = json.load(f)
    except FileNotFoundError:
        print("⚠️  teams_data.json not found, skipping...")
        return
    
    team_count = 0
    member_count = 0
    
    teams = teams_data.get('teams', {})
    for team_id_str, team_data in teams.items():
        team_id = int(team_id_str)
        
        # Create team
        duel_stats = team_data.get('duel_stats', {})
        await db.create_team(
            team_id=team_id,
            name=team_data['name'],
            leader_id=int(team_data['leader']),
            base_tier=team_data.get('base_tier', 'solo'),
            base_color=team_data.get('base_color', 'white'),
            gym_level=team_data.get('gym_level', 0),
            arena_level=team_data.get('arena_level', 0),
            team_chi=team_data.get('team_chi', 0),
            team_score=team_data.get('team_score', 0),
            wins=duel_stats.get('wins', 0),
            losses=duel_stats.get('losses', 0),
            ties=duel_stats.get('ties', 0)
        )
        team_count += 1
        
        # Add members
        for member_id in team_data.get('members', []):
            await db.add_team_member(team_id, int(member_id))
            member_count += 1
        
        # Add modules
        async with db.pool.acquire() as conn:
            for module_name, level in team_data.get('base_modules', {}).items():
                await conn.execute("""
                    INSERT INTO team_modules (team_id, module_name, level)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (team_id, module_name) DO UPDATE SET level = EXCLUDED.level
                """, team_id, module_name, level)
        
        # Add decorations
        async with db.pool.acquire() as conn:
            for decoration in team_data.get('decorations', []):
                await conn.execute("""
                    INSERT INTO team_decorations (team_id, decoration_name)
                    VALUES ($1, $2)
                """, team_id, decoration)
        
        # Add equipment
        async with db.pool.acquire() as conn:
            for equipment in team_data.get('gym_equipment', []):
                await conn.execute("""
                    INSERT INTO team_equipment (team_id, equipment_name)
                    VALUES ($1, $2)
                """, team_id, equipment)
        
        # Add relations
        async with db.pool.acquire() as conn:
            for ally_id in team_data.get('allies', []):
                await conn.execute("""
                    INSERT INTO team_relations (team_id, related_team_id, relation_type)
                    VALUES ($1, $2, 'ally')
                    ON CONFLICT (team_id, related_team_id) DO NOTHING
                """, team_id, ally_id)
            
            for enemy_id in team_data.get('enemies', []):
                await conn.execute("""
                    INSERT INTO team_relations (team_id, related_team_id, relation_type)
                    VALUES ($1, $2, 'enemy')
                    ON CONFLICT (team_id, related_team_id) DO NOTHING
                """, team_id, enemy_id)
    
    print(f"✅ Migrated {team_count} teams")
    print(f"✅ Migrated {member_count} team members")


async def migrate_gardens_data():
    """Migrate gardens_data.json to database"""
    print("\n🌱 Migrating gardens data...")
    
    try:
        with open('gardens_data.json', 'r') as f:
            gardens_data = json.load(f)
    except FileNotFoundError:
        print("⚠️  gardens_data.json not found, skipping...")
        return
    
    garden_count = 0
    plant_count = 0
    
    gardens = gardens_data.get('gardens', {})
    for user_id_str, garden_data in gardens.items():
        user_id = int(user_id_str)
        
        # Create garden
        await db.create_garden(
            user_id=user_id,
            tier=garden_data['tier'],
            level=garden_data.get('level', 1)
        )
        garden_count += 1
        
        # Add plants
        for plant in garden_data.get('plants', []):
            await db.add_garden_plant(
                user_id=user_id,
                plant_name=plant['name'],
                planted_at=plant['planted_at']
            )
            plant_count += 1
        
        # Add watering info
        async with db.pool.acquire() as conn:
            for plant_name, timestamp in garden_data.get('last_watered', {}).items():
                watered_time = datetime.fromtimestamp(timestamp)
                await conn.execute("""
                    INSERT INTO garden_watering (user_id, plant_name, last_watered)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, plant_name) DO UPDATE SET
                        last_watered = EXCLUDED.last_watered
                """, user_id, plant_name, watered_time)
    
    print(f"✅ Migrated {garden_count} gardens")
    print(f"✅ Migrated {plant_count} plants")


async def verify_migration():
    """Verify data was migrated correctly"""
    print("\n🔍 Verifying migration...")
    
    async with db.pool.acquire() as conn:
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        inventory_count = await conn.fetchval("SELECT COUNT(*) FROM inventories")
        artifact_count = await conn.fetchval("SELECT COUNT(*) FROM artifacts")
        pet_count = await conn.fetchval("SELECT COUNT(*) FROM pets")
        team_count = await conn.fetchval("SELECT COUNT(*) FROM teams")
        garden_count = await conn.fetchval("SELECT COUNT(*) FROM gardens")
        plant_count = await conn.fetchval("SELECT COUNT(*) FROM garden_plants")
        
        print(f"\n📊 Database Contents:")
        print(f"   Users: {user_count}")
        print(f"   Inventory Items: {inventory_count}")
        print(f"   Artifacts: {artifact_count}")
        print(f"   Pets: {pet_count}")
        print(f"   Teams: {team_count}")
        print(f"   Gardens: {garden_count}")
        print(f"   Plants: {plant_count}")


async def main():
    """Run migration"""
    print("🚀 Starting Database Migration")
    print("=" * 50)
    
    # Connect to database
    await db.connect()
    
    try:
        # Run migrations in order
        await migrate_chi_data()
        await migrate_teams_data()
        await migrate_gardens_data()
        
        # Verify
        await verify_migration()
        
        print("\n" + "=" * 50)
        print("✅ Migration Complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
