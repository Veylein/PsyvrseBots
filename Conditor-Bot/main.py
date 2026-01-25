import os
import logging

from src.conditor.bot import create_bot
from src.conditor.commands.setup import setup_sync


logging.basicConfig(level=logging.INFO)


def main():
	token = os.environ.get("CONDITOR_TOKEN")
	if not token:
		logging.error("CONDITOR_TOKEN environment variable not set. Aborting.")
		return

	bot = create_bot()

	@bot.event
	async def on_ready():
		# Register cogs and sync application commands when the bot becomes ready
		try:
			await setup_sync(bot)
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

