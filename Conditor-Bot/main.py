"""Entrypoint for Conditor bot.

Provides two modes:
- dry-run: show deterministic plans without connecting to Discord
- run: start the Discord bot (requires CONDITOR_TOKEN)

Usage examples:
  python main.py --dry-run
  python main.py --run  # requires CONDITOR_TOKEN env var
  CONDITOR_TOKEN=... python main.py --run
  CONDITOR_TOKEN=... COND_GUILD_ID=123... python main.py --run
"""
import argparse
import logging
import os
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


BASE = Path(__file__).parent.resolve()
SRC = str(BASE / "src")
if SRC not in sys.path:
	sys.path.insert(0, SRC)


def run_dry_run():
	try:
		from conditor.parser import TemplateParser
		from conditor.templates.loader import load_template
	except Exception as exc:
		logging.exception("Failed to import Conditor modules for dry-run")
		raise

	parser = TemplateParser(load_template("bot_testing"))
	plan = parser.generate(inputs={"project_name": "dry-run"}, actor_id="0")
	import json

	print(json.dumps(plan, indent=2))


def run_bot():
	try:
		from conditor.bot import create_bot
		from conditor.commands.setup import setup_sync
	except Exception:
		logging.exception("Failed to import Conditor bot modules; check your environment and installed deps")
		return 2

	token = os.environ.get("CONDITOR_TOKEN")
	if not token:
		logging.error("CONDITOR_TOKEN environment variable not set. Aborting.")
		return 2

	bot = create_bot()

	@bot.event
	async def on_ready():
		logging.info("Connected — running setup_sync and syncing commands...")
		try:
			await setup_sync(bot)
			# fast guild sync if desired
			guild_id = os.environ.get("COND_GUILD_ID")
			if guild_id:
				try:
					from discord import Object

					obj = Object(id=int(guild_id))
					await bot.tree.sync(guild=obj)
					logging.info(f"Synced commands to dev guild {guild_id}")
				except Exception:
					logging.exception("Failed to sync to dev guild; falling back to global sync")
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
		return 1
	return 0


def main(argv=None):
	p = argparse.ArgumentParser(prog="conditor")
	g = p.add_mutually_exclusive_group(required=True)
	g.add_argument("--dry-run", action="store_true", help="Print deterministic plan and exit")
	g.add_argument("--run", action="store_true", help="Run the Discord bot (requires CONDITOR_TOKEN)")
	args = p.parse_args(argv)

	if args.dry_run:
		run_dry_run()
		return 0
	if args.run:
		return run_bot()


if __name__ == "__main__":
	raise SystemExit(main())

