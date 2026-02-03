import discord
from discord.ext import commands

class General(commands.Cog):
    """Handles general bot commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="test")
    async def test(self, ctx):
        """Test command to check if bot is working."""
        await ctx.send("The bot is working!")

async def setup(bot):
    await bot.add_cog(General(bot))
