from discord.ext import commands
from discord import app_commands
from src.utils.playlist_store import remove_playlist, remove_track, get_playlist
from src.utils.audit import log_action


def register(bot: commands.Bot):
    @bot.command(name='playlist_remove')
    async def _remove(ctx: commands.Context, playlist_id: str, what: str = None):
        """S!playlist remove <playlist_id> [track_index|'playlist'] - remove a track or delete playlist"""
        try:
            if what is None or what.lower() == 'playlist':
                # delete whole playlist
                remove_playlist(playlist_id, ctx.author.id)
                await ctx.send(f'✅ Playlist {playlist_id} deleted')
                await log_action(bot, ctx.author.id, 'playlist_delete', {'id': playlist_id})
                return
            # try parse index
            idx = int(what)
            removed = remove_track(playlist_id, ctx.author.id, idx)
            await ctx.send(f"✅ Removed track '{removed.get('title')}' from {playlist_id}")
            await log_action(bot, ctx.author.id, 'playlist_remove_track', {'id': playlist_id, 'index': idx})
        except PermissionError:
            await ctx.send('You are not the owner of this playlist.')
        except FileNotFoundError:
            await ctx.send('Playlist not found.')
        except ValueError:
            await ctx.send('Invalid track index')
        except Exception as exc:
            await ctx.send(f'Failed to remove: {exc}')

    @bot.tree.command(name='playlist-remove')
    @app_commands.describe(playlist_id='Playlist id', what="'playlist' to delete or track index")
    async def _remove_slash(interaction: commands.Context, playlist_id: str, what: str | None = None):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _remove(ctx, playlist_id=playlist_id, what=what)
