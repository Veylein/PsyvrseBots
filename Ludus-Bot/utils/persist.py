"""utils/persist.py
==================
PostgreSQL-backed JSON file persistence for Render deployments.

Problem: every Render deploy wipes the filesystem → dynamic JSON files in
data/ are lost.  This module solves that without touching any cog code.

HOW IT WORKS
------------
  startup  → restore_all(data_dir)   reads all rows from the DB and writes
                                      every JSON back to disk BEFORE cogs load.
  runtime  → periodic_sync()         background asyncio task that flushes
                                      disk→DB every N seconds (default 5 min).
  shutdown → sync_now(data_dir)      manual / on-signal full flush.

CONFIGURATION
-------------
Set DATABASE_URL in your environment (or Render service env vars):
    DATABASE_URL=postgresql://user:pass@host:5432/dbname

If DATABASE_URL is not set the module is a no-op — bot works normally with
local files (development mode).

TABLE (auto-created on first run)
----------------------------------
    file_store(file_key TEXT PK, content TEXT, updated_at TIMESTAMPTZ)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("persist")

# ---------------------------------------------------------------------------
# Static / git-tracked files that must NOT be synced to the DB
# ---------------------------------------------------------------------------
_SKIP_NAMES: set[str] = {
    "uno_emoji_mapping.json",
    "minesweeper_emoji_mapping.json",
    "user_template.json",
    "profile_template.json",
    "cards_emoji_mapping.json",
    "uno_translations.json",
    # large rarely-changing content files
    "wyr_questions.json",
    "stories.json",
    "tarot_daily.json",
}

# Sub-directories inside data/ that contain per-user / per-game JSON files
_SYNC_SUBDIRS: tuple[str, ...] = ("users", "saves", "tcg")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return None
    # Render uses "postgres://", psycopg2 needs "postgresql://"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _connect():
    """Return a new psycopg2 connection.  Caller must close it."""
    import psycopg2  # lazy import — not needed locally
    url = _db_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg2.connect(url, connect_timeout=10)


def _ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_store (
                file_key   TEXT PRIMARY KEY,
                content    TEXT        NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()


def _collect_files(data_dir: str) -> list[tuple[str, Path]]:
    """Return [(relative_key, abs_path), …] for all dynamic JSON files."""
    base = Path(data_dir)
    out: list[tuple[str, Path]] = []

    # Root-level files  (data/*.json)
    for f in sorted(base.glob("*.json")):
        if f.name not in _SKIP_NAMES:
            out.append((f.name, f))

    # Sub-directories  (data/users/*.json  etc.)
    for sub in _SYNC_SUBDIRS:
        d = base / sub
        if d.is_dir():
            for f in sorted(d.glob("*.json")):
                out.append((f"{sub}/{f.name}", f))

    return out


# ---------------------------------------------------------------------------
# Blocking implementations  (always called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _restore_blocking(data_dir: str) -> int:
    if not _db_url():
        logger.info("[persist] DATABASE_URL not set — running without DB persistence")
        return 0
    try:
        conn = _connect()
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
                json.loads(content)           # validate before writing
                path.write_text(content, encoding="utf-8")
                restored += 1
            except Exception as exc:
                logger.error("[persist] restore '%s' failed: %s", key, exc)

        logger.info("[persist] Restored %d/%d files from database", restored, len(rows))
        return restored

    except Exception as exc:
        logger.error("[persist] restore_all failed: %s", exc)
        return 0


def _sync_blocking(data_dir: str) -> int:
    if not _db_url():
        return 0
    files = _collect_files(data_dir)
    if not files:
        return 0
    try:
        conn = _connect()
        _ensure_table(conn)
        synced = 0
        with conn.cursor() as cur:
            for key, path in files:
                if not path.exists():
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                    json.loads(content)       # skip broken files
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
                except json.JSONDecodeError as exc:
                    logger.warning("[persist] skip '%s' — invalid JSON: %s", key, exc)
                except Exception as exc:
                    logger.error("[persist] error syncing '%s': %s", key, exc)
        conn.commit()
        conn.close()
        logger.info("[persist] Synced %d/%d files to database", synced, len(files))
        return synced
    except Exception as exc:
        logger.error("[persist] sync_all failed: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------

async def restore_all(data_dir: str) -> int:
    """
    Download every JSON file from PostgreSQL and write it to *data_dir*.
    Call this at bot startup **before** any cog is loaded.
    Returns the number of files written (0 when DATABASE_URL is not set).
    """
    return await asyncio.to_thread(_restore_blocking, data_dir)


async def sync_now(data_dir: str) -> int:
    """
    Immediately upload all dynamic JSON files in *data_dir* to PostgreSQL.
    Returns the number of files written.
    """
    return await asyncio.to_thread(_sync_blocking, data_dir)


async def periodic_sync(data_dir: str, interval: int = 300) -> None:
    """
    Asyncio background task — syncs disk→DB every *interval* seconds (default 5 min).

    Usage in bot.py setup_hook:
        bot.loop.create_task(persist.periodic_sync(DATA_DIR))
    """
    logger.info("[persist] Background sync started (every %ds)", interval)
    while True:
        await asyncio.sleep(interval)
        try:
            count = await sync_now(data_dir)
            logger.debug("[persist] periodic tick: %d files synced", count)
        except Exception as exc:
            logger.error("[persist] periodic sync error: %s", exc)
