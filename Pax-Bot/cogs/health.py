import discord
from discord.ext import commands
from discord import app_commands


class HealthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx: commands.Context):
        await ctx.send('Pong!')

    @app_commands.command(name='ping', description='Check bot responsiveness')
    async def ping_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message('Pong!')


async def setup(bot: commands.Bot):
    cog = HealthCog(bot)
    await bot.add_cog(cog)
    try:
        bot.tree.add_cog(cog)
    except Exception:
        pass
