"""Lightweight Spotify resolver using Client Credentials flow.

This helper is optional — if `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
are not set, the resolver will return None and the bot will fall back to
yt-dlp extraction/search.
"""
import os
import time
from typing import Optional

import requests
import yt_dlp
import time

# Network retry defaults
_HTTP_ATTEMPTS = int(__import__('os').getenv('SONUS_HTTP_ATTEMPTS') or 3)
_HTTP_BACKOFF = float(__import__('os').getenv('SONUS_HTTP_BACKOFF') or 0.5)
_HTTP_TIMEOUT = float(__import__('os').getenv('SONUS_HTTP_TIMEOUT') or 5.0)


def _requests_post_with_retries(url: str, data=None, auth=None, headers=None, attempts: int = None, backoff: float = None, timeout: float = None):
    attempts = attempts or _HTTP_ATTEMPTS
    backoff = backoff or _HTTP_BACKOFF
    timeout = timeout or _HTTP_TIMEOUT
    last_exc = None
    for i in range(attempts):
        try:
            return requests.post(url, data=data, auth=auth, headers=headers, timeout=timeout)
        except Exception as exc:
            last_exc = exc
            time.sleep(backoff * (2 ** i))
    # final attempt without catching to preserve original behavior
    try:
        return requests.post(url, data=data, auth=auth, headers=headers, timeout=timeout)
    except Exception:
        raise last_exc


def _requests_get_with_retries(url: str, headers=None, attempts: int = None, backoff: float = None, timeout: float = None):
    attempts = attempts or _HTTP_ATTEMPTS
    backoff = backoff or _HTTP_BACKOFF
    timeout = timeout or _HTTP_TIMEOUT
    last_exc = None
    for i in range(attempts):
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except Exception as exc:
            last_exc = exc
            time.sleep(backoff * (2 ** i))
    try:
        return requests.get(url, headers=headers, timeout=timeout)
    except Exception:
        raise last_exc
from typing import List, Dict

YTDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'nocheckcertificate': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'ignoreerrors': True,
}

_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
_TOKEN: Optional[str] = None
_TOKEN_EXPIRES = 0
PREFER_API = os.getenv('SONUS_SPOTIFY_PREFER_API', '1').lower() in ('1', 'true', 'yes')


def _get_token() -> Optional[str]:
    global _TOKEN, _TOKEN_EXPIRES
    if not _CLIENT_ID or not _CLIENT_SECRET:
        return None
    if _TOKEN and _TOKEN_EXPIRES - 30 > time.time():
        return _TOKEN
    try:
        resp = _requests_post_with_retries('https://accounts.spotify.com/api/token', data={'grant_type': 'client_credentials'}, auth=(_CLIENT_ID, _CLIENT_SECRET))
        if resp is None:
            return None
        if resp.status_code == 200:
            j = resp.json()
            _TOKEN = j.get('access_token')
            _TOKEN_EXPIRES = time.time() + int(j.get('expires_in', 3600))
            return _TOKEN
    except Exception:
        return None
    return None


def resolve_spotify(url: str) -> Optional[dict]:
    """Resolve a Spotify URL to a friendly representation.

    Returns a dict with keys:
      - type: 'track'|'album'|'playlist'
      - query: for single track, a search string
      - items: for album/playlist, a list of search strings (track - artist)

    Returns None if resolution is not possible or creds are not configured.
    """
    # Respect env toggle: allow preferring yt-dlp fallback even when API creds exist
    prefer_api = PREFER_API
    if not prefer_api:
        # try yt-dlp fallback first
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
                try:
                    info = ytdl.extract_info(url, download=False)
                except Exception:
                    info = None
        except Exception:
            info = None

        if info:
            # process extracted info similarly to below fallback
            if isinstance(info, dict) and info.get('entries'):
                items: List[str] = []
                for e in (info.get('entries') or []):
                    if not e or not isinstance(e, dict):
                        continue
                    name = e.get('title') or e.get('name') or e.get('track') or None
                    artists = None
                    a = e.get('artists') or e.get('artist') or e.get('uploader')
                    if isinstance(a, list):
                        try:
                            artists = ', '.join(x.get('name') for x in a if x and x.get('name'))
                        except Exception:
                            artists = None
                    elif isinstance(a, str):
                        artists = a
                    if name and artists:
                        items.append(f"{name} - {artists}")
                    elif name:
                        items.append(name)
                if items:
                    return {'type': 'playlist', 'items': items}
            if isinstance(info, dict):
                name = info.get('title') or info.get('name')
                a = info.get('artists') or info.get('artist') or info.get('uploader')
                artists = None
                if isinstance(a, list):
                    try:
                        artists = ', '.join(x.get('name') for x in a if x and x.get('name'))
                    except Exception:
                        artists = None
                elif isinstance(a, str):
                    artists = a
                if name and artists:
                    return {'type': 'track', 'query': f"{name} - {artists}"}
                if name:
                    return {'type': 'track', 'query': name}

    token = _get_token()
    # If we don't have client credentials, try a yt-dlp extraction fallback
    if not token:
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
                try:
                    info = ytdl.extract_info(url, download=False)
                except Exception:
                    return None
        except Exception:
            return None

        # If yt-dlp returned entries (playlist), collect items
        if isinstance(info, dict) and info.get('entries'):
            items: List[str] = []
            for e in (info.get('entries') or []):
                if not e or not isinstance(e, dict):
                    continue
                name = e.get('title') or e.get('name') or e.get('track') or None
                # artists may be a list of dicts or a single string
                artists = None
                a = e.get('artists') or e.get('artist') or e.get('uploader')
                if isinstance(a, list):
                    try:
                        artists = ', '.join(x.get('name') for x in a if x and x.get('name'))
                    except Exception:
                        artists = None
                elif isinstance(a, str):
                    artists = a
                if name and artists:
                    items.append(f"{name} - {artists}")
                elif name:
                    items.append(name)
            if items:
                # best-effort: classify as playlist/album
                return {'type': 'playlist', 'items': items}

        # single-track fallback
        if isinstance(info, dict):
            name = info.get('title') or info.get('name')
            a = info.get('artists') or info.get('artist') or info.get('uploader')
            artists = None
            if isinstance(a, list):
                try:
                    artists = ', '.join(x.get('name') for x in a if x and x.get('name'))
                except Exception:
                    artists = None
            elif isinstance(a, str):
                artists = a
            if name and artists:
                return {'type': 'track', 'query': f"{name} - {artists}"}
            if name:
                return {'type': 'track', 'query': name}
        return None
    headers = {'Authorization': f'Bearer {token}'}
    try:
        if url.startswith('spotify:'):
            parts = url.split(':')
            if len(parts) >= 3:
                typ = parts[1]
                id_ = parts[2]
            else:
                return None
        else:
            parts = url.split('/')
            if len(parts) < 2:
                return None
            typ = parts[-2].split('?')[0]
            id_ = parts[-1].split('?')[0]

        if typ == 'track':
            r = _requests_get_with_retries(f'https://api.spotify.com/v1/tracks/{id_}', headers=headers)
            if r is None:
                return None
            if r.status_code == 200:
                j = r.json()
                artists = ', '.join(a.get('name') for a in j.get('artists', []) if a.get('name'))
                name = j.get('name')
                if name and artists:
                    return {'type': 'track', 'query': f"{name} - {artists}"}
        elif typ == 'album':
            # fetch album tracks (may be paginated)
            items = []
            offset = 0
            limit = 50
            while True:
                r = _requests_get_with_retries(f'https://api.spotify.com/v1/albums/{id_}/tracks?offset={offset}&limit={limit}', headers=headers)
                if r is None or r.status_code != 200:
                    break
                j = r.json()
                for t in j.get('items', []) or []:
                    name = t.get('name')
                    artists = ', '.join(a.get('name') for a in t.get('artists', []) if a.get('name'))
                    if name and artists:
                        items.append(f"{name} - {artists}")
                if not j.get('next'):
                    break
                offset += limit
            if items:
                return {'type': 'album', 'items': items}
        elif typ == 'playlist':
            items = []
            offset = 0
            limit = 100
            while True:
                r = _requests_get_with_retries(f'https://api.spotify.com/v1/playlists/{id_}/tracks?offset={offset}&limit={limit}', headers=headers)
                if r is None or r.status_code != 200:
                    break
                j = r.json()
                for entry in j.get('items', []) or []:
                    t = entry.get('track') or {}
                    name = t.get('name')
                    artists = ', '.join(a.get('name') for a in t.get('artists', []) if a.get('name'))
                    if name and artists:
                        items.append(f"{name} - {artists}")
                if not j.get('next'):
                    break
                offset += limit
            if items:
                return {'type': 'playlist', 'items': items}
    except Exception:
        return None
    return None
