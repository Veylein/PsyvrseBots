import os
import traceback
import datetime
import asyncio
from typing import Optional

import discord

LOG_CHANNEL_ENV = os.environ.get("LOG_CHANNEL")


class LudusLogger:
    def __init__(self):
        self.bot: Optional[discord.Client] = None
        self.log_channel_id: Optional[int] = None
        self._send_failure_reported = False
        try:
            if LOG_CHANNEL_ENV:
                self.log_channel_id = int(LOG_CHANNEL_ENV)
        except Exception:
            self.log_channel_id = None

    def init(self, bot: discord.Client):
        self.bot = bot

    async def _get_channel(self) -> Optional[discord.TextChannel]:
        if not self.bot or not self.log_channel_id:
            return None
        # Prefer cache, fallback to fetch
        ch = self.bot.get_channel(self.log_channel_id)
        if ch:
            return ch
        try:
            return await self.bot.fetch_channel(self.log_channel_id)
        except Exception:
            return None

    def format_traceback(self, exc: Exception) -> str:
        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        # Discord limit safety
        if len(tb) > 1900:
            tb = tb[-1900:]
        return tb

    async def send(self, *, level: str = "ERROR", title: str = None, message: str = None, exc: Exception = None, ctx=None, interaction=None, extra: dict = None):
        ch = await self._get_channel()
        # Build a fallback log to stdout if channel missing
        if not ch:
            out = f"[{level}] {title or message}\n"
            if exc:
                out += self.format_traceback(exc)
            print(out)
            return

        embed = discord.Embed(title=f"[{level}] {title or message or 'Log'}", timestamp=datetime.datetime.utcnow(), color=0xED4245)
        if message:
            embed.description = message

        if ctx is not None:
            try:
                embed.add_field(name="Command", value=getattr(ctx.command, 'name', str(ctx.command)), inline=True)
                embed.add_field(name="User", value=f"{ctx.author} ({ctx.author.id})", inline=True)
                embed.add_field(name="Channel", value=f"{getattr(ctx.channel, 'name', str(getattr(ctx.channel, 'id', 'unknown')))} ({getattr(ctx.channel, 'id', 'unknown')})", inline=True)
                embed.add_field(name="Guild", value=f"{getattr(ctx.guild, 'name', None)} ({getattr(ctx.guild, 'id', None)})", inline=True)
            except Exception:
                pass

        if interaction is not None:
            try:
                u = interaction.user
                embed.add_field(name="Interaction User", value=f"{u} ({u.id})", inline=True)
                embed.add_field(name="Interaction Guild", value=f"{getattr(interaction.guild, 'name', None)} ({getattr(interaction.guild, 'id', None)})", inline=True)
                embed.add_field(name="Interaction Channel", value=f"{getattr(interaction.channel, 'id', None)}", inline=True)
            except Exception:
                pass

        if exc is not None:
            tb = self.format_traceback(exc)
            embed.add_field(name="Traceback", value=f"```py\n{tb}\n```", inline=False)

        if extra:
            for k, v in (extra.items() if isinstance(extra, dict) else []):
                try:
                    embed.add_field(name=str(k), value=str(v), inline=True)
                except Exception:
                    pass

        try:
            await ch.send(embed=embed)
            self._send_failure_reported = False
        except Exception as send_error:
            # Last resort fallback to stdout (once per failure streak)
            if not self._send_failure_reported:
                print(f"Failed sending log to channel {self.log_channel_id}: {send_error}")
                self._send_failure_reported = True


_L = LudusLogger()


def init(bot: discord.Client):
    _L.init(bot)


def log_exception(exc: Exception, **kwargs):
    """Schedule sending an exception log to the configured log channel."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_L.send(level="ERROR", exc=exc, **kwargs))
        else:
            loop.run_until_complete(_L.send(level="ERROR", exc=exc, **kwargs))
    except Exception:
        # If logging fails, print fallback
        print("Logging failed:")
        traceback.print_exception(type(exc), exc, exc.__traceback__)


def log_message(level: str = "INFO", title: str = None, message: str = None, **kwargs):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_L.send(level=level, title=title, message=message, **kwargs))
        else:
            loop.run_until_complete(_L.send(level=level, title=title, message=message, **kwargs))
    except Exception:
        print(f"[{level}] {title or message}")
