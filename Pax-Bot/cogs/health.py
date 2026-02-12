import discord
from discord.ext import commands
from discord import app_commands


class HealthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context):
        """Respond with Pong and latency."""
        latency = round(self.bot.latency * 1000)  # Convert to ms
        await ctx.send(f'Pong! Latency: {latency}ms')

    @app_commands.command(name='ping', description='Check bot responsiveness')
    async def ping_slash(self, interaction: discord.Interaction):
        """Respond with Pong and latency for slash commands."""
        latency = round(self.bot.latency * 1000)  # Convert to ms
        await interaction.response.send_message(f'Pong! Latency: {latency}ms')


async def setup(bot: commands.Bot):
    cog = HealthCog(bot)
    await bot.add_cog(cog)
    try:
        bot.tree.add_cog(cog)
    except Exception:
        pass
