from discord.ext import commands

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rules", description="Show blocked keywords and rule enforcement.")
    async def rules(self, ctx):
        blocked_keywords = [
            'joke', 'meme', 'coin', 'currency', 'ban', 'kick', 'mute', 'warn', 'music', 'play', 'nsfw', 'game', 'trivia', 'quiz', 'fact', 'funfact', 'entertainment'
        ]
        msg = "Blocked keywords: " + ', '.join(blocked_keywords)
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(Rules(bot))
