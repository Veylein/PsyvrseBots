import json
import threading
from pathlib import Path
from shutil import move
import os
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
# Always store user data inside the Ludus folder (local data dir),
# ignoring Render disk mounts to keep this data untouched by Render.
DATA_DIR = ROOT / "data"
TEMPLATE_FILE = DATA_DIR / "user_template.json"
USERS_DIR = DATA_DIR / "users"
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_DIR.mkdir(parents=True, exist_ok=True)

# in-memory locks per user id to avoid interleaved writes in-process
_locks = {}
_locks_lock = threading.Lock()


def _get_lock(user_id: int):
    with _locks_lock:
        if user_id not in _locks:
            _locks[user_id] = threading.Lock()
        return _locks[user_id]


def _load_template():
    if not TEMPLATE_FILE.exists():
        # fallback minimal template
        return {
            "user_id": 0,
            "username": "unknown",
            "minigames": {"total_played": 0, "wins": 0, "losses": 0, "draws": 0, "by_game": {}, "recent_plays": []},
            "games": {},
            "activity": {"counts": {}, "by_name": {}, "recent": []},
            "meta": {"template_version": 1, "updated_at": None, "last_active": None}
        }
    try:
        return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "user_id": 0,
            "username": "unknown",
            "minigames": {"total_played": 0, "wins": 0, "losses": 0, "draws": 0, "by_game": {}, "recent_plays": []},
            "games": {},
            "activity": {"counts": {}, "by_name": {}, "recent": []},
            "meta": {"template_version": 1, "updated_at": None, "last_active": None}
        }


def user_file(user_id: int) -> Path:
    return USERS_DIR / f"{user_id}.json"


def load_user(user_id: int, username: str | None = None) -> dict:
    p = user_file(user_id)
    lock = _get_lock(user_id)
    with lock:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                # if corrupted, recreate from template
                tpl = _load_template()
                tpl["user_id"] = user_id
                if username:
                    tpl["username"] = username
                tpl["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
                save_user(tpl)
                return tpl
        else:
            tpl = _load_template()
            tpl["user_id"] = user_id
            if username:
                tpl["username"] = username
            tpl["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
            save_user(tpl)
            return tpl


def save_user(user_obj: dict):
    user_id = int(user_obj.get("user_id", 0))
    p = user_file(user_id)
    lock = _get_lock(user_id)
    tmp = p.with_suffix('.tmp')
    # ensure users dir exists (defensive)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    with lock:
        try:
            tmp.write_text(json.dumps(user_obj, ensure_ascii=False, indent=2), encoding="utf-8")
            # use atomic replace where available to avoid Windows move issues
            try:
                os.replace(str(tmp), str(p))
            except Exception:
                # fallback to shutil.move for compatibility
                move(str(tmp), str(p))
        except Exception as e:
            # best-effort cleanup of tmp file and emit a short error to stderr
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            try:
                print(f"[user_storage] failed to save user {user_id}: {e}", file=sys.stderr)
            except Exception:
                pass


def record_minigame_result(user_id: int, game_name: str, result: str, coins: int = 0, username: str | None = None):
    """Record a minigame play.

    result: 'win' | 'loss' | 'draw'
    """
    user = load_user(user_id, username)
    mg = user.setdefault("minigames", {})
    mg["total_played"] = mg.get("total_played", 0) + 1
    if result == 'win':
        mg["wins"] = mg.get("wins", 0) + 1
    elif result == 'loss':
        mg["losses"] = mg.get("losses", 0) + 1
    else:
        mg["draws"] = mg.get("draws", 0) + 1

    mg["total_coins_earned"] = mg.get("total_coins_earned", 0) + max(0, int(coins))

    by = mg.setdefault("by_game", {})
    g = by.setdefault(game_name, {"played": 0, "wins": 0, "losses": 0, "draws": 0, "last_played": None, "total_coins": 0, "history": []})
    g["played"] += 1
    if result == 'win':
        g["wins"] += 1
    elif result == 'loss':
        g["losses"] += 1
    else:
        g["draws"] += 1
    g["last_played"] = datetime.utcnow().isoformat() + "Z"
    g["total_coins"] = g.get("total_coins", 0) + max(0, int(coins))
    hist = g.setdefault("history", [])
    hist.append({"time": datetime.utcnow().isoformat() + "Z", "result": result, "coins": coins})

    recent = mg.setdefault("recent_plays", [])
    recent.insert(0, {"time": datetime.utcnow().isoformat() + "Z", "game": game_name, "result": result, "coins": coins})
    # keep recent bounded
    if len(recent) > 200:
        recent = recent[:200]
        mg["recent_plays"] = recent

    user.setdefault("meta", {})["updated_at"] = datetime.utcnow().isoformat() + "Z"
    save_user(user)


def touch_user(user_id: int, username: str | None = None):
    """Ensure user exists and update last_active timestamp."""
    user = load_user(user_id, username)
    user.setdefault("meta", {})["updated_at"] = datetime.utcnow().isoformat() + "Z"
    user["meta"]["last_active"] = datetime.utcnow().isoformat() + "Z"
    if username:
        user["username"] = username
    save_user(user)


def record_activity(user_id: int, username: str | None, activity_type: str, name: str, extra: dict | None = None):
    """Record generic activity (commands, interactions, games)."""
    user = load_user(user_id, username)
    activity = user.setdefault("activity", {})
    counters = activity.setdefault("counts", {})
    counters[activity_type] = counters.get(activity_type, 0) + 1
    by = activity.setdefault("by_name", {})
    by[name] = by.get(name, 0) + 1

    recent = activity.setdefault("recent", [])
    entry = {
        "time": datetime.utcnow().isoformat() + "Z",
        "type": activity_type,
        "name": name,
    }
    if extra:
        entry["extra"] = extra
    recent.insert(0, entry)
    if len(recent) > 200:
        recent[:] = recent[:200]

    user.setdefault("meta", {})["updated_at"] = datetime.utcnow().isoformat() + "Z"
    user["meta"]["last_active"] = datetime.utcnow().isoformat() + "Z"
    if username:
        user["username"] = username
    save_user(user)


def record_game_state(user_id: int, username: str | None, game_name: str, state: dict):
    """Store a snapshot of a game's state for a user."""
    user = load_user(user_id, username)
    games = user.setdefault("games", {})
    games[game_name] = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "state": state
    }
    user.setdefault("meta", {})["updated_at"] = datetime.utcnow().isoformat() + "Z"
    user["meta"]["last_active"] = datetime.utcnow().isoformat() + "Z"
    if username:
        user["username"] = username
    save_user(user)
