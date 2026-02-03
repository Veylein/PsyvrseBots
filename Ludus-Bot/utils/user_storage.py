import json
import threading
from pathlib import Path
from shutil import move
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TEMPLATE_FILE = DATA_DIR / "user_template.json"
USERS_DIR = DATA_DIR / "users"
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
            "meta": {"template_version": 1}
        }
    try:
        return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "user_id": 0,
            "username": "unknown",
            "minigames": {"total_played": 0, "wins": 0, "losses": 0, "draws": 0, "by_game": {}, "recent_plays": []},
            "meta": {"template_version": 1}
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
    with lock:
        try:
            tmp.write_text(json.dumps(user_obj, ensure_ascii=False, indent=2), encoding="utf-8")
            move(str(tmp), str(p))
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
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
