import aiohttp
import asyncio
import re
from typing import Optional

import discord
from discord.ext import commands

from src.logger import setup_logger
from src.utils.audit import log_action

logger = setup_logger(__name__)


def _split_chunks(text: str, size: int = 1900):
    return [text[i : i + size] for i in range(0, len(text), size)]


def _guess_artist_title(track: dict) -> tuple[Optional[str], Optional[str]]:
    # Prefer explicit metadata
    title = track.get("title") or track.get("name")
    artist = track.get("artist") or track.get("artists") or track.get("author")
    if isinstance(artist, list):
        artist = ", ".join(artist)

    if title and isinstance(title, str) and " - " in title and not artist:
        # common format: Artist - Title or Title - Artist; try both
        parts = [p.strip() for p in title.split(" - ", 1)]
        # Heuristic: if first contains comma or contains more than one word and second shorter, assume first=artist
        a, b = parts[0], parts[1]
        if len(a.split()) <= 3 and len(b.split()) > 1:
            artist, title = a, b
        else:
            artist, title = a, b

    # fallback: attempt parse 'by' in title
    if title and (not artist or artist == ""):
        m = re.match(r"^(?P<title>.*) by (?P<artist>.+)$", title, re.IGNORECASE)
        if m:
            title = m.group("title").strip()
            artist = m.group("artist").strip()

    return artist, title


async def _fetch_lyrics(artist: str, title: str) -> Optional[str]:
    # Try lyrics.ovh first: https://api.lyrics.ovh/v1/{artist}/{title}
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    # sanitize
    url = url.replace(" ", "%20")
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("lyrics")
                    if lyrics:
                        return lyrics
                return None
    except Exception:
        logger.exception("Error fetching lyrics from lyrics.ovh")
        return None


def _now_playing_from_bot(bot: commands.Bot) -> Optional[dict]:
    # check standard locations for now playing metadata
    if hasattr(bot, "sonus_now_playing") and bot.sonus_now_playing:
        return bot.sonus_now_playing
    sa = getattr(bot, "sonus_audio", None)
    if isinstance(sa, dict):
        np = sa.get("now_playing") or sa.get("current")
        if np:
            return np
    # last resort: check bot attributes
    return None


def register(bot: commands.Bot):
    @bot.command(name="lyrics")
    async def _lyrics(ctx: commands.Context):
        """Prefix: S!lyrics — DMs the requesting user the lyrics for the currently playing song."""
        track = _now_playing_from_bot(bot)
        if not track:
            await ctx.author.send("No song is currently playing or lyrics unavailable.")
            await ctx.send("I've sent you a DM (if available).")
            await log_action(bot, ctx.author.id, "lyrics_request", {"found": False})
            return

        artist, title = _guess_artist_title(track)
        if not title:
            await ctx.author.send("Could not determine the current track title for lyrics lookup.")
            await ctx.send("I've sent you a DM (if available).")
            await log_action(bot, ctx.author.id, "lyrics_request", {"found": False})
            return

        lyrics = None
        if artist:
            lyrics = await _fetch_lyrics(artist, title)
        if not lyrics:
            # try swapping artist/title if parsing ambiguous
            if artist:
                lyrics = await _fetch_lyrics(title, artist)

        if not lyrics:
            await ctx.author.send(f"Lyrics not found for: {title} — {artist or 'unknown artist'}")
            await ctx.send("I've sent you a DM (if available).")
            await log_action(bot, ctx.author.id, "lyrics_request", {"found": False, "title": title, "artist": artist})
            return

        # send lyrics in DM in chunks
        try:
            header = f"Lyrics — {title}{' — ' + artist if artist else ''}\n\n"
            for chunk in _split_chunks(lyrics):
                await ctx.author.send(header + chunk)
                header = ""  # only include header once
                await asyncio.sleep(0.2)
            await ctx.send("Sent lyrics to your DMs.")
            await log_action(bot, ctx.author.id, "lyrics_request", {"found": True, "title": title, "artist": artist})
        except Exception:
            logger.exception("Failed to DM lyrics")
            await ctx.send("Could not DM you the lyrics. Do you have DMs disabled?")
            await log_action(bot, ctx.author.id, "lyrics_dm_failed", {})

    @bot.tree.command(name="lyrics")
    async def _lyrics_slash(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        track = _now_playing_from_bot(bot)
        user = interaction.user
        if not track:
            try:
                await user.send("No song is currently playing or lyrics unavailable.")
            except Exception:
                pass
            await interaction.followup.send("I've sent you a DM (if available).", ephemeral=True)
            await log_action(bot, user.id, "lyrics_request", {"found": False})
            return

        artist, title = _guess_artist_title(track)
        if not title:
            try:
                await user.send("Could not determine the current track title for lyrics lookup.")
            except Exception:
                pass
            await interaction.followup.send("I've sent you a DM (if available).", ephemeral=True)
            await log_action(bot, user.id, "lyrics_request", {"found": False})
            return

        lyrics = None
        if artist:
            lyrics = await _fetch_lyrics(artist, title)
        if not lyrics:
            if artist:
                lyrics = await _fetch_lyrics(title, artist)

        if not lyrics:
            try:
                await user.send(f"Lyrics not found for: {title} — {artist or 'unknown artist'}")
            except Exception:
                pass
            await interaction.followup.send("I've sent you a DM (if available).", ephemeral=True)
            await log_action(bot, user.id, "lyrics_request", {"found": False, "title": title, "artist": artist})
            return

        try:
            header = f"Lyrics — {title}{' — ' + artist if artist else ''}\n\n"
            for chunk in _split_chunks(lyrics):
                await user.send(header + chunk)
                header = ""
                await asyncio.sleep(0.2)
            await interaction.followup.send("Sent lyrics to your DMs.", ephemeral=True)
            await log_action(bot, user.id, "lyrics_request", {"found": True, "title": title, "artist": artist})
        except Exception:
            logger.exception("Failed to DM lyrics (slash)")
            await interaction.followup.send("Could not DM you the lyrics. Do you have DMs disabled?", ephemeral=True)
            await log_action(bot, user.id, "lyrics_dm_failed", {})
