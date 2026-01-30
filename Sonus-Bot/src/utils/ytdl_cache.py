import asyncio
import time
from collections import OrderedDict
from typing import Any, Optional

# Local yt-dlp options (kept in-cache to avoid circular imports)
import yt_dlp

YTDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'nocheckcertificate': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'ignoreerrors': True,
}
_YTDL_COOKIEFILE = __import__('os').getenv('YTDL_COOKIEFILE') or __import__('os').getenv('YTDL_COOKIES')
if _YTDL_COOKIEFILE:
    YTDL_OPTS['cookiefile'] = _YTDL_COOKIEFILE

# Simple in-memory TTL LRU cache for yt-dlp extract_info results.
# Not shared across processes; good for single-process bot.

_CACHE = OrderedDict()  # key -> (expires_at, value)
_MAX_ENTRIES = int(__import__("os").getenv('SONUS_YTDL_CACHE_SIZE') or 256)
_TTL = float(__import__("os").getenv('SONUS_YTDL_CACHE_TTL') or 300.0)
_DB_PATH = __import__('os').getenv('SONUS_YTDL_CACHE_DB')
_USE_SHELVE = bool(_DB_PATH)
_SHELVE_DB = None

if _USE_SHELVE:
    try:
        import shelve

        _SHELVE_DB = shelve.open(_DB_PATH, writeback=True)
        # Load persisted entries into memory (respecting TTL)
        now = time.time()
        for k in list(_SHELVE_DB.keys()):
            try:
                expires, data = _SHELVE_DB[k]
                if expires and expires > now:
                    _CACHE[k] = (expires, data)
            except Exception:
                try:
                    del _SHELVE_DB[k]
                except Exception:
                    pass
    except Exception:
        _USE_SHELVE = False


def _cache_get(key: str) -> Optional[Any]:
    now = time.time()
    val = _CACHE.get(key)
    if not val:
        return None
    expires, data = val
    if expires < now:
        try:
            del _CACHE[key]
        except KeyError:
            pass
        return None
    # move to end as recently used
    try:
        _CACHE.move_to_end(key)
    except Exception:
        pass
    return data


def _cache_set(key: str, data: Any) -> None:
    now = time.time()
    expires = now + _TTL
    _CACHE[key] = (expires, data)
    try:
        _CACHE.move_to_end(key)
    except Exception:
        pass
    # trim
    while len(_CACHE) > _MAX_ENTRIES:
        try:
            _CACHE.popitem(last=False)
        except Exception:
            break
    # also persist to shelve if enabled
    if _USE_SHELVE and _SHELVE_DB is not None:
        try:
            _SHELVE_DB[key] = (expires, data)
            _SHELVE_DB.sync()
        except Exception:
            pass


def cache_clear():
    """Clear in-memory and persisted cache."""
    _CACHE.clear()
    if _USE_SHELVE and _SHELVE_DB is not None:
        try:
            _SHELVE_DB.clear()
            _SHELVE_DB.sync()
        except Exception:
            pass


def cache_stats() -> dict:
    """Return simple stats about the cache."""
    now = time.time()
    valid = sum(1 for v in _CACHE.values() if v[0] > now)
    return {'entries': len(_CACHE), 'valid': valid, 'max_entries': _MAX_ENTRIES, 'ttl': _TTL, 'persistent': _USE_SHELVE}


async def extract_info_cached(query: str, attempts: int = 3, backoff: float = 0.5) -> Optional[dict]:
    """Async wrapper that caches yt_dlp.extract_info results.

    Returns the extracted info dict or None on failure.
    """
    key = f"ytdl:{query}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    loop = asyncio.get_running_loop()

    def run(q: str):
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
            try:
                return ytdl.extract_info(q, download=False)
            except Exception:
                return None

    info = None
    for i in range(attempts):
        info = await loop.run_in_executor(None, run, query)
        if info is not None:
            break
        await asyncio.sleep(backoff * (2 ** i))

    if info is not None:
        try:
            _cache_set(key, info)
        except Exception:
            pass
    return info
