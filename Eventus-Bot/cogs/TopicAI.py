import discord
from discord.ext import commands
import random

CATEGORY_KEYWORDS = {
    'memes': ['meme', 'memes', 'funny', 'lol'],
    'music': ['song', 'music', 'album', 'playlist'],
    'gaming': ['game', 'gaming', 'fps'],
    'art': ['art', 'drawing', 'paint'],
}

CATEGORY_TOPICS = {
    'memes': ['Share your favorite meme of the week!', 'What meme format never gets old?'],
    'music': ['What are you listening to right now?', 'Which album should everyone listen to once?'],
    'gaming': ['What game are you playing?', 'Single-player or multiplayer — which do you prefer?'],
    'art': ['Share a piece of art you made recently!', 'What color palette are you using right now?'],
}

class TopicAI(commands.Cog):
    """Generates topics for discussion."""

    def __init__(self, bot):
        self.bot = bot

    def extract_keywords(self, texts):
        """Extract keywords from recent chat messages."""
        words = []
        for text in texts:
            words.extend(text.split())
        return random.choice(words)  # Simplified for now

    @commands.command(name="topic")
    async def topic(self, ctx):
        """Generate a topic for the server."""
        keywords = self.extract_keywords(['sample message', 'another example'])
        category = random.choice(list(CATEGORY_KEYWORDS.keys()))
        topic = random.choice(CATEGORY_TOPICS.get(category, []))
        await ctx.send(f"💡 **Topic Suggestion**: {topic}")

async def setup(bot):
    await bot.add_cog(TopicAI(bot))
