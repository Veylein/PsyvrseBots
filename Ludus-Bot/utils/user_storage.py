"""
user_storage.py  -  Per-user JSON files in data/users/{user_id}.json
=====================================================================

HOW IT WORKS
------------
Every Discord user gets their own file: data/users/123456789.json
The file is created on their FIRST interaction (message, command, game).
All reads/writes run in a thread pool so they never block the event loop.
No batch queue - every save is direct and immediate for reliability.

FILE STRUCTURE
--------------
{
    "user_id": 123456789,
    "username": "playerName",
    "stats": {
        "messages_sent": 0,
        "commands_used": 0,
        "minigames_played": 0,
        "minigames_won": 0,
        ...  (all numeric fields from profile_template.json)
    },
    "minigames": {
        "by_game": {
            "wordle": {"played": 0, "wins": 0, "losses": 0, "draws": 0, "coins": 0}
        },
        "recent_plays": []
    },
    "activity": {
        "counts": {},
        "by_name": {},
        "recent": []
    },
    "games": {},
    "meta": {
        "created_at": "...",
        "updated_at": "...",
        "last_active": "..."
    }
}

USAGE
-----
from utils import user_storage

# Ensure file exists + update last_active (call on every message):
await user_storage.touch_user(user_id, username)

# Record a minigame result:
await user_storage.record_minigame_result(user_id, "wordle", "win", coins=10, username="name")

# Record a command/interaction:
await user_storage.record_activity(user_id, username, "command", "profile")

# Increment any stat:
await user_storage.increment_stat(user_id, "tictactoe_wins", username=username)

# Read user data:
data = await user_storage.get_user(user_id)
"""

import asyncio
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT          = Path(__file__).resolve().parents[1]
DATA_DIR      = ROOT / "data"
USERS_DIR     = DATA_DIR / "users"
TEMPLATE_FILE = DATA_DIR / "profile_template.json"

# Ensure directory exists at import time
USERS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Per-user threading locks (prevent concurrent writes to the same file)
# ---------------------------------------------------------------------------

_locks: dict[int, threading.Lock] = {}
_locks_mutex = threading.Lock()


def _get_lock(user_id: int) -> threading.Lock:
    with _locks_mutex:
        if user_id not in _locks:
            _locks[user_id] = threading.Lock()
        return _locks[user_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_path(user_id: int) -> Path:
    return USERS_DIR / f"{user_id}.json"


def _load_template() -> dict:
    """Load profile_template.json, return numeric-stat fields only."""
    try:
        if TEMPLATE_FILE.exists():
            raw = json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
            # Strip non-stat fields that don't belong in the stats sub-dict
            for k in ("_comment", "created_at", "coins_balance", "fishing_stats",
                      "farming_stats", "most_played_games", "most_played_with",
                      "inventory", "badges", "user_id", "username", "meta"):
                raw.pop(k, None)
            return raw
    except Exception as e:
        print(f"[user_storage] template load error: {e}", file=sys.stderr)
    return {}


def _make_default(user_id: int, username: str | None) -> dict:
    """Build a brand-new user document."""
    now = _now()
    return {
        "user_id": user_id,
        "username": username or "unknown",
        "stats": _load_template(),
        "minigames": {
            "by_game": {},
            "recent_plays": []
        },
        "activity": {
            "counts": {},
            "by_name": {},
            "recent": []
        },
        "games": {},
        "meta": {
            "created_at": now,
            "updated_at": now,
            "last_active": now
        }
    }


# ---------------------------------------------------------------------------
# Synchronous read / write  (always called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _sync_load(user_id: int, username: str | None = None) -> dict:
    """
    Load user document, creating the file from template if it does not exist.
    This is a BLOCKING call - always wrap with asyncio.to_thread.
    """
    path = _user_path(int(user_id))
    lock = _get_lock(int(user_id))

    with lock:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                # Back-fill any new stats keys that were added to the template
                template_stats = _load_template()
                template_stats.pop("_comment", None)
                stats = data.setdefault("stats", {})
                for k, v in template_stats.items():
                    if k not in stats:
                        stats[k] = v
                return data
            except Exception:
                pass  # corrupted - fall through to recreate

        # File missing or corrupted: create it right now
        data = _make_default(int(user_id), username)
        _atomic_write(path, data)
        return data


def _atomic_write(path: Path, data: dict) -> None:
    """Write dict to path atomically using a .tmp file."""
    tmp = path.with_suffix(".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))
    except Exception as e:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        print(f"[user_storage] write failed for {path.name}: {e}", file=sys.stderr)


def _sync_save(data: dict) -> None:
    """Atomically save a user dict. BLOCKING - always wrap with asyncio.to_thread."""
    user_id = int(data.get("user_id", 0))
    path = _user_path(user_id)
    lock = _get_lock(user_id)
    with lock:
        _atomic_write(path, data)


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def get_user(user_id: int, username: str | None = None) -> dict:
    """Return user data dict (creates file if missing)."""
    return await asyncio.to_thread(_sync_load, int(user_id), username)


async def touch_user(user_id: int, username: str | None = None) -> None:
    """
    Ensure user file exists and refresh last_active + messages_sent counter.
    Call this on every incoming message.
    """
    def _do():
        data = _sync_load(int(user_id), username)
        now = _now()
        data["meta"]["last_active"] = now
        data["meta"]["updated_at"]  = now
        if username:
            data["username"] = username
        stats = data.setdefault("stats", {})
        stats["messages_sent"] = stats.get("messages_sent", 0) + 1
        _sync_save(data)

    await asyncio.to_thread(_do)


async def record_activity(user_id: int, username: str | None,
                          activity_type: str, name: str,
                          extra: dict | None = None) -> None:
    """Record a command / interaction in the user's activity log."""
    def _do():
        data = _sync_load(int(user_id), username)
        activity = data.setdefault("activity", {"counts": {}, "by_name": {}, "recent": []})
        activity["counts"][activity_type] = activity["counts"].get(activity_type, 0) + 1
        activity["by_name"][name]         = activity["by_name"].get(name, 0) + 1
        entry = {"time": _now(), "type": activity_type, "name": name}
        if extra:
            entry["extra"] = extra
        recent = activity.setdefault("recent", [])
        recent.insert(0, entry)
        if len(recent) > 100:
            recent[:] = recent[:100]
        stats = data.setdefault("stats", {})
        stats["commands_used"] = stats.get("commands_used", 0) + 1
        now = _now()
        data["meta"]["last_active"] = now
        data["meta"]["updated_at"]  = now
        if username:
            data["username"] = username
        _sync_save(data)

    await asyncio.to_thread(_do)


async def record_minigame_result(user_id: int, game_name: str, result: str,
                                  coins: int = 0, username: str | None = None) -> None:
    """
    Record a minigame play.
    result: 'win' | 'loss' | 'draw'
    """
    def _do():
        data = _sync_load(int(user_id), username)
        stats = data.setdefault("stats", {})
        stats["minigames_played"] = stats.get("minigames_played", 0) + 1
        if result == "win":
            stats["minigames_won"] = stats.get("minigames_won", 0) + 1

        mg = data.setdefault("minigames", {"by_game": {}, "recent_plays": []})
        by = mg.setdefault("by_game", {})
        g  = by.setdefault(game_name, {"played": 0, "wins": 0, "losses": 0, "draws": 0, "coins": 0})
        g["played"] += 1
        if result == "win":
            g["wins"]   += 1
        elif result == "loss":
            g["losses"] += 1
        else:
            g["draws"]  += 1
        g["coins"] = g.get("coins", 0) + max(0, int(coins))

        recent = mg.setdefault("recent_plays", [])
        recent.insert(0, {
            "time": _now(), "game": game_name,
            "result": result, "coins": coins
        })
        if len(recent) > 100:
            recent[:] = recent[:100]

        now = _now()
        data["meta"]["last_active"] = now
        data["meta"]["updated_at"]  = now
        if username:
            data["username"] = username
        _sync_save(data)

    await asyncio.to_thread(_do)


async def increment_stat(user_id: int, stat_name: str,
                          amount: int = 1, username: str | None = None) -> None:
    """Increment any numeric field under stats.  Safe to call from any cog."""
    def _do():
        data = _sync_load(int(user_id), username)
        stats = data.setdefault("stats", {})
        stats[stat_name] = stats.get(stat_name, 0) + amount
        now = _now()
        data["meta"]["updated_at"]  = now
        data["meta"]["last_active"] = now
        if username:
            data["username"] = username
        _sync_save(data)

    await asyncio.to_thread(_do)


async def set_stat(user_id: int, stat_name: str,
                   value, username: str | None = None) -> None:
    """Set any field under stats to an explicit value."""
    def _do():
        data = _sync_load(int(user_id), username)
        data.setdefault("stats", {})[stat_name] = value
        now = _now()
        data["meta"]["updated_at"]  = now
        data["meta"]["last_active"] = now
        if username:
            data["username"] = username
        _sync_save(data)

    await asyncio.to_thread(_do)


async def record_game_state(user_id: int, username: str | None,
                             game_name: str, state: dict) -> None:
    """Store a game-state snapshot for a user."""
    def _do():
        data = _sync_load(int(user_id), username)
        data.setdefault("games", {})[game_name] = {
            "updated_at": _now(),
            "state": state
        }
        now = _now()
        data["meta"]["updated_at"]  = now
        data["meta"]["last_active"] = now
        if username:
            data["username"] = username
        _sync_save(data)

    await asyncio.to_thread(_do)


# ---------------------------------------------------------------------------
# Backwards-compatibility stubs
# (older cog code calls these - keep them so nothing crashes)
# ---------------------------------------------------------------------------

def init_user_storage_worker(loop=None):
    """No-op: no batch queue needed. Kept for backwards compatibility."""
    print("[USER STORAGE] Ready - direct async/thread writes, no queue.")


async def flush_user_storage_queue():
    """No-op kept for backwards compatibility."""
    pass


async def enqueue_user_storage(func, *args, **kwargs):
    """Legacy stub - runs the function directly in a thread instead of queuing."""
    await asyncio.to_thread(func, *args, **kwargs)


# Synchronous aliases used by some legacy code
load_user        = _sync_load
save_user        = _sync_save
user_file        = _user_path
load_user_simple = _sync_load
save_user_simple = lambda uid, d: (_sync_save({**d, "user_id": uid}))
get_user_file_simple = lambda uid: str(_user_path(int(uid)))
