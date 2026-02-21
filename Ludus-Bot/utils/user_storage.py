"""
user_storage.py - Database-backed user storage
=====================================================================

HOW IT WORKS
------------
Replaces the old JSON file system with direct database calls via the DatabaseManager.
Maintains the same async interface for compatibility with existing cogs.

"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from .database import db

logger = logging.getLogger("LudusUserStorage")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def get_user(user_id: int, username: str | None = None) -> dict:
    """Return user data dict (creates DB entry if missing)."""
    
    def _do():
        data = db.get_user_data(user_id)
        if not data:
            # Create user if missing
            db.upsert_user(int(user_id), username or "unknown")
            # Return empty struct, next call will have data or we can construct it
            return {
                "user_id": int(user_id),
                "username": username or "unknown",
                "stats": {},
                "minigames": {"by_game": {}, "recent_plays": []},
                "activity": {"counts": {}, "by_name": {}, "recent": []},
                "games": {},
                "meta": {
                    "created_at": _now(),
                    "updated_at": _now(),
                    "last_active": _now()
                }
            }
        
        # If stats keys are missing, add defaults? 
        # The legacy code did this by merging with template.
        # DB calls handle missing keys gracefully (returns 0 or None usually).
        # We need to ensure the structure matches what cogs expect.
        if "stats" not in data:
            data["stats"] = {}
        if "games" not in data:
            data["games"] = {}
        if "minigames" not in data:
            data["minigames"] = {"by_game": {}, "recent_plays": []}
        if "activity" not in data:
            data["activity"] = {"counts": {}, "by_name": {}, "recent": []}
        if "meta" not in data:
            data["meta"] = {"created_at": _now(), "updated_at": _now(), "last_active": _now()}
            
        return data

    return await asyncio.to_thread(_do)


async def touch_user(user_id: int, username: str | None = None) -> None:
    """
    Ensure user row exists and refresh last_active + messages_sent counter.
    Call this on every incoming message.
    """
    def _do():
        db.upsert_user(int(user_id), username or "unknown")
        # Increment messages_sent stat
        db.increment_stat(int(user_id), "messages_sent")

    await asyncio.to_thread(_do)


async def record_activity(user_id: int, username: str | None,
                          activity_type: str, name: str,
                          extra: dict | None = None) -> None:
    """Record a command / interaction in the user's activity log."""
    def _do():
        db.upsert_user(int(user_id), username or "unknown")
        db.log_activity(int(user_id), activity_type, name)
        db.increment_stat(int(user_id), "commands_used")

    await asyncio.to_thread(_do)


async def record_minigame_result(user_id: int, game_name: str, result: str,
                                  coins: int = 0, username: str | None = None) -> None:
    """
    Record a minigame play.
    result: 'win' | 'loss' | 'draw'
    """
    def _do():
        uid = int(user_id)
        if username:
            db.upsert_user(uid, username)
        
        # General stats
        db.increment_stat(uid, "minigames_played")
        if result == "win":
            db.increment_stat(uid, "minigames_won")
        
        # Per-game stats (flattened)
        base_key = f"minigame_{game_name}"
        db.increment_stat(uid, f"{base_key}_played")
        
        if result == "win":
            db.increment_stat(uid, f"{base_key}_wins")
        elif result == "loss":
            db.increment_stat(uid, f"{base_key}_losses")
        else:
            db.increment_stat(uid, f"{base_key}_draws")
            
        if coins > 0:
            # We assume total_coins_earned is tracked
            # And potentially a per-game coins stat
            db.increment_stat(uid, f"{base_key}_coins", coins)
            db.increment_stat(uid, "total_coins_earned", coins)

        # Log activity
        db.log_activity(uid, "minigame", f"{game_name}:{result}")

    await asyncio.to_thread(_do)


async def increment_stat(user_id: int, stat_name: str,
                          amount: int = 1, username: str | None = None) -> None:
    """Increment any numeric field under stats."""
    def _do():
        uid = int(user_id)
        if username:
            db.upsert_user(uid, username)
        db.increment_stat(uid, stat_name, amount)

    await asyncio.to_thread(_do)


async def set_stat(user_id: int, stat_name: str,
                   value, username: str | None = None) -> None:
    """Set any field under stats to an explicit value."""
    def _do():
        uid = int(user_id)
        if username:
            db.upsert_user(uid, username)
        db.update_stat(uid, stat_name, value)

    await asyncio.to_thread(_do)


async def record_game_state(user_id: int, username: str | None,
                             game_name: str, state: dict) -> None:
    """Store a game-state snapshot for a user."""
    def _do():
        uid = int(user_id)
        if username:
            db.upsert_user(uid, username)
        
        if hasattr(db, 'save_game_state'):
            db.save_game_state(uid, game_name, json.dumps(state))

    await asyncio.to_thread(_do)


# ---------------------------------------------------------------------------
# Backwards-compatibility stubs
# ---------------------------------------------------------------------------

def init_user_storage_worker(loop=None):
    pass

async def flush_user_storage_queue():
    pass

async def enqueue_user_storage(func, *args, **kwargs):
    await asyncio.to_thread(func, *args, **kwargs)

# ---------------------------------------------------------------------------
# Synchronous Support (Legacy)
# ---------------------------------------------------------------------------

def _sync_get_user(user_id: int, username: str | None = None) -> dict:
    # Synchronous version using blocking DB calls
    data = db.get_user_data(int(user_id))
    if not data:
        db.upsert_user(int(user_id), username or "unknown")
        return {
            "user_id": int(user_id), 
            "username": username or "unknown", 
            "stats": {}, 
            "minigames": {"by_game": {}, "recent_plays": []}, 
            "activity": {"counts": {}, "by_name": {}, "recent": []}, 
            "games": {}, 
            "meta": {"created_at": _now(), "updated_at": _now(), "last_active": _now()}
        }
    
    # Fill missing structures
    if "stats" not in data: data["stats"] = {}
    if "games" not in data: data["games"] = {}
    if "minigames" not in data: data["minigames"] = {"by_game": {}, "recent_plays": []}
    if "activity" not in data: data["activity"] = {"counts": {}, "by_name": {}, "recent": []}
    if "meta" not in data: data["meta"] = {"created_at": _now(), "updated_at": _now(), "last_active": _now()}

    return data

def _sync_save_user(data: dict) -> None:
    # Partial save support for legacy code manipulating dicts
    uid = int(data.get("user_id", 0))
    if not uid: return
    
    # Save specific fields if they exist
    if "username" in data:
        db.upsert_user(uid, data["username"])
        
    if "stats" in data:
        for k, v in data["stats"].items():
            if isinstance(v, (int, float)):
                db.update_stat(uid, k, v)
            
    if "games" in data:
        for k, v in data["games"].items():
            if hasattr(db, 'save_game_state'):
                db.save_game_state(uid, k, json.dumps(v))

load_user = _sync_get_user
load_user_simple = _sync_get_user
save_user = _sync_save_user
user_file = lambda uid: Path(f"DB_{uid}") # Dummy path object
get_user_file_simple = lambda uid: f"DB:{uid}" # Mock path string
save_user_simple = lambda uid, d: _sync_save_user({**d, "user_id": uid})
