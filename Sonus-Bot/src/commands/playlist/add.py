from discord.ext import commands
from discord import app_commands
from src.utils.playlist_store import add_track, get_playlist
from src.utils.audit import log_action
import os
import yt_dlp


_YTDL_COOKIEFILE = os.getenv('YTDL_COOKIEFILE') or os.getenv('YTDL_COOKIES')

YTDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'nocheckcertificate': True,
    'no_warnings': True,
}
if _YTDL_COOKIEFILE:
    YTDL_OPTS['cookiefile'] = _YTDL_COOKIEFILE


def _extract_title_and_url(query: str):
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
            info = ytdl.extract_info(query, download=False)
            title = info.get('title') or query
            url = info.get('webpage_url') or info.get('url') or query
            return title, url
    except Exception:
        return query, query


def register(bot: commands.Bot):
    @bot.command(name='playlist_add')
    async def _add(ctx: commands.Context, playlist_id: str, *, query: str):
        """S!playlist add <playlist_id> <url|search> - add a track to your playlist"""
        try:
            pl = get_playlist(playlist_id)
            if not pl:
                await ctx.send('Playlist not found')
                return
            title, url = _extract_title_and_url(query)
            track = add_track(playlist_id, ctx.author.id, title, url)
            await ctx.send(f"✅ Added '{track['title']}' to playlist {pl['name']}")
            await log_action(bot, ctx.author.id, 'playlist_add', {'playlist': playlist_id, 'title': track['title']})
        except PermissionError:
            await ctx.send('You are not the owner of this playlist.')
        except Exception as exc:
            await ctx.send(f'Failed to add track: {exc}')

    @bot.tree.command(name='playlist-add')
    @app_commands.describe(playlist_id='Playlist id', query='URL or search term')
    async def _add_slash(interaction: commands.Context, playlist_id: str, query: str):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _add(ctx, playlist_id=playlist_id, query=query)
