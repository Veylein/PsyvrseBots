"""YouTube source adapter — metadata helper backed by yt-dlp cache.

This project uses yt-dlp via `src.utils.ytdl_cache.extract_info_cached`.
The adapter provides `metadata()` to return a track-like dict compatible
with the rest of the Sonus code (title, url, webpage_url, duration, thumbnail).
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


class YouTubeSource:
    def __init__(self, query: str):
        """`query` may be a search term, video id or URL — passed to yt-dlp."""
        self.query = query

    async def metadata(self) -> Optional[Dict[str, Any]]:
        """Return a metadata dict similar to what the play command expects.

        Keys: `title`, `url` (direct audio URL when available), `webpage_url`,
        `duration` (seconds, if available), `thumbnail`, and `raw` (full info).
        Returns None on failure.
        """
        try:
            # if the query looks like a plain search term (not a URL), use yt-dlp's ytsearch1: to find best match
            q = str(self.query)
            is_url = q.startswith('http') or q.startswith('<') and q.endswith('>')
            if not is_url:
                q = f"ytsearch1:{q}"
            info = await extract_info_cached(q)
        except Exception:
            info = None

        if not info:
            return None

        # If yt-dlp returned a container (playlist/search), pick the first usable entry
        if isinstance(info, dict) and info.get('entries'):
            entries = [e for e in (info.get('entries') or []) if isinstance(e, dict)]
            if entries:
                info = entries[0]

        url = _select_audio_url(info) or info.get('url') or info.get('webpage_url')
        title = info.get('title') or str(self.query)
        duration = info.get('duration')
        thumbnail = info.get('thumbnail') or info.get('thumbnails') and (info.get('thumbnails')[-1].get('url') if isinstance(info.get('thumbnails'), list) and info.get('thumbnails') else None)

        return {
            'title': title,
            'url': url,
            'webpage_url': info.get('webpage_url'),
            'duration': duration,
            'thumbnail': thumbnail,
            'raw': info,
        }

    async def stream(self):
        """Not implemented: Sonus currently streams via discord.FFmpegOpusAudio and
        uses direct URLs produced by yt-dlp. If you need a raw PCM iterator,
        implement this method to spawn ffmpeg and yield bytes.
        """
        raise NotImplementedError('stream() is not implemented for YouTubeSource; use metadata() to obtain a playable URL')
