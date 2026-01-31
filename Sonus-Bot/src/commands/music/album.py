import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
from typing import Dict, Optional

from src.utils.loaders import ROOT, load_json
from src.utils.audit import log_action


ALBUMS_PATH = ROOT / "data" / "albums"
_ALBUM_CACHE: Dict[str, Dict] = {}


def _load_albums() -> Dict[str, Dict]:
    global _ALBUM_CACHE
    if _ALBUM_CACHE:
        return _ALBUM_CACHE
    albums = {}
    if ALBUMS_PATH.exists():
        for p in ALBUMS_PATH.glob("*.json"):
            try:
                data = load_json(f"data/albums/{p.name}")
                if data.get("id"):
                    albums[data["id"].lower()] = data
            except Exception:
                continue
    _ALBUM_CACHE = albums
    return albums


def _find_album(name: str) -> Optional[Dict]:
    albums = _load_albums()
    if not name:
        return None
    key = name.lower().strip()
    if key in albums:
        return albums[key]
    for a in albums.values():
        if a.get("name", "").lower() == key:
            return a
    return None


def _ensure_guild_queue(bot: commands.Bot, guild_id: int):
    q = getattr(bot, 'sonus_queues', None)
    if q is None:
        bot.sonus_queues = {}
        q = bot.sonus_queues
    if guild_id not in q:
        q[guild_id] = []
    return q[guild_id]


def _enqueue_album(bot: commands.Bot, guild: discord.Guild, album: Dict, start_index: int = 0) -> int:
    tracks = album.get('tracks', []) or []
    if start_index and start_index > 0:
        tracks = tracks[start_index:]
    q = _ensure_guild_queue(bot, guild.id)
    added = 0
    for t in tracks:
        # Track dicts may use 'source' or 'uri'
        uri = t.get('source') or t.get('uri') or t.get('url')
        title = t.get('title') or t.get('name') or uri
        q.append({'title': title, 'url': uri, 'webpage_url': uri})
        added += 1
    return added


def register(bot: commands.Bot):
    @bot.command(name='album')
    async def _album(ctx: commands.Context, action: str = 'list', *, name: str = ''):
        """Prefix: S!album list|play <name> — play albums from the local `data/albums` collection."""
        action = (action or '').lower()
        if action == 'list':
            albums = _load_albums()
            if not albums:
                await ctx.send('No albums available.')
                return
            desc = '\n'.join(f"• **{a.get('name', aid)}** — `{aid}`" for aid, a in albums.items())
            await ctx.send(embed=discord.Embed(title='Albums', description=desc, color=0x4CC9F0))
            return

        if action != 'play':
            await ctx.send('Usage: `S!album list` or `S!album play <name>`')
            return

        guild = ctx.guild
        if guild is None:
            await ctx.send('Playback is only available in a guild.')
            return

        album = _find_album(name)
        if not album:
            await ctx.send('Unknown album. Try `S!album list`.')
            return

        added = _enqueue_album(bot, guild, album)
        if added <= 0:
            await ctx.send('No tracks were enqueued (album may be empty).')
            return
        await ctx.send(embed=discord.Embed(title='Album Enqueued', description=f"Enqueued {added} tracks from {album.get('name')}", color=0x1DB954))
        await log_action(bot, getattr(ctx.author, 'id', None), 'album_play', {'album': album.get('id'), 'added': added})

    @bot.tree.command(name='album-play')
    @app_commands.describe(name='Album id or name from data/albums')
    async def _album_play_slash(interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _album(ctx, action='play', name=name)