"""Persistent `core.config` shim for Villicus.

Stores per-guild settings (prefix and basic options) in a JSON file under
the bot `data/` directory so commands like `V!prefix` can persist changes.
This is intentionally lightweight and can be replaced with a DB-backed
implementation later.
"""
import asyncio
import json
import os
from typing import Optional

DEFAULT_PREFIX = 'V!'

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_SETTINGS_FILE = os.path.join(_DATA_DIR, 'settings.json')


def _ensure_storage():
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
    except Exception:
        pass


def _load_all():
    _ensure_storage()
    try:
        if not os.path.exists(_SETTINGS_FILE):
            return {}
        with open(_SETTINGS_FILE, 'r', encoding='utf8') as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _save_all(data: dict):
    _ensure_storage()
    try:
        with open(_SETTINGS_FILE, 'w', encoding='utf8') as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


async def get_prefix(guild) -> str:
    """Return the configured prefix for `guild` or the default."""
    await asyncio.sleep(0)
    if guild is None:
        return DEFAULT_PREFIX
    data = _load_all()
    g = data.get(str(guild.id), {})
    return g.get('prefix', DEFAULT_PREFIX)


def set_prefix(guild_id: int, prefix: str) -> bool:
    """Persist a prefix for the given guild id."""
    try:
        data = _load_all()
        g = data.get(str(guild_id), {})
        g['prefix'] = prefix
        data[str(guild_id)] = g
        return _save_all(data)
    except Exception:
        return False


def get_guild_settings(guild_id: int) -> dict:
    data = _load_all()
    return data.get(str(guild_id), {})


def save_guild_settings(guild_id: int, settings: dict) -> bool:
    try:
        data = _load_all()
        data[str(guild_id)] = settings
        return _save_all(data)
    except Exception:
        return False
