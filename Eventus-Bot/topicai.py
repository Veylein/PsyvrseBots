import discord
from discord.ext import commands
from discord import app_commands, Interaction
import random

TOPIC_CATEGORIES = {
    "fun": [
        "What's a weird food combo you love?",
        "If you could teleport anywhere right now, where would you go?",
        "What's your favorite meme format?"
    ],
    "debate": [
        "Is AI a threat or a tool?",
        "Should pineapple go on pizza?",
        "Is social media good for society?"
    ]
}


class TopicAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="topic", description="Drop a new topic in chat.")
    async def topic(self, ctx, category: str = None):
        category = category or "fun"
        topic = random.choice(TOPIC_CATEGORIES.get(category, TOPIC_CATEGORIES["fun"]))
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"💡 **TopicAI Suggests:** {topic}")
        else:
            await ctx.send(f"💡 **TopicAI Suggests:** {topic}")

async def setup(bot):
    await bot.add_cog(TopicAI(bot))
