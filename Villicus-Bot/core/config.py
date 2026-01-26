"""Minimal `core.config` shim for Villicus.

Provides an async `get_prefix` and a no-op `set_prefix` so the bot can start.
Replace with the project's real config implementation when available.
"""
import asyncio

DEFAULT_PREFIX = 'V!'

async def get_prefix(guild):
    # Placeholder: in real deployment this should read per-guild settings
    await asyncio.sleep(0)  # keep it awaitable
    return DEFAULT_PREFIX

def set_prefix(guild_id, prefix):
    # No-op placeholder: replace with persistence (DB) as needed
    return True
