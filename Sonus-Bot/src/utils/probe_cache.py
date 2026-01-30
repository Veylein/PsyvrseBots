import time
from collections import OrderedDict
from typing import Optional

_CACHE = OrderedDict()  # url -> (expires_at, success: bool)
_MAX = int(__import__('os').getenv('SONUS_PROBE_CACHE_SIZE') or 512)
_TTL = float(__import__('os').getenv('SONUS_PROBE_CACHE_TTL') or 3600.0)


def get(url: str) -> Optional[bool]:
    now = time.time()
    val = _CACHE.get(url)
    if not val:
        return None
    expires, success = val
    if expires < now:
        try:
            del _CACHE[url]
        except Exception:
            pass
        return None
    try:
        _CACHE.move_to_end(url)
    except Exception:
        pass
    return success


def set_success(url: str) -> None:
    _set(url, True)


def set_failure(url: str) -> None:
    _set(url, False)


def _set(url: str, success: bool) -> None:
    expires = time.time() + _TTL
    _CACHE[url] = (expires, success)
    try:
        _CACHE.move_to_end(url)
    except Exception:
        pass
    while len(_CACHE) > _MAX:
        try:
            _CACHE.popitem(last=False)
        except Exception:
            break


def clear() -> None:
    _CACHE.clear()
