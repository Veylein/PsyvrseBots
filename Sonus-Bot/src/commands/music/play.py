import asyncio
import time
from typing import Optional, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands
import os
import yt_dlp

from src.logger import setup_logger
from src.utils.audit import log_action

logger = setup_logger(__name__)


_YTDL_COOKIEFILE = os.getenv('YTDL_COOKIEFILE') or os.getenv('YTDL_COOKIES')

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
    return None


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


def _queue_add(q, item: Any):
    try:
        if hasattr(q, 'enqueue'):
            q.enqueue(item)
            return
        if hasattr(q, 'append'):
            q.append(item)
            return
        # fallback
        q.enqueue(item)
    except Exception:
        try:
            q.append(item)
        except Exception:
            raise


def _queue_pop(q):
    try:
        if hasattr(q, 'dequeue'):
            return q.dequeue()
        if hasattr(q, 'pop'):
            # assume list-like pop(0)
            try:
                return q.pop(0)
            except TypeError:
                return q.pop()
        return None
    except Exception:
        return None


async def _create_player_with_probe(url: str, ffmpeg_options: Dict[str, str], timeout: float = 12.0):
    loop = asyncio.get_running_loop()

    def do_probe(u: str):
        return discord.FFmpegOpusAudio.from_probe(u, **ffmpeg_options)

    def do_plain(u: str):
        return discord.FFmpegOpusAudio(u, **ffmpeg_options)
    # try probe first with escalating timeouts and small backoffs, then fallback to plain construction.
    last_exc = None
    timeouts = [timeout, timeout * 2]
    for attempt, t in enumerate(timeouts, start=1):
        try:
            player = await asyncio.wait_for(loop.run_in_executor(None, do_probe, url), timeout=t)
            logger.debug('Probe succeeded on attempt %d for %s (timeout=%s)', attempt, url, t)
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

        info = await _yt_search(query)
        if not info:
            await ctx.send('Could not find or extract the requested media.')
            return

        # choose the best possible direct audio URL
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
                bot.loop.create_task(_play_next(bot, guild.id))
            else:
                embed = discord.Embed(title="Enqueued", description=title, color=0xFFD166)
                await ctx.send(embed=embed)

            await log_action(bot, ctx.author.id, 'play', {'title': title})
        except Exception as exc:
            embed = discord.Embed(title="Playback Error", description=str(exc), color=0xE63946)
            await ctx.send(embed=embed)
            await log_action(bot, ctx.author.id, 'play_failed', {'title': title, 'error': str(exc)})

    @bot.tree.command(name='play')
    @app_commands.describe(query='Search term or URL')
    async def _play_slash(interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        await _play(ctx, query=query)

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

    track = _queue_pop(q)
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


async def _after_play(bot: commands.Bot, guild_id: int, error):
    if error:
        logger.exception('Error in playback: %s', error)
    try:
        setattr(bot, 'sonus_now_playing', None)
    except Exception:
        pass
    await _play_next(bot, guild_id)
