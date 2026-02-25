"""utils/persist.py
==================
PostgreSQL-backed JSON file persistence for Render deployments.

On every deploy, Render wipes the filesystem. This module solves that by:
  1. restore_all(data_dir)   – called at bot startup, downloads saved files
                               from PostgreSQL → disk (before cogs load)
  2. periodic_sync(data_dir) – asyncio background task, syncs disk → DB every N seconds
  3. sync_now(data_dir)      – force immediate full sync (e.g. on clean shutdown)

PostgreSQL connection uses the DATABASE_URL environment variable.
Add a free Render PostgreSQL database, set DATABASE_URL, and this module
handles the rest — no code changes needed in any cog.

Table schema (auto-created):
    file_store(file_key TEXT PRIMARY KEY, content TEXT, updated_at TIMESTAMPTZ)
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("persist")

# ---------------------------------------------------------------------------
# Files that are already committed to git → skip syncing them
# ---------------------------------------------------------------------------
_STATIC_FILES = {
    "uno_emoji_mapping.json",
    "minesweeper_emoji_mapping.json",
    "user_template.json",
    "profile_template.json",
    "cards_emoji_mapping.json",
    "uno_translations.json",
}

# Large static content datasets → not worth storing in the DB
_CONTENT_FILES = {
    "wyr_questions.json",
    "stories.json",
    "tarot_daily.json",
}

_SKIP_FILES = _STATIC_FILES | _CONTENT_FILES

# Sub-directories inside data/ whose *.json files should be synced
_SYNC_SUBDIRS = ("users", "saves", "tcg")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_db_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")


def _make_conn():
    """Open a new psycopg2 connection.  Raises if DATABASE_URL is not set."""
    import psycopg2
    url = _get_db_url()
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    # Render PostgreSQL URLs start with postgres:// but psycopg2 needs postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return psycopg2.connect(url)


def _ensure_table(conn) -> None:
    """Create the file_store table if it does not exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_store (
                file_key   TEXT PRIMARY KEY,
                content    TEXT        NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()


def _collect_dynamic_files(data_dir: str) -> list:
    """Return list of (relative_key, abs_path) for all dynamic JSON files."""
    base = Path(data_dir)
    result = []

    # Root-level files
    for f in sorted(base.glob("*.json")):
        if f.name not in _SKIP_FILES:
            result.append((f.name, f))

    # Sub-directories
    for sub in _SYNC_SUBDIRS:
        d = base / sub
        if d.exists():
            for f in sorted(d.glob("*.json")):
                result.append((f"{sub}/{f.name}", f))

    return result


# ---------------------------------------------------------------------------
# Blocking implementations (run inside asyncio.to_thread)
# ---------------------------------------------------------------------------

def _restore_all_blocking(data_dir: str) -> int:
    """Download all stored files from PostgreSQL and write to disk."""
    if not _get_db_url():
        logger.info("[persist] DATABASE_URL not set — skipping restore")
        return 0

    try:
        conn = _make_conn()
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT file_key, content FROM file_store")
            rows = cur.fetchall()
        conn.close()

        restored = 0
        for key, content in rows:
            path = Path(data_dir) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                # Validate JSON before writing so corrupted rows don't break cogs
                json.loads(content)
                path.write_text(content, encoding="utf-8")
                restored += 1
            except Exception as e:
                logger.error(f"[persist] restore '{key}' failed: {e}")

        logger.info(f"[persist] Restored {restored}/{len(rows)} files from database")
        return restored

    except Exception as e:
        logger.error(f"[persist] restore_all failed: {e}")
        return 0


def _sync_all_blocking(data_dir: str) -> int:
    """Upload all dynamic JSON files from disk to PostgreSQL."""
    if not _get_db_url():
        return 0

    files = _collect_dynamic_files(data_dir)
    if not files:
        return 0

    try:
        conn = _make_conn()
        _ensure_table(conn)
        synced = 0

        with conn.cursor() as cur:
            for key, path in files:
                if not path.exists():
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                    json.loads(content)  # validate — skip broken files
                    cur.execute(
                        """
                        INSERT INTO file_store (file_key, content, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (file_key) DO UPDATE
                            SET content    = EXCLUDED.content,
                                updated_at = NOW()
                        """,
                        (key, content),
                    )
                    synced += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"[persist] skipping '{key}' — invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"[persist] error syncing '{key}': {e}")

        conn.commit()
        conn.close()
        logger.info(f"[persist] Synced {synced}/{len(files)} files to database")
        return synced

    except Exception as e:
        logger.error(f"[persist] sync_all failed: {e}")
        return 0


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def restore_all(data_dir: str) -> int:
    """
    Download every JSON file stored in PostgreSQL to *data_dir* on disk.
    Call this at bot startup **before** any cog is loaded so the cogs find
    their data files already in place.

    Returns the number of files restored (0 if DATABASE_URL is not set).
    """
    return await asyncio.to_thread(_restore_all_blocking, data_dir)


async def sync_now(data_dir: str) -> int:
    """
    Immediately upload all dynamic JSON files from *data_dir* to PostgreSQL.
    Use this for a clean shutdown or as a manual trigger.

    Returns the number of files synced.
    """
    return await asyncio.to_thread(_sync_all_blocking, data_dir)


async def periodic_sync(data_dir: str, interval: int = 300) -> None:
    """
    Asyncio background task — uploads dynamic JSON files to PostgreSQL every
    *interval* seconds (default 5 minutes).

    Start with:
        bot.loop.create_task(persist.periodic_sync(data_dir))
    """
    logger.info(f"[persist] Periodic sync task started (interval={interval}s)")
    while True:
        await asyncio.sleep(interval)
        try:
            count = await sync_now(data_dir)
            logger.debug(f"[persist] periodic tick: {count} files synced")
        except Exception as e:
            logger.error(f"[persist] periodic sync error: {e}")
