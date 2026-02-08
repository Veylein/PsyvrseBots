from __future__ import annotations

from typing import Iterable, Optional, Tuple

import discord

BRAND_COLOR = discord.Color.from_rgb(255, 215, 0)
OK_COLOR = discord.Color.from_rgb(46, 204, 113)
WARN_COLOR = discord.Color.from_rgb(243, 156, 18)
ERROR_COLOR = discord.Color.from_rgb(231, 76, 60)
INFO_COLOR = discord.Color.from_rgb(52, 152, 219)

FOOTER_TEXT = "Villicus VIP Moderation"


def _base_embed(title: str, description: Optional[str], color: discord.Color) -> discord.Embed:
    emb = discord.Embed(title=title, description=description, color=color)
    emb.set_footer(text=FOOTER_TEXT)
    return emb


def brand_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    return _base_embed(title, description, BRAND_COLOR)


def success_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    return _base_embed(title, description, OK_COLOR)


def warn_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    return _base_embed(title, description, WARN_COLOR)


def error_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    return _base_embed(title, description, ERROR_COLOR)


def info_embed(title: str, description: Optional[str] = None) -> discord.Embed:
    return _base_embed(title, description, INFO_COLOR)


def mod_action_embed(
    action: str,
    target_display: str,
    moderator_display: str,
    reason: Optional[str] = None,
    duration: Optional[str] = None,
    extra_fields: Optional[Iterable[Tuple[str, str]]] = None,
) -> discord.Embed:
    emb = brand_embed(f"{action} | {target_display}")
    emb.add_field(name="Target", value=target_display, inline=True)
    emb.add_field(name="Moderator", value=moderator_display, inline=True)
    if reason:
        emb.add_field(name="Reason", value=reason, inline=False)
    if duration:
        emb.add_field(name="Duration", value=duration, inline=True)
    if extra_fields:
        for name, value in extra_fields:
            emb.add_field(name=name, value=value, inline=False)
    return emb


async def send(
    interaction: discord.Interaction,
    *,
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    ephemeral: bool = True,
    view: Optional[discord.ui.View] = None,
):
    if interaction.response.is_done():
        return await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral, view=view)
    return await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral, view=view)
