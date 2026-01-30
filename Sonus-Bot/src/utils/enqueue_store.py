"""Simple shelve-backed persistence for enqueue tasks.

Stores a mapping of guild_id -> enqueue metadata (items list, progress counters).
This is intentionally minimal and used to resume long-running enqueues across restarts.
"""
import os
import shelve
from typing import Optional, Dict, Any

DB_PATH = os.getenv('SONUS_ENQUEUE_DB') or os.path.join(os.getcwd(), 'sonus_enqueue.db')


def _open(write: bool = False):
    # use writeback=False for safety; callers can replace whole entries
    return shelve.open(DB_PATH, writeback=False)


def save_enqueue_state(guild_id: int, data: Dict[str, Any]):
    try:
        with _open(True) as db:
            db[str(guild_id)] = data
    except Exception:
        pass


def load_all_enqueue_states() -> Dict[int, Dict[str, Any]]:
    out = {}
    try:
        with _open(False) as db:
            for k in list(db.keys()):
                try:
                    out[int(k)] = db[k]
                except Exception:
                    continue
    except Exception:
        pass
    return out


def remove_enqueue_state(guild_id: int):
    try:
        with _open(True) as db:
            key = str(guild_id)
            if key in db:
                del db[key]
    except Exception:
        pass
