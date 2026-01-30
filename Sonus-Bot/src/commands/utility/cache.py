import discord
from discord.ext import commands
from discord import app_commands

from src.utils.ytdl_cache import cache_clear, cache_stats


def register(bot: commands.Bot):
    @bot.command(name='ytdl_cache_clear')
    async def _cache_clear(ctx: commands.Context):
        try:
            cache_clear()
            await ctx.send('ytdl cache cleared.')
        except Exception as exc:
            await ctx.send(f'Failed to clear cache: {exc}')

    @bot.tree.command(name='ytdl-cache-clear')
    async def _cache_clear_slash(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _cache_clear(ctx)

    @bot.command(name='ytdl_cache_stats')
    async def _cache_stats(ctx: commands.Context):
        try:
            s = cache_stats()
            await ctx.send(f"Cache entries: {s.get('entries')}, valid: {s.get('valid')}, ttl: {s.get('ttl')}, persistent: {s.get('persistent')}")
        except Exception as exc:
            await ctx.send(f'Failed to read cache stats: {exc}')

    @bot.tree.command(name='ytdl-cache-stats')
    async def _cache_stats_slash(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _cache_stats(ctx)
