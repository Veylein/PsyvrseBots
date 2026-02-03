import os
import discord
from discord.ext import commands
import asyncio

# Fetch the token from the environment variable
TOKEN = os.getenv("EVENTUS_TOKEN")

if not TOKEN:
    print("ERROR: Discord bot token not set.")
    exit(1)

# Set up the bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="E!", intents=intents, help_command=None)

async def load_cogs():
    await bot.load_extension('cogs.activity')
    await bot.load_extension('cogs.eventos')
    await bot.load_extension('cogs.topicai')
    await bot.load_extension('cogs.dashboard')
    await bot.load_extension('cogs.momentum')
    await bot.load_extension('cogs.rules')
    await bot.load_extension('cogs.help')
    await bot.load_extension('cogs.general')
    await bot.load_extension('cogs.owner')
    await bot.load_extension('cogs.slash')

# Event to trigger when bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await load_cogs()

# Run the bot
if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))
