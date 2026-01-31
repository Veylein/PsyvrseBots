#!/usr/bin/env python3
"""Convert YouTube links in local playlists/albums/radios to SoundCloud matches.

Dry-run by default; use --apply to overwrite files (creates .bak backups).

The script uses the project's `src.utils.ytdl_cache.extract_info_cached` to
query yt-dlp for SoundCloud search results (scsearch). This avoids adding new
dependencies and reuses existing caching.
"""
import argparse
import json
import os
from pathlib import Path
from typing import Optional

# make src package importable
import sys
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from src.utils.ytdl_cache import extract_info_cached

YT_DOMAINS = ("youtube.com", "youtu.be", "music.youtube.com")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

YTDL_SEARCH_PREFIX = "scsearch5:"  # ask yt-dlp to search SoundCloud and return top 5


def is_youtube_url(u: Optional[str]) -> bool:
    if not u:
        return False
    lu = u.lower()
    return any(d in lu for d in YT_DOMAINS)


async def find_soundcloud_for(query: str):
    """Return the best SoundCloud entry info dict or None."""
    try:
        info = await extract_info_cached(f"{YTDL_SEARCH_PREFIX}{query}")
    except Exception:
        info = None
    if not info:
        return None
    # same pattern: prefer first entry
    if isinstance(info, dict) and info.get('entries'):
        entries = [e for e in (info.get('entries') or []) if isinstance(e, dict)]
        if entries:
            return entries[0]
    # if single dict
    if isinstance(info, dict):
        return info
    return None


def iter_data_files(folders):
    for folder in folders:
        p = DATA_DIR / folder
        if not p.exists() or not p.is_dir():
            continue
        for f in p.glob("*.json"):
            yield f


async def process_file(path: Path, apply: bool = False, limit: Optional[int] = None):
    changed = False
    with path.open('r', encoding='utf8') as fh:
        try:
            data = json.load(fh)
        except Exception:
            print(f"Skipping (invalid json): {path}")
            return False

    # data can be list of tracks or dict depending on schema; normalize to list
    if isinstance(data, dict) and data.get('tracks') and isinstance(data['tracks'], list):
        container = data
        tracks = data['tracks']
    elif isinstance(data, list):
        container = None
        tracks = data
    elif isinstance(data, dict) and data.get('stations') and isinstance(data['stations'], list):
        container = data
        tracks = data['stations']
    else:
        # unknown format; try to find common list fields
        tracks = None
        for k, v in list(data.items()):
            if isinstance(v, list) and v and isinstance(v[0], dict) and any('url' in v[0] for _ in []):
                tracks = v
                container = data
                break
        if tracks is None:
            print(f"Unknown file format, skipping: {path}")
            return False

    total = len(tracks)
    updates = 0
    checked = 0
    for idx, t in enumerate(tracks):
        if limit and checked >= limit:
            break
        url = t.get('url') if isinstance(t, dict) else None
        if not url or not is_youtube_url(url):
            continue
        checked += 1
        title = t.get('title') or t.get('name') or ''
        query = title or url
        sc = await find_soundcloud_for(query)
        if not sc:
            print(f"No SoundCloud match for {query} in {path.name}")
            continue
        sc_url = sc.get('webpage_url') or sc.get('url')
        if not sc_url:
            continue
        # update
        print(f"Replace in {path.name}: {url} -> {sc_url}")
        t['url'] = sc_url
        t['source_replaced'] = 'youtube->soundcloud'
        t['original_url'] = url
        updates += 1
        changed = True

    if changed and apply:
        # backup
        bak = path.with_suffix(path.suffix + '.bak')
        try:
            if not bak.exists():
                path.replace(bak)
                # write new file to original path
                with path.open('w', encoding='utf8') as fh:
                    json.dump(container if container is not None else tracks, fh, indent=2, ensure_ascii=False)
                print(f"Wrote updated file and created backup: {bak}")
            else:
                # fallback: write to temp then replace
                with path.open('w', encoding='utf8') as fh:
                    json.dump(container if container is not None else tracks, fh, indent=2, ensure_ascii=False)
                print(f"Wrote updated file (backup already existed): {path}")
        except Exception as exc:
            print(f"Failed to write updates for {path}: {exc}")
            return False
    elif changed:
        print(f"(dry-run) Would update {path}: {updates} replacements")
    else:
        print(f"No replacements in {path}")

    return changed


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply changes (writes files). Default: dry-run')
    parser.add_argument('--folders', nargs='*', default=['playlists', 'albums', 'radios'], help='Which data subfolders to process')
    parser.add_argument('--limit', type=int, default=0, help='Max replacements per file (0 = unlimited)')
    args = parser.parse_args()

    files = list(iter_data_files(args.folders))
    if not files:
        print('No data files found to process.')
        return

    any_changed = False
    for f in files:
        changed = await process_file(f, apply=args.apply, limit=(args.limit or None))
        any_changed = any_changed or changed

    if any_changed:
        print('Processing complete: some files would be/ were changed.')
    else:
        print('Processing complete: no changes found.')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
