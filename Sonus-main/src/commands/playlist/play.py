from typing import Dict, Any

import discord
from discord.ext import commands
from discord import app_commands

from src.utils.playlist_store import get_playlist
from src.utils.audit import log_action

# import the internal play helper to start playback when enqueued
try:
    from src.commands.music.play import _play_next
except Exception:
    _play_next = None


def _ensure_guild_queue(bot: commands.Bot, guild_id: int):
    q = getattr(bot, 'sonus_queues', None)
    if q is None:
        bot.sonus_queues = {}
        q = bot.sonus_queues
    if guild_id not in q:
        q[guild_id] = []
    return q[guild_id]


def _ensure_track_queue(bot: commands.Bot):
    tq = getattr(bot, 'track_queue', None)
    if tq is None:
        try:
            from src.audio.queue import TrackQueue

            bot.track_queue = TrackQueue()
            tq = bot.track_queue
        except Exception:
            bot.track_queue = None
            tq = None
    return tq


async def _enqueue_playlist(bot: commands.Bot, author, guild, playlist_id: str, start_index: int = 0, to_track_queue: bool = False, progress_callback=None) -> int:
    pl = get_playlist(playlist_id)
    if not pl:
        return 0
    tracks = pl.get('tracks', []) or []
    if start_index and start_index > 0:
        tracks = tracks[start_index:]

    added = 0
    # helper to report progress
    def _report(n: int):
        try:
            if callable(progress_callback):
                progress_callback(n)
        except Exception:
            pass

    if to_track_queue:
        tq = _ensure_track_queue(bot)
        if tq is None:
            return 0
        for t in tracks:
            title = t.get('title') if isinstance(t, dict) else str(t)
            uri = t.get('uri') if isinstance(t, dict) else str(t)
            tq.add({'title': title, 'url': uri, 'webpage_url': uri})
            added += 1
            if added % 10 == 0:
                _report(added)
        _report(added)
        return added

    # else enqueue into guild sonus_queues
    q = _ensure_guild_queue(bot, guild.id)
    for t in tracks:
        title = t.get('title') if isinstance(t, dict) else str(t)
        uri = t.get('uri') if isinstance(t, dict) else str(t)
        q.append({'title': title, 'url': uri, 'webpage_url': uri})
        added += 1
        if added % 10 == 0:
            _report(added)
    _report(added)
    return added


def register(bot: commands.Bot):
    @bot.command(name='playlist_play')
    async def _playlist_play(ctx: commands.Context, playlist_id: str, start_index: int = 0, to_track_queue: bool = False):
        """S!playlist_play <id> [start_index] — enqueue an existing playlist into the guild queue
        Use to_track_queue=True to enqueue into `bot.track_queue` instead of guild queues.
        """
        guild = ctx.guild
        if guild is None:
            await ctx.send('Playlist playback is only available in a guild.')
            return

        pl = get_playlist(playlist_id)
        if not pl:
            await ctx.send('Playlist not found.')
            return

        # send initial confirmation embed and update with progress for large playlists
        embed = discord.Embed(title="Enqueueing Playlist", description=f"{pl.get('name')} ({playlist_id})", color=0x1DB954)
        embed.add_field(name="Status", value="Starting...", inline=False)
        embed.set_footer(text=f"Requested by {getattr(ctx.author, 'display_name', str(ctx.author))}")
        status_msg = await ctx.send(embed=embed)

        def _progress(n: int):
            try:
                embed.set_field_at(0, name="Status", value=f"Enqueued {n} tracks...", inline=False)
                try:
                    # edit may fail if message deleted; ignore
                    coro = status_msg.edit
                    # schedule edit
                    import asyncio

                    asyncio.get_event_loop().create_task(coro(embed=embed))
                except Exception:
                    pass
            except Exception:
                pass

        added = await _enqueue_playlist(bot, ctx.author, guild, playlist_id, start_index=start_index, to_track_queue=to_track_queue, progress_callback=_progress)
        if added <= 0:
            await status_msg.edit(embed=discord.Embed(title="Enqueue Failed", description="No tracks enqueued (playlist empty or error).", color=0xE74C3C))
            return

        embed.set_field_at(0, name="Status", value=f"✅ Enqueued {added} tracks", inline=False)
        embed.add_field(name="Playlist", value=pl.get('name'), inline=True)
        embed.add_field(name="Tracks added", value=str(added), inline=True)
        await status_msg.edit(embed=embed)
        await log_action(bot, ctx.author.id, 'playlist_play', {'playlist': playlist_id, 'added': added})

        # Attempt to start playback if enqueued into guild queue
        if not to_track_queue:
            try:
                guild_obj = bot.get_guild(guild.id)
                vc = guild_obj.voice_client if guild_obj else None
                if not vc or not vc.is_connected():
                    # try to connect to the author's channel if available
                    author_chan = getattr(ctx.author.voice, 'channel', None)
                    if author_chan:
                        try:
                            await author_chan.connect()
                        except Exception:
                            pass
                # kick off play loop if available and not playing
                if _play_next is not None:
                    try:
                        bot.loop.create_task(_play_next(bot, guild.id))
                    except Exception:
                        pass
            except Exception:
                pass


    @bot.tree.command(name='playlist-play')
    @app_commands.describe(playlist_id='Playlist id to enqueue')
    async def _playlist_play_slash(interaction: discord.Interaction, playlist_id: str, start_index: int = 0):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index)

    @bot.command(name='playlist')
    async def _playlist_group(ctx: commands.Context, subcommand: str, playlist_id: str, maybe_index: str | None = None):
        """Group-style helper: S!playlist play <id> | S!playlist enqueue <id> [start_index] | S!playlist enqueue_tq <id> [start_index]"""
        sub = (subcommand or '').lower()
        start_index = 0
        if maybe_index:
            try:
                start_index = int(maybe_index)
            except Exception:
                start_index = 0

        if sub in ('play', 'enqueue'):
            await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index, to_track_queue=False)
            return
        if sub == 'list':
            # show playlist contents
            pl = get_playlist(playlist_id)
            if not pl:
                await ctx.send('Playlist not found.')
                return
            tracks = pl.get('tracks', []) or []
            if not tracks:
                await ctx.send('Playlist is empty.')
                return
            # build embed listing up to 50 tracks
            e = discord.Embed(title=f"Playlist: {pl.get('name')}", description=f"ID: {pl.get('id')}")
            lines = []
            for i, t in enumerate(tracks[:50]):
                title = t.get('title') if isinstance(t, dict) else str(t)
                lines.append(f"{i}. {title}")
            e.add_field(name='Tracks', value='\n'.join(lines), inline=False)
            if len(tracks) > 50:
                e.set_footer(text=f"And {len(tracks)-50} more tracks")
            await ctx.send(embed=e)
            return
        if sub in ('enqueue_tq', 'enqueue-tq', 'enqueue_tq') or sub == 'enqueue_tq':
            await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index, to_track_queue=True)
            return

        await ctx.send('Unknown subcommand. Use "play" or "enqueue" or "enqueue_tq"')

    @bot.command(name='playlist_enqueue')
    async def _playlist_enqueue(ctx: commands.Context, playlist_id: str, start_index: int = 0):
        await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index, to_track_queue=False)

    @bot.command(name='playlist_enqueue_tq')
    async def _playlist_enqueue_tq(ctx: commands.Context, playlist_id: str, start_index: int = 0):
        await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index, to_track_queue=True)

    @bot.tree.command(name='playlist-enqueue')
    @app_commands.describe(playlist_id='Playlist id to enqueue', start_index='Start at index (0-based)')
    async def _playlist_enqueue_slash(interaction: discord.Interaction, playlist_id: str, start_index: int = 0):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index, to_track_queue=False)

    @bot.tree.command(name='playlist-enqueue-tq')
    @app_commands.describe(playlist_id='Playlist id to enqueue to TrackQueue', start_index='Start at index (0-based)')
    async def _playlist_enqueue_tq_slash(interaction: discord.Interaction, playlist_id: str, start_index: int = 0):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _playlist_play(ctx, playlist_id=playlist_id, start_index=start_index, to_track_queue=True)
