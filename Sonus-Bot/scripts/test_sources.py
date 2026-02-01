import sys
import asyncio
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audio.sources.youtube import YouTubeSource
from src.audio.sources.soundcloud import SoundCloudSource

async def main():
    queries = [
        ('YouTube search', 'never gonna give you up', YouTubeSource),
        ('YouTube URL', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', YouTubeSource),
        ('SoundCloud URL', 'https://soundcloud.com/forss/flickermood', SoundCloudSource),
    ]

    for label, q, cls in queries:
        try:
            src = cls(q)
            print(f'--- Testing {label}: {q}')
            m = await asyncio.wait_for(src.metadata(), timeout=30)
            if not m:
                print('Result: None')
            else:
                print('Title:', m.get('title'))
                print('Playable URL:', (m.get('url') or m.get('webpage_url')))
                print('Duration:', m.get('duration'))
        except asyncio.TimeoutError:
            print('Timed out')
        except Exception as exc:
            print('Error:', type(exc).__name__, exc)

if __name__ == '__main__':
    asyncio.run(main())
