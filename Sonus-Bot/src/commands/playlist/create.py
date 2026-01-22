from discord.ext import commands
from discord import app_commands
from src.utils.playlist_store import create_playlist, get_playlist
from src.utils.audit import log_action


def register(bot: commands.Bot):
    @bot.command(name='playlist_create')
    async def _create(ctx: commands.Context, *, name: str):
        """S!playlist create <name> - create a new playlist you own"""
        try:
            pl = create_playlist(name, ctx.author.id)
            await ctx.send(f"✅ Created playlist '{pl['name']}' (id: {pl['id']})")
            await log_action(bot, ctx.author.id, 'playlist_create', {'id': pl['id'], 'name': pl['name']})
        except FileExistsError:
            await ctx.send("A playlist with that name already exists.")
        except Exception as exc:
            await ctx.send(f"Failed to create playlist: {exc}")

    @bot.tree.command(name='playlist-create')
    @app_commands.describe(name='Playlist name')
    async def _create_slash(interaction: commands.Context, name: str):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _create(ctx, name=name)
