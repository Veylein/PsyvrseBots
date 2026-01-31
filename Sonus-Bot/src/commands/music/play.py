import asyncio
import time
from typing import Optional, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands
import os
from pathlib import Path
import yt_dlp

from src.logger import setup_logger
from src.utils.audit import log_action
from src.utils.ytdl_cache import extract_info_cached
from src.utils.probe_cache import get as probe_get, set_success as probe_set_success, set_failure as probe_set_failure
from src.utils.spotify import resolve_spotify

logger = setup_logger(__name__)


_YTDL_COOKIEFILE = None

_env_cookie = os.getenv('YTDL_COOKIEFILE') or os.getenv('YTDL_COOKIES')
if _env_cookie and os.path.exists(_env_cookie):
    _YTDL_COOKIEFILE = _env_cookie
else:
    _secret_path = '/etc/secrets/cookies.txt'
    if os.path.exists(_secret_path):
        _YTDL_COOKIEFILE = _secret_path

YTDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'nocheckcertificate': True,
    'no_warnings': True,
    # prefer IPv4 (helps on some hosts/networks) and keep going on minor errors
    'source_address': '0.0.0.0',
    'ignoreerrors': True,
}
if _YTDL_COOKIEFILE:
    YTDL_OPTS['cookiefile'] = _YTDL_COOKIEFILE


def _select_audio_url(info: Dict[str, Any]) -> Optional[str]:
    if not info:
        return None
    if info.get('url'):
        return info['url']
    formats: List[Dict[str, Any]] = info.get('formats') or []
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


async def _yt_search(query: str, attempts: int = 3, backoff: float = 0.5) -> Optional[dict]:
    """Extract media info using a cached yt-dlp wrapper. Falls back to fresh extraction on failures.

    Returns either a dict or None.
    """
    try:
        info = await extract_info_cached(query, attempts=attempts, backoff=backoff)
    except Exception:
        logger.exception('Cached yt-dlp extract failed for query/url: %s', query)
        info = None

    # If cached extraction failed or returned a container, still try a direct fresh extraction
    if not info:
        loop = asyncio.get_running_loop()

        def run(q: str):
            with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
                try:
                    return ytdl.extract_info(q, download=False)
                except Exception:
                    logger.exception('yt-dlp extract failed for query/url: %s', q)
                    return None

        for i in range(attempts):
            info = await loop.run_in_executor(None, run, query)
            if not info:
                await asyncio.sleep(backoff * (2 ** i))
                continue
            break

    if not info:
        return None

    # yt-dlp may return a container with `entries` (playlist/search results).
    # Prefer the first valid entry that contains stream info.
    if isinstance(info, dict) and info.get('entries'):
        entries = info.get('entries') or []
        # entries can be a generator or list-like
        for e in entries:
            if not e:
                continue
            # some entries are urls/ids while others are full dicts
            if isinstance(e, dict) and (e.get('url') or e.get('formats') or e.get('webpage_url') or e.get('title')):
                return e
        # if no usable entry found, fall back to the parent info
    return info


def _ensure_guild_queue(bot: commands.Bot, guild_id: int):
    q = getattr(bot, 'sonus_queues', None)
    if q is None:
        bot.sonus_queues = {}
        q = bot.sonus_queues
    if guild_id not in q:
        # try to create a TrackQueue instance for the guild if available
        try:
            from src.audio.queue import TrackQueue

            q[guild_id] = TrackQueue()
        except Exception:
            q[guild_id] = []
    return q[guild_id]


from src.utils.queue_store import save_queue
from src.utils.enqueue_store import save_enqueue_state, remove_enqueue_state, load_all_enqueue_states


def _queue_add(q, item: Any, guild_id: Optional[int] = None):
    try:
        if hasattr(q, 'enqueue'):
            q.enqueue(item)
            # persist when possible
            try:
                if guild_id:
                    save_queue(guild_id, q.all() if hasattr(q, 'all') else list(q))
            except Exception:
                pass
            return
        if hasattr(q, 'append'):
            q.append(item)
            try:
                if guild_id:
                    save_queue(guild_id, q.all() if hasattr(q, 'all') else list(q))
            except Exception:
                pass
            return
        # fallback
        q.enqueue(item)
    except Exception:
        try:
            q.append(item)
            try:
                if guild_id:
                    save_queue(guild_id, q.all() if hasattr(q, 'all') else list(q))
            except Exception:
                pass
        except Exception:
            raise


def _queue_pop(q, guild_id: Optional[int] = None):
    try:
        if hasattr(q, 'dequeue'):
            item = q.dequeue()
            try:
                if guild_id:
                    save_queue(guild_id, q.all() if hasattr(q, 'all') else list(q))
            except Exception:
                pass
            return item
        if hasattr(q, 'pop'):
            # assume list-like pop(0)
            try:
                item = q.pop(0)
            except TypeError:
                item = q.pop()
            try:
                if guild_id:
                    save_queue(guild_id, q.all() if hasattr(q, 'all') else list(q))
            except Exception:
                pass
            return item
        return None
    except Exception:
        return None


async def _create_player_with_probe(url: str, ffmpeg_options: Dict[str, str], timeout: float = 12.0):
    loop = asyncio.get_running_loop()

    def do_probe(u: str):
        return discord.FFmpegOpusAudio.from_probe(u, **ffmpeg_options)

    def do_plain(u: str):
        return discord.FFmpegOpusAudio(u, **ffmpeg_options)
    # If we have a cached probe success for this URL, try a single quick probe
    cached = None
    try:
        cached = probe_get(url)
    except Exception:
        cached = None
    if cached is True:
        try:
            player = await asyncio.wait_for(loop.run_in_executor(None, do_probe, url), timeout=min(6.0, timeout))
            # mark success in cache and return
            try:
                probe_set_success(url)
            except Exception:
                pass
            return player
        except Exception:
            # cached result seemed stale; fall through to normal probing
            try:
                probe_set_failure(url)
            except Exception:
                pass

    # try probe first with escalating timeouts and small backoffs, then fallback to plain construction.
    last_exc = None
    timeouts = [timeout, timeout * 2]
    for attempt, t in enumerate(timeouts, start=1):
        try:
            player = await asyncio.wait_for(loop.run_in_executor(None, do_probe, url), timeout=t)
            logger.debug('Probe succeeded on attempt %d for %s (timeout=%s)', attempt, url, t)
            try:
                probe_set_success(url)
            except Exception:
                pass
            return player
        except Exception as exc:
            last_exc = exc
            logger.debug('Probe attempt %d failed for %s: %s', attempt, url, exc)
            # small backoff between attempts
            await asyncio.sleep(0.5 * attempt)

    # as a last resort, try constructing without probing (may succeed for some streams)
    try:
        player = await asyncio.wait_for(loop.run_in_executor(None, do_plain, url), timeout=max(8.0, timeout))
        logger.debug('Plain FFmpeg construction succeeded for %s', url)
        return player
    except Exception as exc2:
        logger.exception('Plain FFmpeg construction failed for %s: %s', url, exc2)
        # raise the most relevant exception for upstream handling
        try:
            probe_set_failure(url)
        except Exception:
            pass
        raise last_exc or exc2


async def _ensure_vc_connected(bot: commands.Bot, guild: discord.Guild, preferred_channel_id: Optional[int] = None, attempts: int = 3):
    """Ensure the bot has an active VoiceClient in `guild`.

    If `preferred_channel_id` is provided, try connecting to that channel first.
    Returns the `VoiceClient` instance or `None` if unable to connect.
    """
    if guild is None:
        return None

    # quick check for existing client
    vc = guild.voice_client
    if vc and getattr(vc, 'is_connected', lambda: False)():
        return vc

    # try preferred channel first
    channels_to_try = []
    if preferred_channel_id:
        try:
            c = guild.get_channel(preferred_channel_id)
            if isinstance(c, discord.VoiceChannel):
                channels_to_try.append(c)
        except Exception:
            pass

    # fallback: pick a voice channel with members or the first voice channel the bot can join
    try:
        for c in guild.voice_channels:
            # prefer channels with non-bot members
            if any(not m.bot for m in c.members):
                channels_to_try.append(c)
        if not channels_to_try:
            channels_to_try.extend(guild.voice_channels)
    except Exception:
        logger.exception('Could not enumerate voice channels for guild %s', getattr(guild, 'id', 'unknown'))

    last_exc = None
    for ch in channels_to_try:
        for attempt in range(attempts):
            try:
                vc = await ch.connect(reconnect=True)
                return vc
            except Exception as exc:
                last_exc = exc
                logger.debug('Attempt %d to connect to %s failed: %s', attempt + 1, getattr(ch, 'id', None), exc)
                await asyncio.sleep(0.5 * (attempt + 1))

    logger.error('Failed to establish voice connection in guild %s: %s', getattr(guild, 'id', None), last_exc)
    return None


def register(bot: commands.Bot):
    @bot.command(name='play')
    async def _play(ctx: commands.Context, *, query: str):
        """Prefix: S!play <query|url> — enqueue or play immediately."""
        guild = ctx.guild
        if guild is None:
            await ctx.send('Playback is only available in a guild.')
            return

        # If the query looks like a plain search (not a URL), offer interactive
        # selection from top search results to improve reliability and UX.
        info = None
        is_plain_search = not (query.startswith('http') or query.startswith('<') and query.endswith('>'))
        if is_plain_search:
            # perform a yt-dlp search for top entries
            try:
                loop = asyncio.get_running_loop()

                def run_search(q: str):
                    with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
                        try:
                            return ytdl.extract_info(f"ytsearch20:{q}", download=False)
                        except Exception:
                            return None

                search_info = await loop.run_in_executor(None, run_search, query)
                entries = []
                if isinstance(search_info, dict) and search_info.get('entries'):
                    entries = [e for e in (search_info.get('entries') or []) if isinstance(e, dict)][:20]

                # If multiple entries found, present a paginated selection UI
                if entries:
                    PAGE_SIZE = 5

                    class SearchPaginator(discord.ui.View):
                        def __init__(self, entries: List[dict], page_size: int = PAGE_SIZE, timeout: int = 30):
                            super().__init__(timeout=timeout)
                            self.entries = entries
                            self.page_size = page_size
                            self.page = 0
                            self.value = None
                            self.message = None
                            self._build()

                        def _build(self):
                            # clear existing children
                            try:
                                self.clear_items()
                            except Exception:
                                pass
                            start = self.page * self.page_size
                            end = start + self.page_size
                            page_entries = self.entries[start:end]
                            for i, e in enumerate(page_entries, start=1):
                                title = (e.get('title') or 'Untitled')[:80]
                                btn = discord.ui.Button(label=f"{i}. {title}", style=discord.ButtonStyle.primary)
                                async def _select(button: discord.ui.Button, interaction: discord.Interaction, idx=(start + i - 1)):
                                    await interaction.response.defer(ephemeral=True)
                                    try:
                                        self.value = self.entries[idx]
                                    except Exception:
                                        self.value = None
                                    # disable buttons
                                    try:
                                        for child in list(self.children):
                                            child.disabled = True
                                    except Exception:
                                        pass
                                    try:
                                        if self.message:
                                            await self.message.edit(view=self)
                                    except Exception:
                                        pass
                                btn.callback = _select
                                self.add_item(btn)

                            # navigation buttons
                            prev_disabled = self.page == 0
                            next_disabled = (end >= len(self.entries))
                            prev_btn = discord.ui.Button(label='◀ Prev', style=discord.ButtonStyle.secondary)
                            next_btn = discord.ui.Button(label='Next ▶', style=discord.ButtonStyle.secondary)

                            async def _prev(button: discord.ui.Button, interaction: discord.Interaction):
                                await interaction.response.defer(ephemeral=True)
                                if self.page > 0:
                                    self.page -= 1
                                    self._build()
                                    try:
                                        if self.message:
                                            await self.message.edit(content=f'Select a result to play (page {self.page+1}/{(len(self.entries)-1)//self.page_size+1}):', view=self)
                                    except Exception:
                                        pass

                            async def _next(button: discord.ui.Button, interaction: discord.Interaction):
                                await interaction.response.defer(ephemeral=True)
                                if (self.page + 1) * self.page_size < len(self.entries):
                                    self.page += 1
                                    self._build()
                                    try:
                                        if self.message:
                                            await self.message.edit(content=f'Select a result to play (page {self.page+1}/{(len(self.entries)-1)//self.page_size+1}):', view=self)
                                    except Exception:
                                        pass

                            prev_btn.callback = _prev
                            next_btn.callback = _next
                            prev_btn.disabled = prev_disabled
                            next_btn.disabled = next_disabled
                            self.add_item(prev_btn)
                            self.add_item(next_btn)

                        async def on_timeout(self):
                            try:
                                for child in list(self.children):
                                    child.disabled = True
                                if self.message:
                                    await self.message.edit(view=self)
                            except Exception:
                                pass

                    view = SearchPaginator(entries)
                    try:
                        msg = await ctx.send(f'Select a result to play (page 1/{(len(entries)-1)//PAGE_SIZE+1}):', view=view)
                        view.message = msg
                        await view.wait()
                        chosen = getattr(view, 'value', None)
                        if chosen:
                            info = chosen
                        else:
                            info = await _yt_search(query)
                    except Exception:
                        info = await _yt_search(query)
                else:
                    info = await _yt_search(query)
            except Exception:
                info = await _yt_search(query)
        else:
            # handle spotify urls by resolving to search string(s) if possible
            spotify_res = None
            if 'spotify' in (query or '').lower():
                try:
                    spotify_res = resolve_spotify(query)
                except Exception:
                    spotify_res = None

            if spotify_res:
                # single track -> treat as a normal query
                if spotify_res.get('type') == 'track' and spotify_res.get('query'):
                    info = await _yt_search(spotify_res['query'])
                # playlists/albums -> enqueue each resolved track
                elif spotify_res.get('type') in ('album', 'playlist') and spotify_res.get('items'):
                    items = spotify_res['items']
                    limit = int(os.getenv('SONUS_PLAYLIST_LIMIT') or 100)
                    to_enqueue = items[:limit]
                    added = 0
                    q = _ensure_guild_queue(bot, guild.id)
                    CHUNK = int(os.getenv('SONUS_ENQUEUE_CHUNK') or 25)
                    total = len(to_enqueue)
                    try:
                        # create a cancelable view so the requester can abort a large enqueue
                        class _CancelEnqueueView(discord.ui.View):
                            def __init__(self, bot: commands.Bot, guild_id: int):
                                super().__init__(timeout=None)
                                self._bot = bot
                                self._guild_id = guild_id

                                btn = discord.ui.Button(label='Cancel Enqueue', style=discord.ButtonStyle.danger)

                                async def _cancel(interaction: discord.Interaction):
                                    await interaction.response.defer(ephemeral=True)
                                    tasks = getattr(self._bot, 'sonus_enqueue_tasks', {})
                                    t = tasks.get(self._guild_id)
                                    if t and not t.done():
                                        t.cancel()
                                        await interaction.followup.send('Enqueue cancelled.', ephemeral=True)
                                    else:
                                        await interaction.followup.send('No active enqueue to cancel.', ephemeral=True)

                                btn.callback = _cancel
                                self.add_item(btn)

                        view = _CancelEnqueueView(bot, guild.id)
                        progress_msg = await ctx.send(f'Enqueuing 0/{total} tracks from Spotify {spotify_res.get("type")}...', view=view)
                    except Exception:
                        progress_msg = None

                    async def _enqueue_worker(items, q, ctx, progress_msg, guild_id):
                        added_local = 0
                        total_local = len(items)
                        # persist initial state so we can resume after restarts
                        try:
                            save_enqueue_state(guild_id, {'items': items, 'added': 0, 'total': total_local, 'requester_id': getattr(ctx.author, 'id', None)})
                        except Exception:
                            pass
                        try:
                            for idx, item_query in enumerate(items, start=1):
                                try:
                                    e_info = await _yt_search(item_query)
                                except asyncio.CancelledError:
                                    raise
                                except Exception:
                                    e_info = None

                                if not e_info:
                                    if progress_msg and (idx % CHUNK == 0 or idx == total_local):
                                        try:
                                            await progress_msg.edit(content=f'Enqueued {added_local}/{total_local} tracks from Spotify {spotify_res.get("type")} (in progress)...')
                                        except Exception:
                                            pass
                                    continue

                                e = None
                                try:
                                    if isinstance(e_info, dict) and e_info.get('entries'):
                                        entries = [ent for ent in (e_info.get('entries') or []) if isinstance(ent, dict)]
                                        if entries:
                                            e = entries[0]
                                    if e is None:
                                        e = e_info
                                except Exception:
                                    e = e_info

                                try:
                                    url = _select_audio_url(e) or e.get('url') or e.get('webpage_url')
                                    title = e.get('title') or (e.get('webpage_url') or str(url))
                                    track = {'title': title, 'url': url, 'webpage_url': e.get('webpage_url')}
                                    try:
                                        if ctx.author:
                                            track['requested_by'] = getattr(ctx.author, 'display_name', None) or getattr(ctx.author, 'name', None) or str(ctx.author)
                                            track['requester_id'] = getattr(ctx.author, 'id', None)
                                            if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                                                track['requester_channel_id'] = ctx.author.voice.channel.id
                                    except Exception:
                                        pass
                                    _queue_add(q, track, guild_id)
                                    added_local += 1
                                    # persist progress and remaining items
                                    try:
                                        remaining = items[idx:]
                                        save_enqueue_state(guild_id, {'items': remaining, 'added': added_local, 'total': total_local, 'requester_id': getattr(ctx.author, 'id', None)})
                                    except Exception:
                                        pass
                                except Exception:
                                    pass

                                if progress_msg and (idx % CHUNK == 0 or idx == total_local):
                                    try:
                                        await progress_msg.edit(content=f'Enqueued {added_local}/{total_local} tracks from Spotify {spotify_res.get("type")} (in progress)...')
                                    except Exception:
                                        pass

                            # final update
                            if progress_msg:
                                try:
                                    await progress_msg.edit(content=f'Enqueued {added_local}/{total_local} tracks from Spotify {spotify_res.get("type")}.')
                                except Exception:
                                    pass

                            # schedule playback if needed
                            try:
                                vc = ctx.guild.voice_client
                                if not vc or not getattr(vc, 'is_connected', lambda: False)():
                                    preferred = None
                                    try:
                                        if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                                            preferred = ctx.author.voice.channel.id
                                    except Exception:
                                        preferred = None
                                    await _ensure_vc_connected(bot, ctx.guild, preferred_channel_id=preferred)
                                asyncio.create_task(_play_next(bot, guild_id))
                            except Exception:
                                pass

                            try:
                                await log_action(bot, ctx.author.id, 'play_playlist', {'title': getattr(spotify_res, 'get', lambda k, d=None: d)('name', 'spotify'), 'added': added_local})
                            except Exception:
                                pass
                        except asyncio.CancelledError:
                            # user cancelled the enqueue
                            try:
                                if progress_msg:
                                    await progress_msg.edit(content=f'Enqueue cancelled by user. Enqueued {added_local}/{total_local} tracks.')
                            except Exception:
                                pass
                        finally:
                            # cleanup persistence on finish or cancel
                            try:
                                remove_enqueue_state(guild_id)
                            except Exception:
                                pass
                            # cleanup task registry
                            try:
                                tasks = getattr(bot, 'sonus_enqueue_tasks', {})
                                if tasks.get(guild_id):
                                    del tasks[guild_id]
                            except Exception:
                                pass

                    # register and start background enqueue task
                    try:
                        if not hasattr(bot, 'sonus_enqueue_tasks'):
                            bot.sonus_enqueue_tasks = {}
                        task = asyncio.create_task(_enqueue_worker(to_enqueue, q, ctx, progress_msg, guild.id))
                        bot.sonus_enqueue_tasks[guild.id] = task
                    except Exception:
                        # fallback to inline processing if background task creation fails
                        pass

                    # start playback task if not already playing
                    try:
                        vc = guild.voice_client
                        if not vc or not getattr(vc, 'is_connected', lambda: False)():
                            preferred = None
                            try:
                                if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                                    preferred = ctx.author.voice.channel.id
                            except Exception:
                                preferred = None
                            vc = await _ensure_vc_connected(bot, guild, preferred_channel_id=preferred)
                            if not vc:
                                await log_action(bot, ctx.author.id, 'play_failed', {'reason': 'no_channel'})
                                return
                        asyncio.create_task(_play_next(bot, guild.id))
                    except Exception:
                        pass
                    await log_action(bot, ctx.author.id, 'play_playlist', {'title': getattr(spotify_res, 'get', lambda k, d=None: d)('name', 'spotify'), 'added': added})
                    return
                else:
                    info = await _yt_search(query)
            else:
                info = await _yt_search(query)
        if not info:
            await ctx.send('Could not find or extract the requested media.')
            return

        # If the extracted info contains multiple entries (playlist/album/search results),
        # enqueue each entry rather than attempting to play the container itself.
        entries = []
        if isinstance(info, dict) and info.get('entries'):
            try:
                entries = [e for e in (info.get('entries') or []) if isinstance(e, dict)]
            except Exception:
                entries = []

        if entries:
            # Enqueue up to a sensible limit to avoid flooding the queue (default 100)
            limit = int(os.getenv('SONUS_PLAYLIST_LIMIT') or 100)
            added = 0
            q = _ensure_guild_queue(bot, guild.id)
            for e in entries[:limit]:
                try:
                    url = _select_audio_url(e) or e.get('url') or e.get('webpage_url')
                    title = e.get('title') or (e.get('webpage_url') or str(url))
                    track = {'title': title, 'url': url, 'webpage_url': e.get('webpage_url')}
                    # preserve requester metadata
                    try:
                        if ctx.author:
                            track['requested_by'] = getattr(ctx.author, 'display_name', None) or getattr(ctx.author, 'name', None) or str(ctx.author)
                            track['requester_id'] = getattr(ctx.author, 'id', None)
                            if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                                track['requester_channel_id'] = ctx.author.voice.channel.id
                    except Exception:
                        pass
                    _queue_add(q, track)
                    added += 1
                except Exception:
                    continue

            if added == 0:
                await ctx.send('Could not extract entries from the provided playlist/album.')
                return

            embed = discord.Embed(title="Enqueued Playlist", description=f"Enqueued {added} tracks from playlist/album/search results.", color=0x1DB954)
            await ctx.send(embed=embed)
            # start playback task if not already playing
            try:
                vc = guild.voice_client
                if not vc or not getattr(vc, 'is_connected', lambda: False)():
                    preferred = None
                    try:
                        if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                            preferred = ctx.author.voice.channel.id
                    except Exception:
                        preferred = None
                    vc = await _ensure_vc_connected(bot, guild, preferred_channel_id=preferred)
                    if not vc:
                        await log_action(bot, ctx.author.id, 'play_failed', {'reason': 'no_channel'})
                        return
                # schedule play loop
                asyncio.create_task(_play_next(bot, guild.id))
            except Exception:
                pass
            await log_action(bot, ctx.author.id, 'play_playlist', {'title': getattr(info, 'get', lambda k, d=None: d)('title', 'playlist'), 'added': added})
            return

        # choose the best possible direct audio URL for single-entry results
        url = _select_audio_url(info) or info.get('url') or (info.get('formats') and info['formats'][0].get('url'))
        title = info.get('title') or query

        track = {'title': title, 'url': url, 'webpage_url': info.get('webpage_url')}
        # remember the requester's voice channel and identity
        try:
            if ctx.author:
                track['requested_by'] = getattr(ctx.author, 'display_name', None) or getattr(ctx.author, 'name', None) or str(ctx.author)
                track['requester_id'] = getattr(ctx.author, 'id', None)
            if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                track['requester_channel_id'] = ctx.author.voice.channel.id
        except Exception:
            pass

        q = _ensure_guild_queue(bot, guild.id)
        _queue_add(q, track)

        vc = guild.voice_client
        try:
            if not vc or not getattr(vc, 'is_connected', lambda: False)():
                # try to establish a voice connection robustly
                preferred = None
                try:
                    if ctx.author and getattr(ctx.author, 'voice', None) and getattr(ctx.author.voice, 'channel', None):
                        preferred = ctx.author.voice.channel.id
                except Exception:
                    preferred = None

                vc = await _ensure_vc_connected(bot, guild, preferred_channel_id=preferred)
                if not vc:
                    embed = discord.Embed(title="Playback Error", description='Bot is not connected to a voice channel and could not join your channel.', color=0xE63946)
                    await ctx.send(embed=embed)
                    await log_action(bot, ctx.author.id, 'play_failed', {'title': title, 'reason': 'no_channel'})
                    return
            else:
                # try moving to author's channel if different
                author_chan = getattr(ctx.author.voice, 'channel', None)
                if author_chan and vc.channel != author_chan:
                    try:
                        await vc.move_to(author_chan)
                    except Exception:
                        pass

            if not vc.is_playing() and not vc.is_paused():
                embed = discord.Embed(title="Now playing", description=title, color=0x1DB954)
                try:
                    if info.get('webpage_url'):
                        embed.url = info.get('webpage_url')
                except Exception:
                    pass
                await ctx.send(embed=embed)
                # start playback task
                asyncio.create_task(_play_next(bot, guild.id))
            else:
                embed = discord.Embed(title="Enqueued", description=title, color=0xFFD166)
                await ctx.send(embed=embed)

            await log_action(bot, ctx.author.id, 'play', {'title': title})
        except Exception as exc:
            embed = discord.Embed(title="Playback Error", description=str(exc), color=0xE63946)
            await ctx.send(embed=embed)
            await log_action(bot, ctx.author.id, 'play_failed', {'title': title, 'error': str(exc)})

    @bot.tree.command(name='play')
    @app_commands.describe(query='Search term or URL or id', source='Source type to play from')
    @app_commands.choices(source=[
        app_commands.Choice(name='YouTube / search', value='youtube'),
        app_commands.Choice(name='Playlist (local)', value='playlist'),
        app_commands.Choice(name='Album (local)', value='album'),
        app_commands.Choice(name='Radio (local)', value='radio'),
    ])
    async def _play_slash(interaction: discord.Interaction, query: str, source: str = 'youtube'):
        """Compact play slash command — choose a source type for clearer UX."""
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)

        # Route to local sources when requested
        src = (source or 'youtube').lower()
        try:
            if src == 'playlist':
                cmd = bot.get_command('playlist_play')
                if cmd:
                    await ctx.invoke(cmd, playlist_id=query)
                    return
            if src == 'album':
                cmd = bot.get_command('album')
                if cmd:
                    # album command expects action and name
                    await ctx.invoke(cmd, 'play', query)
                    return
            if src == 'radio':
                cmd = bot.get_command('radio')
                if cmd:
                    await ctx.invoke(cmd, 'play', query)
                    return
        except Exception:
            # fallback to default play behavior on any error
            pass

        # Default: treat as a normal play query or URL
        await _play(ctx, query=query)
    try:
        _play.help = (
            "Search term or URL to play/enqueue. Supports search terms, YouTube/Spotify/SoundCloud URLs and stream URLs. "
            "Use `playlist:<id>` to play playlists from data/playlists, `album:<id>` to play from data/albums, and `radio:<id>` to play a local radio station."
        )
    except Exception:
        pass

    @bot.command(name='enqueue_status')
    async def _enqueue_status(ctx: commands.Context):
        """Show status of any active background enqueue task for this guild."""
        guild = ctx.guild
        if not guild:
            await ctx.send('This command must be used in a guild.')
            return
        tasks = getattr(bot, 'sonus_enqueue_tasks', {})
        t = tasks.get(guild.id)
        if not t:
            await ctx.send('No active enqueue task for this guild.')
            return
        state = 'running'
        try:
            if t.cancelled():
                state = 'cancelled'
            elif t.done():
                state = 'finished'
        except Exception:
            pass
        await ctx.send(f'Enqueue task status: {state}')

    @bot.tree.command(name='enqueue_status')
    async def _enqueue_status_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _enqueue_status(ctx)
    try:
        _enqueue_status.help = "Show status of any active background enqueue task for your guild."
    except Exception:
        pass

    @bot.command(name='enqueue_cancel')
    async def _enqueue_cancel(ctx: commands.Context):
        """Cancel an active background enqueue for this guild."""
        guild = ctx.guild
        if not guild:
            await ctx.send('This command must be used in a guild.')
            return
        tasks = getattr(bot, 'sonus_enqueue_tasks', {})
        t = tasks.get(guild.id)
        if not t or t.done():
            await ctx.send('No active enqueue to cancel.')
            return
        try:
            t.cancel()
            await ctx.send('Enqueue cancellation requested.')
        except Exception:
            await ctx.send('Failed to cancel enqueue task.')

    @bot.tree.command(name='enqueue_cancel')
    async def _enqueue_cancel_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _enqueue_cancel(ctx)
    try:
        _enqueue_cancel.help = "Cancel an active background enqueue for this guild."
    except Exception:
        pass

    # ----- Music help and grouped slash commands -----
    @bot.command(name='music_help')
    async def _music_help(ctx: commands.Context):
        """Show help for music commands (prefix and slash)."""
        embed = discord.Embed(title="Sonus Music Commands", color=0x4CC9F0)
        try:
            cmds = [
                ('play', getattr(_play, 'help', 'Play a track or enqueue a query/url')),
                ('radio', getattr(_radio, 'help', 'List and play radio stations')),
                ('enqueue status/cancel', getattr(_enqueue_status, 'help', 'Enqueue status/cancel')),
                ('audiotest', getattr(_audiotest, 'help', 'Test extraction and probe without playing')),
            ]
            for name, desc in cmds:
                embed.add_field(name=f'S!{name}', value=desc or 'No description', inline=False)
        except Exception:
            embed.description = 'Music commands: play, radio, enqueue_status, enqueue_cancel, audiotest'
        await ctx.send(embed=embed)

    @bot.tree.command(name='music_help')
    async def _music_help_slash(interaction: discord.Interaction):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _music_help(ctx)

    # Create organized slash command groups for better UX
    try:
        music_group = app_commands.Group(name='music', description='Top-level music commands')

        enqueue_group = app_commands.Group(name='enqueue', description='Manage background enqueues', parent=music_group)

        @enqueue_group.command(name='status', description='Show status of background enqueue for this guild')
        async def _enqueue_status_group(interaction: discord.Interaction):
            await interaction.response.defer()
            ctx = await commands.Context.from_interaction(interaction)
            await _enqueue_status(ctx)

        @enqueue_group.command(name='cancel', description='Cancel background enqueue for this guild')
        async def _enqueue_cancel_group(interaction: discord.Interaction):
            await interaction.response.defer()
            ctx = await commands.Context.from_interaction(interaction)
            await _enqueue_cancel(ctx)

        playlist_group = app_commands.Group(name='playlist', description='Playlist and album helpers', parent=music_group)

        @playlist_group.command(name='enqueue', description='Enqueue a playlist/album URL or search')
        async def _playlist_enqueue(interaction: discord.Interaction, query: str):
            await interaction.response.defer()
            ctx = await commands.Context.from_interaction(interaction)
            await _play(ctx, query=query)

        @playlist_group.command(name='limit', description='Show current playlist enqueue limit')
        async def _playlist_limit(interaction: discord.Interaction):
            await interaction.response.defer()
            lim = int(os.getenv('SONUS_PLAYLIST_LIMIT') or 100)
            await interaction.followup.send(f'Playlist enqueue limit: {lim}')

        settings_group = app_commands.Group(name='settings', description='Sonus settings and diagnostics', parent=music_group)

        @music_group.command(name='help', description='Show paginated help for Sonus music commands')
        async def _music_help_pages(interaction: discord.Interaction):
            await interaction.response.defer()

            # collect commands and descriptions
            items = []
            try:
                for c in bot.commands:
                    name = c.name
                    desc = c.help or 'No description available.'
                    items.append((f'S!{name}', desc))
            except Exception:
                pass
            try:
                for c in bot.tree.walk_commands():
                    try:
                        # skip groups themselves
                        if isinstance(c, app_commands.Group):
                            continue
                        name = f'/{c.qualified_name}'
                        desc = c.description or 'No description available.'
                        items.append((name, desc))
                    except Exception:
                        continue
            except Exception:
                pass

            if not items:
                await interaction.followup.send('No command help available.')
                return

            # build pages
            PAGE_SIZE = 6
            pages = []
            for i in range(0, len(items), PAGE_SIZE):
                block = items[i:i+PAGE_SIZE]
                embed = discord.Embed(title='Sonus Music Help', color=0x4CC9F0)
                for name, desc in block:
                    embed.add_field(name=name, value=desc, inline=False)
                embed.set_footer(text=f'Page {i//PAGE_SIZE+1}/{(len(items)-1)//PAGE_SIZE+1}')
                pages.append(embed)

            class _HelpView(discord.ui.View):
                def __init__(self, pages):
                    super().__init__(timeout=180)
                    self.pages = pages
                    self.index = 0

                    # Page selector (limit to 25 options due to Discord limits)
                    options = []
                    total = len(self.pages)
                    for i in range(min(total, 25)):
                        options.append(discord.SelectOption(label=f'Page {i+1}', value=str(i)))

                    if options:
                        class PageSelect(discord.ui.Select):
                            def __init__(self, options, parent_view):
                                super().__init__(placeholder='Jump to page...', min_values=1, max_values=1, options=options)
                                self._parent = parent_view

                            async def callback(self, interaction: discord.Interaction):
                                try:
                                    val = int(self.values[0])
                                    self._parent.index = val
                                    await self._parent._update(interaction)
                                except Exception:
                                    await interaction.response.send_message('Invalid page selection.', ephemeral=True)

                        self.add_item(PageSelect(options, self))

                async def _update(self, interaction: discord.Interaction, *, edit=True):
                    # update footer to reflect current page
                    try:
                        embed = self.pages[self.index]
                        embed.set_footer(text=f'Page {self.index+1}/{len(self.pages)}')
                    except Exception:
                        pass
                    try:
                        if edit:
                            await interaction.response.edit_message(embed=embed, view=self)
                        else:
                            await interaction.followup.send(embed=embed)
                    except Exception:
                        try:
                            await interaction.followup.send(embed=embed)
                        except Exception:
                            pass

                @discord.ui.button(label='◀ Prev', style=discord.ButtonStyle.secondary)
                async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
                    if self.index > 0:
                        self.index -= 1
                        await self._update(interaction)

                @discord.ui.button(label='Next ▶', style=discord.ButtonStyle.secondary)
                async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
                    if self.index < len(self.pages)-1:
                        self.index += 1
                        await self._update(interaction)

                @discord.ui.button(label='Close', style=discord.ButtonStyle.danger)
                async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
                    try:
                        for child in list(self.children):
                            child.disabled = True
                        await interaction.response.edit_message(view=self)
                    except Exception:
                        pass
                    try:
                        # send a small ephemeral confirmation so user knows it closed
                        await interaction.followup.send('Help closed.', ephemeral=True)
                    except Exception:
                        try:
                            await interaction.response.send_message('Closed.', ephemeral=True)
                        except Exception:
                            pass

            view = _HelpView(pages)
            try:
                # ensure initial footer is accurate
                pages[0].set_footer(text=f'Page 1/{len(pages)}')
                await interaction.followup.send(embed=pages[0], view=view)
            except Exception:
                await interaction.followup.send(embed=pages[0])

        @settings_group.command(name='show', description='Show bot music-related settings for this process')
        async def _settings_show(interaction: discord.Interaction):
            await interaction.response.defer()
            vals = {
                'SONUS_RESUME_ON_STARTUP': os.getenv('SONUS_RESUME_ON_STARTUP') or 'unset',
                'SONUS_PLAYLIST_LIMIT': os.getenv('SONUS_PLAYLIST_LIMIT') or '100',
            }
            text = '\n'.join(f'{k}: {v}' for k, v in vals.items())
            await interaction.followup.send(f'```\n{text}\n```')

        bot.tree.add_command(music_group)
        bot.tree.add_command(enqueue_group)  
        bot.tree.add_command(playlist_group)
        bot.tree.add_command(settings_group)
    except Exception:
        # if building groups fails, ignore (older discord.py compatibility)
        pass

    @bot.command(name='radio')
    async def _radio(ctx: commands.Context, *, query: Optional[str] = None):
        """List and play radio stations. Usage: S!radio [name|index|search]

        Without arguments this lists available stations (by country/category).
        Provide a name or partial match to play the first matching station.
        """
        guild = ctx.guild
        try:
            data_dir = Path(__file__).parents[2] / 'data' / 'radios'
        except Exception:
            data_dir = None

        stations = []
        if data_dir and data_dir.exists():
            for f in data_dir.iterdir():
                if f.suffix.lower() in ('.json',):
                    try:
                        import json

                        j = json.loads(f.read_text())
                        # assume structure: { 'stations': [...] } or list
                        if isinstance(j, dict) and j.get('stations'):
                            for s in j.get('stations'):
                                s['_source_file'] = f.name
                                stations.append(s)
                        elif isinstance(j, list):
                            for s in j:
                                s['_source_file'] = f.name
                                stations.append(s)
                    except Exception:
                        continue

        if not stations:
            await ctx.send('No radio station data available.')
            return

        if not query:
            # show top 10 stations as examples
            msg = 'Available radio stations (sample):\n'
            for i, s in enumerate(stations[:10], start=1):
                name = s.get('title') or s.get('name') or s.get('title_long') or 'Unnamed'
                country = s.get('country') or s.get('_source_file')
                msg += f'{i}. {name} ({country})\n'
            msg += '\nUse `S!radio <name|index>` to play.'
            await ctx.send(msg)
            return

        # try numeric index
        q = query.strip()
        chosen = None
        if q.isdigit():
            idx = int(q) - 1
            if 0 <= idx < len(stations):
                chosen = stations[idx]

        if not chosen:
            # search by partial match on name/title
            lower = q.lower()
            for s in stations:
                name = (s.get('title') or s.get('name') or '')
                if lower in name.lower():
                    chosen = s
                    break

        if not chosen:
            await ctx.send('No matching radio station found.')
            return

        # attempt to play station by its stream URL
        url = chosen.get('url') or chosen.get('stream') or chosen.get('stream_url') or chosen.get('play_url')
        if not url:
            await ctx.send('Selected station has no playable URL.')
            return

        await ctx.send(f'Enqueuing radio: {chosen.get("title") or chosen.get("name")}')
        # reuse existing play logic by calling _play with the stream URL
        await _play(ctx, query=url)

    @bot.tree.command(name='radio')
    @app_commands.describe(query='Station name, index, or search term')
    async def _radio_slash(interaction: discord.Interaction, query: Optional[str] = None):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _radio(ctx, query=query)

    # Register `audiotest` only if it doesn't already exist (some modules provide it)
    if bot.get_command('audiotest') is None:
        async def _audiotest(ctx: commands.Context, *, query: str):
            """Prefix: S!audiotest <url|query> — test extraction and ffmpeg probe without playing."""
            guild = ctx.guild
            await ctx.send('Running audio test...')
            info = await _yt_search(query)
            if not info:
                embed = discord.Embed(title="Extraction Failed", description="yt-dlp could not find or extract the media.", color=0xE63946)
                await ctx.send(embed=embed)
                return

            candidate_urls = []
            direct = _select_audio_url(info)
            if direct:
                candidate_urls.append(direct)
            if info.get('webpage_url') and info.get('webpage_url') not in candidate_urls:
                candidate_urls.append(info.get('webpage_url'))
            # also include the original query as a last resort
            if query and query not in candidate_urls:
                candidate_urls.append(query)

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }

            results = []
            for src in candidate_urls:
                try:
                    await ctx.send(f'Testing source: {src}')
                    player = await _create_player_with_probe(src, ffmpeg_options, timeout=6.0)
                    try:
                        player.cleanup()
                    except Exception:
                        pass
                    results.append(f'SUCCESS: {src}')
                    break
                except Exception as exc:
                    results.append(f'FAILED: {src} -> {type(exc).__name__}: {str(exc)[:200]}')

            if not results:
                embed = discord.Embed(title="Audio Test", description="No candidate URLs were evaluated.", color=0xE63946)
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(title="Audio Test Results", description='\n'.join(results), color=0x4CC9F0)
            await ctx.send(embed=embed)

        try:
            bot.add_command(commands.Command(_audiotest, name='audiotest'))
        except Exception:
            # if registration fails for any reason, continue without crashing the whole module
            logger.info('Could not add audiotest command; it may already exist.')
    try:
        _audiotest.help = "Test extraction and ffmpeg probe for a given URL or search term (no playback)."
    except Exception:
        pass

    # Register a slash variant only if the tree doesn't already have it
    if bot.tree.get_command('audiotest') is None:
        @bot.tree.command(name='audiotest')
        async def _audiotest_slash(interaction: discord.Interaction, query: str):
            await interaction.response.defer()
            ctx = await commands.Context.from_interaction(interaction)
            await _audiotest(ctx, query=query)


async def _play_next(bot: commands.Bot, guild_id: int):
    q = getattr(bot, 'sonus_queues', {}).get(guild_id, None)
    if not q:
        return

    track = _queue_pop(q, guild_id=guild_id)
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    # enrich track with any available metadata before playback (duration, thumbnail, uploader)
    try:
        info = await _yt_search(track.get('webpage_url') or track.get('url') or track.get('title') or '')
        if info:
            # prefer explicit duration/thumbnail if present
            if info.get('duration') and not track.get('duration'):
                track['duration'] = info.get('duration')
            if info.get('thumbnail') and not track.get('thumbnail'):
                track['thumbnail'] = info.get('thumbnail')
            if info.get('uploader') and not track.get('uploader'):
                track['uploader'] = info.get('uploader')
            # normalize webpage_url
            if info.get('webpage_url') and not track.get('webpage_url'):
                track['webpage_url'] = info.get('webpage_url')
    except Exception:
        pass

    # ensure a voice client exists (reconnect if needed)
    vc = guild.voice_client
    preferred_chan = None
    try:
        # if track stored the requester's channel id, prefer that
        preferred_chan = track.get('requester_channel_id')
    except Exception:
        preferred_chan = None

    if not vc or not getattr(vc, 'is_connected', lambda: False)():
        vc = await _ensure_vc_connected(bot, guild, preferred_channel_id=preferred_chan)
        if not vc:
            # couldn't re-establish voice connection; skip playback and try next
            logger.warning('Could not re-establish voice connection for guild %s', guild_id)
            await _play_next(bot, guild_id)
            return

    # FFmpeg options
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    source_url = track.get('url') or track.get('webpage_url')
    if not source_url:
        return

    tried_sources: List[str] = []

    async def _extract_candidates(url_or_page: str) -> List[str]:
        info = await _yt_search(url_or_page)
        if not info:
            return []
        urls: List[str] = []
        direct = _select_audio_url(info)
        if direct:
            urls.append(direct)
        if info.get('webpage_url') and info.get('webpage_url') not in urls:
            urls.append(info.get('webpage_url'))
        return urls

    lower_src = (source_url or '').lower()
    candidate_urls: List[str] = [source_url]
    if (not source_url.startswith('http')) or ('youtube' in lower_src) or ('soundcloud' in lower_src) or ('spotify' in lower_src):
        candidate_urls = await _extract_candidates(source_url)
    else:
        if track.get('webpage_url'):
            candidate_urls += await _extract_candidates(track.get('webpage_url'))

    # dedupe while preserving order
    seen = set()
    candidate_urls = [u for u in candidate_urls if u and (u not in seen and not seen.add(u))]

    for src in candidate_urls:
        tried_sources.append(src)
        try:
            player = await _create_player_with_probe(src, ffmpeg_options, timeout=12.0)
            try:
                # record the actual source and start time for UI/diagnostics
                track['source'] = src
                track['started_at'] = time.time()
                setattr(bot, 'sonus_now_playing', track)
            except Exception:
                pass
            try:
                vc.play(player, after=lambda e: asyncio.get_event_loop().create_task(_after_play(bot, guild_id, e)))
            except Exception as play_exc:
                logger.exception('vc.play failed for %s: %s', src, play_exc)
                try:
                    player.cleanup()
                except Exception:
                    pass
                continue
            return
        except Exception as exc:
            logger.exception('Probe/plain creation failed for %s: %s', src, exc)
            # attach exception details to tried_sources for diagnostics
            tried_sources.append(f"error:{src}:{type(exc).__name__}:{str(exc)[:200]}")
            # try next

    logger.error('All probes failed for track %s (tried: %s)', track.get('title'), tried_sources)
    await log_action(bot, 0, 'playback_error', {'guild_id': guild_id, 'track': track.get('title'), 'tried': tried_sources})
    try:
        setattr(bot, 'sonus_now_playing', None)
    except Exception:
        pass
    # notify an appropriate text channel in the guild with guidance for resolving common issues
    try:
        guild = bot.get_guild(guild_id)
        async def _notify_guild(message: str):
            try:
                if not guild:
                    return
                ch = None
                # prefer the system channel, else first writable text channel
                if getattr(guild, 'system_channel', None):
                    ch = guild.system_channel
                if ch is None:
                    for c in guild.text_channels:
                        try:
                            perms = c.permissions_for(guild.me)
                        except Exception:
                            perms = None
                        if perms and perms.send_messages:
                            ch = c
                            break
                if ch:
                    await ch.send(message)
            except Exception:
                logger.exception('Failed to send playback diagnostic message to guild')

        hint = (
            "Failed to start playback for the requested track. This can be caused by: \n"
            "- YouTube requiring cookies for this content (set YTDL_COOKIEFILE env var).\n"
            "- FFmpeg not available or unable to open network streams.\n"
            "- Network/DNS issues on the host.\n"
            "Admins: check bot logs for detailed errors and ensure `ffmpeg` is installed."
        )
        await _notify_guild(hint)
    except Exception:
        logger.exception('Failed while attempting to notify guild about playback failure')

    # continue to next track (if any)
    await _play_next(bot, guild_id)


# Enqueue resume helpers were removed to avoid import-time syntax issues.
# Persistence helpers are available in src/utils/enqueue_store.py and
# can be integrated later when ready.


async def _after_play(bot: commands.Bot, guild_id: int, error):
    if error:
        logger.exception('Error in playback: %s', error)
    try:
        setattr(bot, 'sonus_now_playing', None)
    except Exception:
        pass
    await _play_next(bot, guild_id)


# resume_persisted_enqueues removed; deferred until persistence logic is stabilized.
