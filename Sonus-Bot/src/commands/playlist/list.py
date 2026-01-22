from discord.ext import commands
from discord import app_commands
from src.utils.playlist_store import list_playlists, get_playlist


def register(bot: commands.Bot):
    @bot.command(name='playlist_list')
    async def _list(ctx: commands.Context, only_mine: bool = False):
        """S!playlist list [only_mine] - list playlists or only your playlists"""
        owner = ctx.author.id if only_mine else None
        pls = list_playlists(owner)
        if not pls:
            await ctx.send('No playlists found.')
            return
        # present as embed
        e = commands.Embed = None
        embed = discord.Embed(title='Playlists', color=0x1DB954)
        for p in pls:
            embed.add_field(name=f"{p['id']} - {p['name']}", value=f"Tracks: {len(p.get('tracks', []))}", inline=False)
        await ctx.send(embed=embed)

    @bot.tree.command(name='playlist-list')
    @app_commands.describe(only_mine='Show only your playlists')
    async def _list_slash(interaction: commands.Context, only_mine: bool = False):
        await interaction.response.defer(ephemeral=True)
        owner = interaction.user.id if only_mine else None
        pls = list_playlists(owner)
        if not pls:
            await interaction.followup.send('No playlists found.', ephemeral=True)
            return
        embed = discord.Embed(title='Playlists', color=0x1DB954)
        for p in pls:
            embed.add_field(name=f"{p['id']} - {p['name']}", value=f"Tracks: {len(p.get('tracks', []))}", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name='playlist-show')
    @app_commands.describe(playlist_id='Playlist id to show')
    async def _show_slash(interaction: commands.Context, playlist_id: str):
        await interaction.response.defer(ephemeral=True)
        pl = get_playlist(playlist_id)
        if not pl:
            await interaction.followup.send('Playlist not found.', ephemeral=True)
            return
        tracks = pl.get('tracks', []) or []
        embed = discord.Embed(title=f"Playlist: {pl.get('name')}", description=f"ID: {pl.get('id')}", color=0x1DB954)
        lines = []
        for i, t in enumerate(tracks[:50]):
            title = t.get('title') if isinstance(t, dict) else str(t)
            lines.append(f"{i}. {title}")
        embed.add_field(name='Tracks', value='\n'.join(lines) if lines else '(empty)', inline=False)
        if len(tracks) > 50:
            embed.set_footer(text=f"And {len(tracks)-50} more tracks")
        await interaction.followup.send(embed=embed, ephemeral=True)
