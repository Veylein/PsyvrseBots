import importlib
import pkgutil
from pathlib import Path

import discord
from discord.ext import commands

from src.config import Config
from src.logger import setup_logger
from src.audio.player import Player
from src.utils.guild_settings import load as load_guild_settings

logger = setup_logger(__name__)


def _register_event_modules(bot):
    try:
        import src.events as events_pkg
    except Exception:
        logger.exception("Could not import src.events package")
        return

    for finder, name, ispkg in pkgutil.iter_modules(events_pkg.__path__):
        full = f"{events_pkg.__name__}.{name}"
        try:
            mod = importlib.import_module(full)
            if hasattr(mod, "register"):
                mod.register(bot)
                logger.info(f"Registered event module: {full}")
        except Exception:
            logger.exception(f"Failed to register event module: {full}")


async def _register_command_modules(bot):
    """Automatically load all cogs from src.commands and src.ui as Cogs."""
    for pkg_name in ["src.commands", "src.ui"]:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            logger.exception(f"Could not import {pkg_name} package")
            continue

        for finder, name, ispkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
            try:
                mod = importlib.import_module(name)
                # Support two module styles:
                # 1) Modern Cog-style modules exposing `async def setup(bot)`
                # 2) Legacy modules exposing `def register(bot)` which attach commands/events
                if hasattr(mod, "setup"):
                    await mod.setup(bot)
                    logger.info(f"Loaded cog: {name}")
                elif hasattr(mod, "register"):
                    try:
                        mod.register(bot)
                        logger.info(f"Registered module via register(): {name}")
                    except Exception:
                        logger.exception(f"register() failed for module: {name}")
            except Exception:
                logger.exception(f"Failed to load cog: {name}")


def create_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.voice_states = True

    async def _get_prefix(bot, message):
        # return a callable-compatible prefix list; fall back to default
        try:
            if message.guild:
                settings = load_guild_settings(message.guild.id)
                prefix = settings.get("prefix", "S!")
            else:
                prefix = "S!"
            return commands.when_mentioned_or(prefix)(bot, message)
        except Exception:
            return commands.when_mentioned_or("S!")(bot, message)

    bot = commands.Bot(
        command_prefix=_get_prefix,
        intents=intents,
        help_command=None,
    )

    bot.config = Config()
    bot.logger = logger

    # attach lightweight in-memory audio primitives
    try:
        bot.player = Player()
        try:
            from src.audio.queue import TrackQueue

            bot.track_queue = TrackQueue()
        except Exception:
            bot.track_queue = []
    except Exception:
        logger.exception("Failed to attach audio primitives")

    # Auto-register event modules
    _register_event_modules(bot)

    # Command / UI modules are loaded asynchronously as cogs
    # We'll handle that in on_ready
    async def _on_ready_internal():
        logger.info(f"Bot ready as {bot.user}")
        # Load commands and UI cogs
        await _register_command_modules(bot)
        # mark that command modules have been loaded
        try:
            setattr(bot, "sonus_commands_loaded", True)
        except Exception:
            pass
        # set application id if provided in config to help some sync paths
        try:
            if getattr(bot.config, "APP_ID", None):
                try:
                    bot.application_id = int(bot.config.APP_ID)
                except Exception:
                    # ignore invalid APP_ID format
                    pass
        except Exception:
            pass
        # Ensure commands have a help string
        try:
            for c in bot.commands:
                if not c.help:
                    c.help = "No description provided."
        except Exception:
            pass

        # Sync slash commands globally
        try:
            await bot.tree.sync()
            logger.info("✅ Slash commands synced successfully")
            try:
                slash_count = sum(1 for _ in bot.tree.walk_commands())
                prefix_count = len(bot.commands)
                slash_names = [c.name for c in bot.tree.walk_commands()]
                prefix_names = [c.name for c in bot.commands]
                logger.info(f"Registered slash commands: {slash_count} -> {slash_names}")
                logger.info(f"Registered prefix commands: {prefix_count} -> {prefix_names}")
            except Exception:
                logger.exception("Failed to enumerate registered commands for diagnostics")
        except Exception:
            logger.exception("❌ Failed to sync slash commands")
        # Diagnostic: check ffmpeg availability and log counts
        try:
            import asyncio, shutil

            ffmpeg_path = shutil.which('ffmpeg') or shutil.which('avconv')
            if ffmpeg_path:
                logger.info(f"FFmpeg found at: {ffmpeg_path}")
            else:
                # try to run `ffmpeg -version` to be sure
                proc = await asyncio.create_subprocess_exec('ffmpeg', '-version', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                out, err = await proc.communicate()
                if proc.returncode == 0:
                    logger.info("FFmpeg is available (version check succeeded)")
                else:
                    logger.warning("FFmpeg not found or not executable in PATH; audio playback may fail")
        except Exception:
            logger.exception("FFmpeg diagnostic check failed")

        try:
            slash_count = sum(1 for _ in bot.tree.walk_commands())
            prefix_count = len(bot.commands)
            logger.info(f"Command counts - slash: {slash_count}, prefix: {prefix_count}")
        except Exception:
            logger.exception("Failed to enumerate commands for diagnostics")

    # Add as an event listener without overwriting any existing on_ready handlers
    bot.add_listener(_on_ready_internal, "on_ready")

    return bot