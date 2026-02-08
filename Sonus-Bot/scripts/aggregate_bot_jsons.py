#!/usr/bin/env python3
"""Aggregate radios/albums/playlists JSON files from other bot folders into Sonus `data/`.

Dry-run by default; use --apply to copy files. Files are copied into matching
subfolders under Sonus `data/` (radios, albums, playlists). If a destination
filename already exists, the script will skip unless --overwrite is used.

This is conservative: it only copies files located under a top-level
`data/` directory in the source bots or files named like `radios/*.json`,
`albums/*.json`, `playlists/*.json`.
"""
import argparse
import json
import shutil
from pathlib import Path
from typing import List


def find_candidate_files(src: Path) -> List[Path]:
    cand = []
    # Look for top-level data dir
    d = src / "data"
    if d.exists() and d.is_dir():
        for sub in ("radios", "albums", "playlists"):
            p = d / sub
            if p.exists() and p.is_dir():
                for f in p.glob("*.json"):
                    cand.append(f)
    # Also accept direct radios/albums/playlists folders at repo root of the bot
    for sub in ("radios", "albums", "playlists"):
        p = src / sub
        if p.exists() and p.is_dir():
            for f in p.glob("*.json"):
                cand.append(f)
    return cand


def detect_target_subfolder(path: Path) -> str:
    # Determine whether file should go into radios, albums or playlists
    parts = [p.name.lower() for p in path.parts]
    for candidate in ("radios", "albums", "playlists"):
        if candidate in parts:
            return candidate
    # fallback: inspect json contents
    try:
        j = json.loads(path.read_text(encoding='utf8'))
    except Exception:
        return "playlists"
    if isinstance(j, dict):
        if j.get('stations'):
            return 'radios'
        if j.get('tracks') and isinstance(j.get('tracks'), list):
            return 'playlists'
    if isinstance(j, list):
        return 'playlists'
    return 'playlists'


def safe_copy(src: Path, dest_dir: Path, overwrite: bool = False) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists() and not overwrite:
        return False
    shutil.copy2(src, dest)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', nargs='*', default=[], help='Source bot folders to scan (absolute or repo-relative)')
    parser.add_argument('--dest', default=None, help='Destination Sonus data directory (defaults to repo Sonus-Bot/data)')
    parser.add_argument('--apply', action='store_true', help='Copy files; default is dry-run')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files in dest')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    default_dest = repo_root / 'data'
    dest_root = Path(args.dest).resolve() if args.dest else default_dest

    if not args.sources:
        # sensible defaults: look for sibling bot folders in repo root
        defaults = [p for p in repo_root.iterdir() if p.is_dir() and p.name.endswith('-Bot')]
        sources = defaults
    else:
        sources = [Path(s).resolve() for s in args.sources]

    print(f"Destination: {dest_root}")
    total = 0
    copied = 0
    for s in sources:
        if not s.exists():
            print(f"Skipping missing source: {s}")
            continue
        print(f"Scanning: {s}")
        files = find_candidate_files(s)
        for f in files:
            total += 1
            target = detect_target_subfolder(f)
            dest_dir = dest_root / target
            if args.apply:
                ok = safe_copy(f, dest_dir, overwrite=args.overwrite)
                if ok:
                    print(f"Copied: {f} -> {dest_dir / f.name}")
                    copied += 1
                else:
                    print(f"Skipped (exists): {dest_dir / f.name}")
            else:
                print(f"Would copy: {f} -> {dest_dir / f.name}")

    print(f"Found {total} candidate files; {'copied' if args.apply else 'would copy'}: {copied}")


if __name__ == '__main__':
    main()
