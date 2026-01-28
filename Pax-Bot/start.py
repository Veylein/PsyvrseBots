"""Minimal Pax-Bot startup script.
Checks for `PAX_TOKEN` and runs a lightweight discord.py bot for health.
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
logging.basicConfig(level=logging.INFO, format='[Pax-Bot] %(message)s')

TOKEN = os.environ.get('PAX_TOKEN')
if not TOKEN:
    logging.error('PAX_TOKEN not set. Create a Pax-Bot/.env from Pax-Bot/.env.example')
    sys.exit(2)

import runpy


def main():
    try:
        # Execute main.py in a fresh namespace and get its globals
        module_globals = runpy.run_path("main.py")
        bot = module_globals.get("bot")
        if bot is None:
            logging.error('Pax main.py did not expose `bot`. Falling back to minimal runner.')
            sys.exit(2)

        # Run the bot using the token from the environment
        bot.run(TOKEN)
    except Exception as e:
        logging.exception('Bot failed to start: %s', e)


if __name__ == '__main__':
    main()
