"""Persistent per-guild queue storage using shelve.

Provides simple load/save helpers. Persistence is optional and enabled by
setting the `SONUS_QUEUE_DB` environment variable to a writable path.
"""
import os
import shelve
import time
from typing import Dict, Any, Optional

_DB_PATH = os.getenv('SONUS_QUEUE_DB')
_DB = None

if _DB_PATH:
    try:
        _DB = shelve.open(_DB_PATH, writeback=True)
    except Exception:
        _DB = None


def load_queues() -> Dict[int, Any]:
    """Return a mapping of guild_id -> queue contents (lists)."""
    out: Dict[int, Any] = {}
    if not _DB:
        return out
    try:
        for k in list(_DB.keys()):
            try:
                out[int(k)] = _DB[k]
            except Exception:
                continue
    except Exception:
        pass
    return out


def save_queue(guild_id: int, queue_contents) -> None:
    """Save a single guild queue. `queue_contents` should be serializable.

    If persistence isn't enabled this is a no-op.
    """
    if not _DB:
        return
    try:
        _DB[str(guild_id)] = queue_contents
        _DB.sync()
    except Exception:
        pass


def save_all(queues: Dict[int, Any]) -> None:
    if not _DB:
        return
    try:
        for gid, q in queues.items():
            try:
                _DB[str(gid)] = q
            except Exception:
                pass
        _DB.sync()
    except Exception:
        pass


def clear():
    if not _DB:
        return
    try:
        _DB.clear()
        _DB.sync()
    except Exception:
        pass
