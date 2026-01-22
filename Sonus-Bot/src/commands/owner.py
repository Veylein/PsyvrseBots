import asyncio
import importlib
import pkgutil
import sys
import time
from typing import Set

import discord
from discord.ext import commands

from src.utils.loaders import load_json
from src.logger import setup_logger
from src.utils.audit import log_action

logger = setup_logger(__name__)

OWNER_IDS: Set[int] = {1311394031640776716, 1382187068373074001}


def _owner_check(ctx: commands.Context) -> bool:
    return getattr(ctx.author, "id", None) in OWNER_IDS


def register(bot: commands.Bot):
    # expose owner ids on bot for other modules
    bot.owner_ids = OWNER_IDS

    # Static owner command registry (kept out of public help)
    OWNER_COMMANDS = [
        ("status <online|idle|dnd|invisible", "Set bot presence status"),
        ("presence <type> <text>", "Set activity line (playing/listening/watch/competing)"),
        ("test", "Run diagnostics"),
        ("ping", "Latency check"),
        ("voicecheck", "Verify voice subsystem"),
        ("reload <commands|ui|data|all>", "Soft-reload parts of Sonus"),
        ("album publish|unpublish <name>", "Manage published albums"),
        ("radio enable|disable <name>", "Enable/disable radios"),
        ("audiodebug", "Dump audio state"),
        ("forcefade <seconds>", "Force global fade"),
        ("silence", "Immediate mute"),
        ("lockdown", "Freeze controls"),
        ("unlock", "Restore controls"),
        ("shutdown", "Graceful shutdown"),
        ("say <text>", "Owner: send plain text as the bot"),
        ("embed <title> | <body>", "Owner: send an embed as the bot"),
        ("xyzownerzyx", "Hidden list of owner commands (DMs you)")
    ]

    @bot.check
    def _global_owner_check(ctx: commands.Context):
        # Only apply owner gates to owner-only commands explicitly.
        return True

    def owner_only():
        return commands.check(lambda ctx: _owner_check(ctx))

    @bot.command(name="status")
    @owner_only()
    async def _status(ctx: commands.Context, status: str):
        mapping = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        s = mapping.get(status.lower())
        if s is None:
            await ctx.send("Invalid status. Use: online|idle|dnd|invisible")
            return
        await bot.change_presence(status=s)
        await ctx.send(f"Status set to {status}")
        await log_action(bot, ctx.author.id, "status", {"status": status})

    @bot.command(name="presence")
    @owner_only()
    async def _presence(ctx: commands.Context, ptype: str, *, text: str = ""):
        if ptype.lower() == "clear":
            await bot.change_presence(activity=None)
            await ctx.send("Presence cleared")
            await log_action(bot, ctx.author.id, "presence_clear", {})
            return

        types = {
            "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "watching": discord.ActivityType.watching,
            "competing": discord.ActivityType.competing,
        }
        atype = types.get(ptype.lower())
        if atype is None:
            await ctx.send("Invalid activity type. Use playing|listening|watching|competing|clear")
            return
        activity = discord.Activity(type=atype, name=text)
        await bot.change_presence(activity=activity)
        await ctx.send(f"Presence set: {ptype} {text}")
        await log_action(bot, ctx.author.id, "presence", {"type": ptype, "text": text})

    @bot.command(name="test")
    @owner_only()
    async def _test(ctx: commands.Context):
        from discord import Embed

        e = Embed(title="Sonus Diagnostic")
        # Music commands
        music_ok = any(pkg.name == "music" for pkg in pkgutil.iter_modules(("src/commands/music",)))
        try:
            import src.audio
            audio_ok = True
        except Exception:
            audio_ok = False
        try:
            settings = load_json("data/settings.json")
            data_ok = True
        except Exception:
            data_ok = False
        ui_ok = True

        e.add_field(name="Music Commands", value=("✅" if music_ok else "⚠️"), inline=True)
        e.add_field(name="Audio Engine", value=("✅" if audio_ok else "❌"), inline=True)
        e.add_field(name="Data Loaders", value=("✅" if data_ok else "❌"), inline=True)
        e.add_field(name="UI", value=("✅" if ui_ok else "⚠️"), inline=True)

        await ctx.send(embed=e)
        await log_action(bot, ctx.author.id, "test", {})

    @bot.command(name="ping")
    @owner_only()
    async def _ping(ctx: commands.Context):
        start = time.perf_counter()
        msg = await ctx.send("Pinging...")
        gateway = round(bot.latency * 1000)
        delta = round((time.perf_counter() - start) * 1000)
        try:
            await msg.edit(content=f"Pong — gateway: {gateway}ms, roundtrip: {delta}ms")
        except Exception:
            await ctx.send(f"Pong — gateway: {gateway}ms, roundtrip: {delta}ms")
        await log_action(bot, ctx.author.id, "ping", {"gateway_ms": gateway, "roundtrip_ms": delta})

    @bot.command(name="voicecheck")
    @owner_only()
    async def _voicecheck(ctx: commands.Context):
        # Best-effort checks without actually connecting
        msgs = []
        intents_ok = bot.intents.voice_states
        msgs.append(("Voice Intents", intents_ok))
        try:
            import src.audio.player as player_mod
            msgs.append(("Player Module", True))
        except Exception:
            msgs.append(("Player Module", False))
        out = "\n".join([f"{n}: {'✅' if v else '❌'}" for n, v in msgs])
        await ctx.send(f"Voice check:\n{out}")
        await log_action(bot, ctx.author.id, "voicecheck", {"results": out})

    async def _reload_package(prefix: str):
        reloaded = []
        errors = []
        for name, mod in list(sys.modules.items()):
            if name.startswith(prefix):
                try:
                    importlib.reload(mod)
                    reloaded.append(name)
                except Exception as e:
                    errors.append((name, str(e)))
        return reloaded, errors

    @bot.command(name="reload")
    @owner_only()
    async def _reload(ctx: commands.Context, target: str):
        target = target.lower()
        if target == "commands":
            reloaded, errors = await _reload_package("src.commands")
            await ctx.send(f"Reloaded commands: {len(reloaded)} modules; errors: {len(errors)}")
            await log_action(bot, ctx.author.id, "reload_commands", {"modules": len(reloaded), "errors": len(errors)})
        elif target == "ui":
            reloaded, errors = await _reload_package("src.ui")
            await ctx.send(f"Reloaded ui: {len(reloaded)} modules; errors: {len(errors)}")
            await log_action(bot, ctx.author.id, "reload_ui", {"modules": len(reloaded), "errors": len(errors)})
        elif target == "data":
            # Reload JSON data into a cache on bot
            try:
                bot.sonus_data = {
                    "settings": load_json("data/settings.json"),
                    "eq_presets": load_json("data/eq_presets.json"),
                }
                await ctx.send("Data reloaded")
                await log_action(bot, ctx.author.id, "reload_data", {})
            except Exception as e:
                await ctx.send(f"Failed to reload data: {e}")
                await log_action(bot, ctx.author.id, "reload_data_failed", {"error": str(e)})
        elif target == "all":
            await _reload(ctx, "commands")
            await _reload(ctx, "ui")
            await _reload(ctx, "data")
            await ctx.send("Reloaded all")
            await log_action(bot, ctx.author.id, "reload_all", {})
        else:
            await ctx.send("Unknown reload target: commands|ui|data|all")

    @bot.group(name="album", invoke_without_command=True)
    @owner_only()
    async def _album(ctx: commands.Context):
        await ctx.send("Use: album publish|unpublish <name>")

    @_album.command(name="publish")
    @owner_only()
    async def _album_publish(ctx: commands.Context, *, name: str):
        s = getattr(bot, "sonus_published_albums", set())
        s.add(name)
        bot.sonus_published_albums = s
        await ctx.send(f"Album published: {name}")
        await log_action(bot, ctx.author.id, "album_publish", {"name": name})

    @_album.command(name="unpublish")
    @owner_only()
    async def _album_unpublish(ctx: commands.Context, *, name: str):
        s = getattr(bot, "sonus_published_albums", set())
        s.discard(name)
        bot.sonus_published_albums = s
        await ctx.send(f"Album unpublished: {name}")
        await log_action(bot, ctx.author.id, "album_unpublish", {"name": name})

    if bot.get_command('radio') is None:
        @bot.group(name="radio", invoke_without_command=True)
        @owner_only()
        async def _radio(ctx: commands.Context):
            await ctx.send("Use: radio enable|disable <name>")

        @_radio.command(name="enable")
        @owner_only()
        async def _radio_enable(ctx: commands.Context, *, name: str):
            s = getattr(bot, "sonus_enabled_radios", set())
            s.add(name)
            bot.sonus_enabled_radios = s
            await ctx.send(f"Radio enabled: {name}")
            await log_action(bot, ctx.author.id, "radio_enable", {"name": name})

        @_radio.command(name="disable")
        @owner_only()
        async def _radio_disable(ctx: commands.Context, *, name: str):
            s = getattr(bot, "sonus_enabled_radios", set())
            s.discard(name)
            bot.sonus_enabled_radios = s
            await ctx.send(f"Radio disabled: {name}")
            await log_action(bot, ctx.author.id, "radio_disable", {"name": name})
    else:
        logger.info("Radio command already exists; skipping owner radio group")

    @bot.command(name="audiodebug")
    @owner_only()
    async def _audiodebug(ctx: commands.Context):
        info = getattr(bot, "sonus_audio", {}) or {}
        lines = [f"{k}: {v}" for k, v in info.items()]
        await ctx.send("Audio debug:\n" + ("\n".join(lines) if lines else "(no audio state)"))
        await log_action(bot, ctx.author.id, "audiodebug", {"state_present": bool(lines)})

    @bot.command(name="forcefade")
    @owner_only()
    async def _forcefade(ctx: commands.Context, seconds: int):
        bot.sonus_forcefade = seconds
        await ctx.send(f"Forcing global fade: {seconds}s")
        await log_action(bot, ctx.author.id, "forcefade", {"seconds": seconds})

    @bot.command(name="silence")
    @owner_only()
    async def _silence(ctx: commands.Context):
        bot.sonus_silenced = True
        await ctx.send("Global silence engaged")
        await log_action(bot, ctx.author.id, "silence", {})

    @bot.command(name="lockdown")
    @owner_only()
    async def _lockdown(ctx: commands.Context):
        bot.sonus_lockdown = True
        await ctx.send("Sonus is now in lockdown (controls frozen)")
        await log_action(bot, ctx.author.id, "lockdown", {})

    @bot.command(name="unlock")
    @owner_only()
    async def _unlock(ctx: commands.Context):
        bot.sonus_lockdown = False
        await ctx.send("Sonus controls restored")
        await log_action(bot, ctx.author.id, "unlock", {})

    @bot.command(name="shutdown")
    @owner_only()
    async def _shutdown(ctx: commands.Context):
        await ctx.send("Shutting down gracefully...")
        try:
            # attempt to fade and close
            bot.sonus_silenced = True
            await asyncio.sleep(0.5)
            await log_action(bot, ctx.author.id, "shutdown", {})
            await bot.close()
        except Exception as e:
            logger.exception("Error during shutdown: %s", e)
            await log_action(bot, ctx.author.id, "shutdown_error", {"error": str(e)})

    @bot.command(name="say", hidden=True)
    @owner_only()
    async def _say(ctx: commands.Context, *, text: str):
        """Owner-only: send raw text as the bot in the current channel."""
        await ctx.send(text)
        await log_action(bot, ctx.author.id, "say", {"text_preview": text[:200]})

    @bot.command(name="embed", hidden=True)
    @owner_only()
    async def _embed(ctx: commands.Context, *, payload: str):
        """Owner-only: send an embed. Usage: S!embed Title | Body"""
        parts = [p.strip() for p in payload.split("|", 1)]
        title = parts[0] if parts else ""
        body = parts[1] if len(parts) > 1 else ""
        e = discord.Embed(title=title or None, description=body or None)
        await ctx.send(embed=e)
        await log_action(bot, ctx.author.id, "embed", {"title": title, "body_preview": body[:200]})

    @bot.command(name="xyzownerzyx", hidden=True)
    @owner_only()
    async def _xyzownerzyx(ctx: commands.Context):
        """Hidden owner command: DMs the invoking owner the master list of owner commands."""
        lines = [f"**{cmd}** — {desc}" for cmd, desc in OWNER_COMMANDS]
        text = "\n".join(lines)
        try:
            await ctx.author.send("Owner commands:\n" + text)
            await ctx.send("Sent owner commands to your DMs.")
        except Exception:
            await ctx.send("Could not DM you. Here are owner commands:\n" + text)
        await log_action(bot, ctx.author.id, "xyz_list", {})

    logger.info("Owner command module registered")
