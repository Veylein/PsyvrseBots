import os
import sys
import logging
from pathlib import Path

# Ensure Conditor package (Conditor-Bot/src) is importable when running this script
BASE = Path(__file__).parent.resolve()
SRC = str(BASE / "src")
if SRC not in sys.path:
	sys.path.insert(0, SRC)

from conditor.bot import create_bot
from conditor.commands.setup import setup_sync


logging.basicConfig(level=logging.INFO)


def main():
	token = os.environ.get("CONDITOR_TOKEN")
	if not token:
		logging.error("CONDITOR_TOKEN environment variable not set. Aborting.")
		return

	bot = create_bot()

	@bot.event
	async def on_ready():
		logging.info("Conditor connected, running setup_sync and syncing commands...")
		try:
			await setup_sync(bot)
			# allow a fast guild sync for development: set COND_GUILD_ID to a guild id to sync there
			guild_id = os.environ.get("COND_GUILD_ID")
			if guild_id:
				try:
					from discord import Object
					obj = Object(id=int(guild_id))
					await bot.tree.sync(guild=obj)
					logging.info(f"Synced commands to dev guild {guild_id}")
				except Exception:
					logging.exception("Failed to sync to dev guild, falling back to global sync")
					await bot.tree.sync()
			else:
				await bot.tree.sync()
			logging.info(f"Conditor ready — {bot.user} (id: {bot.user.id})")
		except Exception:
			logging.exception("Failed to register commands on ready")

	try:
		bot.run(token)
	except Exception:
		logging.exception("Bot terminated with an exception")


if __name__ == "__main__":
	main()

