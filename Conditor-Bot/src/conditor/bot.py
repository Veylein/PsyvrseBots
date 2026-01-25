import logging
from discord.ext import commands
import discord

logger = logging.getLogger("conditor.bot")


def create_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.messages = True
    intents.guilds = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot
