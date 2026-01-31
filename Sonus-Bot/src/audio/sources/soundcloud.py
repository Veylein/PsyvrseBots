"""SoundCloud source adapter — metadata helper backed by yt-dlp cache.

Provides `metadata()` which mirrors the shape used by the play code.
"""

from typing import Optional, Dict, Any

from src.utils.ytdl_cache import extract_info_cached


def _select_audio_url(info: Optional[Dict[str, Any]]) -> Optional[str]:
    if not info:
        return None
    if info.get('url'):
        return info['url']
    formats = info.get('formats') or []
    audio_only = [
        f for f in formats
        if (not f.get('vcodec') or f.get('vcodec') == 'none') and f.get('acodec') and f.get('acodec') != 'none'
    ]
    if audio_only:
        audio_only.sort(key=lambda f: (f.get('abr') or 0, f.get('tbr') or 0), reverse=True)
        return audio_only[0].get('url')
    for f in formats:
        if f.get('url'):
            return f.get('url')
    return None


class SoundCloudSource:
    def __init__(self, query: str):
        self.query = query

    async def metadata(self) -> Optional[Dict[str, Any]]:
        try:
            info = await extract_info_cached(self.query)
        except Exception:
            info = None

        if not info:
            return None

        # pick first entry if container
        if isinstance(info, dict) and info.get('entries'):
            entries = [e for e in (info.get('entries') or []) if isinstance(e, dict)]
            if entries:
                info = entries[0]

        url = _select_audio_url(info) or info.get('url') or info.get('webpage_url')
        title = info.get('title') or str(self.query)
        duration = info.get('duration')
        thumbnail = info.get('thumbnail')

        return {
            'title': title,
            'url': url,
            'webpage_url': info.get('webpage_url'),
            'duration': duration,
            'thumbnail': thumbnail,
            'raw': info,
        }

    async def stream(self):
        raise NotImplementedError('stream() is not implemented for SoundCloudSource; use metadata() to obtain a playable URL')
