import asyncio
import importlib
from typing import Dict

from src.logger import setup_logger
from src.utils.enqueue_store import load_all_enqueue_states, remove_enqueue_state

logger = setup_logger(__name__)


async def _resume_enqueue_task(bot: 'commands.Bot', guild_id: int, state: Dict):
    # Import play module at runtime to avoid import cycles during module import
    try:
        play = importlib.import_module('src.commands.music.play')
    except Exception:
        logger.exception('Failed to import play module for enqueue resume')
        return

    items = state.get('items') or []
    if not items:
        try:
            remove_enqueue_state(guild_id)
        except Exception:
            pass
        return

    try:
        q = play._ensure_guild_queue(bot, guild_id)
    except Exception:
        q = getattr(bot, 'sonus_queues', {}).get(guild_id)

    for item_query in items:
        try:
            info = await play._yt_search(item_query)
        except Exception:
            info = None
        if not info:
            continue
        e = None
        try:
            if isinstance(info, dict) and info.get('entries'):
                entries = [ent for ent in (info.get('entries') or []) if isinstance(ent, dict)]
                if entries:
                    e = entries[0]
            if e is None:
                e = info
        except Exception:
            e = info
        try:
            url = play._select_audio_url(e) or e.get('url') or e.get('webpage_url')
            title = e.get('title') or (e.get('webpage_url') or str(url))
            track = {'title': title, 'url': url, 'webpage_url': e.get('webpage_url')}
            play._queue_add(q, track, guild_id)
        except Exception:
            pass

    try:
        remove_enqueue_state(guild_id)
    except Exception:
        pass

    # ensure playback is scheduled if guild is available
    try:
        guild = bot.get_guild(guild_id)
        if guild:
            vc = guild.voice_client
            if not vc or not getattr(vc, 'is_connected', lambda: False)():
                try:
                    await play._ensure_vc_connected(bot, guild)
                except Exception:
                    pass
            asyncio.create_task(play._play_next(bot, guild_id))
    except Exception:
        pass


async def resume_persisted_enqueues(bot: 'commands.Bot'):
    """Load persisted enqueue states and schedule resume tasks."""
    states = load_all_enqueue_states()
    if not states:
        return
    try:
        if not hasattr(bot, 'sonus_enqueue_tasks'):
            bot.sonus_enqueue_tasks = {}
    except Exception:
        pass
    for gid, state in states.items():
        try:
            if getattr(bot, 'sonus_enqueue_tasks', {}).get(gid):
                continue
            task = asyncio.create_task(_resume_enqueue_task(bot, gid, state))
            try:
                bot.sonus_enqueue_tasks[gid] = task
            except Exception:
                pass
        except Exception:
            continue
