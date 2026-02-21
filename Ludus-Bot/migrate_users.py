
import asyncio
import json
import logging
import os
from pathlib import Path
from utils.database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

DATA_DIR = Path("data") / "users"

async def migrate():
    print("Starting migration...")
    
    # Initialize schema first
    await asyncio.to_thread(db.initialize_schema)
    
    if not DATA_DIR.exists():
        print(f"No user data directory found at {DATA_DIR}")
        return

    files = list(DATA_DIR.glob("*.json"))
    print(f"Found {len(files)} user files to migrate.")

    for i, file_path in enumerate(files):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            user_id = int(data.get("user_id", file_path.stem))
            username = data.get("username", "unknown")
            
            # Upsert User
            await asyncio.to_thread(db.upsert_user, user_id, username)
            
            # Migrate Stats
            stats = data.get("stats", {})
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    await asyncio.to_thread(db.update_stat, user_id, key, value)
            
            # Migrate Minigame Stats (flattened)
            minigames = data.get("minigames", {}).get("by_game", {})
            for game, game_stats in minigames.items():
                for stat, val in game_stats.items():
                    stat_key = f"minigame_{game}_{stat}"
                    if isinstance(val, (int, float)):
                        await asyncio.to_thread(db.update_stat, user_id, stat_key, val)
            
            # Migrate Recent Activity
            activities = data.get("activity", {}).get("recent", [])
            for act in activities[:10]:
                t = act.get("time")
                atype = act.get("type", "unknown")
                aname = act.get("name", "unknown")
                
                # Use synchronous wrapper in async context
                def _log():
                    db.log_activity(user_id, atype, aname, t)
                await asyncio.to_thread(_log)

            # Migrate Game States
            games = data.get("games", {})
            for game_name, game_data in games.items():
                # game_data is likely {"state": ..., "updated_at": ...}
                state = game_data.get("state", {})
                await asyncio.to_thread(db.save_game_state, user_id, game_name, json.dumps(state))

            if (i + 1) % 10 == 0:
                print(f"Migrated {i + 1}/{len(files)} users...")
                
        except Exception as e:
            print(f"Failed to migrate {file_path.name}: {e}")

    print("Migration complete.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if DB credentials exist
    if not os.getenv("DATABASE_HOST"):
        print("Error: DATABASE_HOST not set in .env")
        exit(1)
        
    asyncio.run(migrate())
