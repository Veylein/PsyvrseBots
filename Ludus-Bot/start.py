"""Minimal Ludus-Bot startup script.
Checks for `LUDUS_TOKEN` and runs a lightweight discord.py bot for health.
Replace with full implementation as needed.
"""
import os
import sys
import logging

try:
    import dotenv
    from discord.ext import commands
except Exception:
    print("Missing runtime dependencies (dotenv, discord). Install requirements.")
    raise

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO, format='[Ludus-Bot] %(message)s')

TOKEN = os.environ.get('LUDUS_TOKEN')
if not TOKEN:
    logging.error('LUDUS_TOKEN not set. Create a Ludus-Bot/.env from Ludus-Bot/.env.example')
    sys.exit(2)

intents = None
try:
    import discord
    intents = discord.Intents.default()
    intents.message_content = True
except Exception:
    intents = None

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f"[Ludus-Bot] Ready as {bot.user} (id: {bot.user.id})")


def main():
    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.exception('Bot failed to start: %s', e)


if __name__ == '__main__':
    main()
