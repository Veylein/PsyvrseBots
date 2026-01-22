from typing import Any, Dict, List

import discord
from discord import Embed
from discord.ext import commands

from src.utils.audit import log_action


def register(bot: commands.Bot):
    @bot.command(name="queue")
    async def _queue(ctx: commands.Context):
        try:
            items = bot.player.all()
        except Exception:
            items = getattr(bot, "track_queue", None) or getattr(bot, "sonus_queue", [])

        if not items:
            await ctx.send("Queue is empty")
            return

        # Build a simple embed showing up to 10 upcoming tracks
        lines: List[str] = []
        for i, t in enumerate(list(items)[:10], start=1):
            title = t.get("title") if isinstance(t, dict) else str(t)
            lines.append(f"{i}. {title}")

        desc = "\n".join(lines)
        if len(items) > 10:
            desc += f"\n...and {len(items) - 10} more"

        e = Embed(title="Queue", description=desc)
        await ctx.send(embed=e)

    @bot.tree.command(name="queue")
    async def _queue_slash(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ctx = await commands.Context.from_interaction(interaction)
        await _queue(ctx)