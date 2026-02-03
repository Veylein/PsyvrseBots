import discord
from discord.ext import commands

class Rules(commands.Cog):
    """Enforces rules related to blocked keywords and content."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rules")
    async def rules(self, ctx):
        """Show blocked keywords and rule enforcement."""
        blocked_keywords = [
            'joke', 'meme', 'coin', 'currency', 'ban', 'kick', 'mute', 'warn', 'music', 'play', 'nsfw', 'game', 'trivia', 'quiz', 'fact', 'funfact', 'entertainment'
        ]
        msg = "Blocked keywords: " + ', '.join(blocked_keywords)
        await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(Rules(bot))
